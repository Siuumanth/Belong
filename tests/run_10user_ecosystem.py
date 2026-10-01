"""
10-User Population Ecosystem Test Runner (Stage 1 Pure Candidate Retrieval)
=============================================================================
Tests Stage 1 candidate retrieval and vector similarity recall across 11 Bangalore personas:
- Hard constraints (location, distance, gender orientation, age bounds, relationship goal)
  are satisfied 100% so that ALL opposite-gender candidates pass Stage 1 SQL filters.
- Queries `GET /matches/retrieval/{user_id}` to test pgvector embedding recall & similarity scores
  WITHOUT invoking Stage 2 LLM pairwise compatibility reasoning.
- Provides detailed, structured logging of cosine similarity, reverse similarity, and combined score.

USAGE:
    python tests/run_10user_ecosystem.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

# Fix Windows console UTF-8 output encoding
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure tests directory and root directory are in sys.path
TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(ROOT_DIR))

from simulators.user_simulator import UserSimulator, PersonaConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ecosystem_stage1_retrieval")

API_URL = os.getenv("BELONG_API_URL", "http://localhost:8000")


async def check_api_health(client: httpx.AsyncClient) -> bool:
    try:
        res = await client.get("/healthz")
        if res.status_code == 200:
            logger.info(f"Connected to Belong API at {API_URL} (Status: OK)")
            return True
        logger.error(f"API health check failed: {res.status_code}")
        return False
    except Exception as e:
        logger.error(f"Cannot connect to Belong API at {API_URL}: {e}")
        return False


def load_golden_personas() -> List[PersonaConfig]:
    fixtures_file = TESTS_DIR / "fixtures" / "personas.json"
    if not fixtures_file.exists():
        raise FileNotFoundError(f"Personas file not found at {fixtures_file}")

    with open(fixtures_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    personas_raw = data.get("personas", [])
    configs = [PersonaConfig.from_dict(p) for p in personas_raw]
    logger.info(f"Loaded {len(configs)} personas from {fixtures_file.name}")
    return configs


async def run_ecosystem_test():
    print("=" * 85)
    print("      BELONG 10-USER POPULATION ECOSYSTEM SIMULATION (STAGE 1 RETRIEVAL)")
    print("=" * 85)

    persona_configs = load_golden_personas()
    simulated_users: Dict[str, UserSimulator] = {}
    user_id_to_pid: Dict[str, str] = {}
    
    for p_cfg in persona_configs:
        simulated_users[p_cfg.id] = UserSimulator(p_cfg)

    async with httpx.AsyncClient(base_url=API_URL, timeout=300.0) as client:
        if not await check_api_health(client):
            return

        # STEP 1: CREATE PROFILES
        print("\n-----------------------------------------------------------------")
        print(f"STEP 1: Registering Profiles for All {len(simulated_users)} Population Users")
        print("-----------------------------------------------------------------")

        async def _register(user: UserSimulator):
            ok = await user.create_profile_async(client)
            demo = user.persona.demographics
            if ok:
                user_id_to_pid[user.user_id] = user.persona.id
                logger.info(f"  [OK] Profile registered: '{user.persona.id}' ({demo.get('gender')}, age {demo.get('age')}) in Bangalore")
            else:
                logger.error(f"  [ERR] Failed profile: '{user.persona.id}'")
            return ok

        await asyncio.gather(*(_register(u) for u in simulated_users.values()))

        # STEP 2: ONBOARDING / TRAIT EXTRACTION
        print("\n-----------------------------------------------------------------")
        print(f"STEP 2: Executing Conversational Onboarding for Ecosystem Population")
        print("-----------------------------------------------------------------")

        async def _onboard(user: UserSimulator):
            ok = await user.run_onboarding_async(client)
            if ok:
                logger.info(f"  [OK] Onboarding complete: '{user.persona.id}'")
            else:
                logger.warning(f"  [WARN] Onboarding fallback/seeded: '{user.persona.id}'")
            return ok

        await asyncio.gather(*(_onboard(u) for u in simulated_users.values()))

        # STEP 3: TRIGGER & CONFIRM EMBEDDINGS
        print("\n-----------------------------------------------------------------")
        print("STEP 3: Computing Trait & Vector Embeddings (pgvector)")
        print("-----------------------------------------------------------------")

        async def _embed(user: UserSimulator):
            return await user.trigger_embeddings_async(client)

        await asyncio.gather(*(_embed(u) for u in simulated_users.values()))

        logger.info("Waiting for EmbeddingWorker to compute pgvector embeddings...")
        for w in range(15):
            await asyncio.sleep(2)
            ready_count = 0
            for u in simulated_users.values():
                try:
                    res = await client.get(f"/profiles/{u.user_id}/embeddings")
                    if res.status_code == 200 and res.json().get("has_self_embedding"):
                        ready_count += 1
                except Exception:
                    pass
            if ready_count >= len(simulated_users):
                logger.info(f"  [OK] All {ready_count}/{len(simulated_users)} user embeddings confirmed in pgvector after {(w+1)*2}s!")
                break
            elif w % 3 == 0:
                logger.info(f"  └─ Confirmed {ready_count}/{len(simulated_users)} embeddings ready...")

        # STEP 4: PERFORM STAGE 1 CANDIDATE RETRIEVAL FOR ALL USERS
        print("\n" + "=" * 90)
        print("STEP 4: DETAILED STAGE 1 CANDIDATE RETRIEVAL & VECTOR RECALL SCORES")
        print("=" * 90)

        retrieval_matrix: Dict[str, List[Dict[str, Any]]] = {}

        for pid, u in simulated_users.items():
            res = await client.get(f"/matches/retrieval/{u.user_id}")
            if res.status_code == 200:
                candidates = res.json().get("candidates", [])
            else:
                candidates = []
                logger.error(f"Failed retrieval for user '{pid}': {res.status_code} {res.text}")

            retrieval_matrix[pid] = candidates
            demo = u.persona.demographics

            print("\n" + "-" * 85)
            print(f"👤 PRIMARY USER: {pid.upper()} ({demo.get('gender')}, age {demo.get('age')}) | Bangalore")
            print(f"   Name: {u.persona.name} | ID: {u.user_id}")
            print("-" * 85)

            if not candidates:
                print("  ❌ No candidates retrieved (All filtered out by hard SQL constraints).")
                continue

            print(f"  Retrieved {len(candidates)} candidates passing hard constraints:\n")

            for rank, cand in enumerate(candidates, 1):
                cand_id = cand.get("user_id", "")
                cand_pid = user_id_to_pid.get(cand_id, cand.get("name") or cand_id[:8])
                cos_sim = cand.get("cosine_similarity", 0.0)
                rev_sim = cand.get("reverse_cosine_similarity")
                combined = cand.get("combined_score", 0.0)
                dist_km = cand.get("distance_km")

                rev_str = f"{rev_sim:.4f}" if rev_sim is not None else "N/A"
                dist_str = f"{dist_km} km" if dist_km is not None else "Nearby"

                print(f"  [{rank}] Candidate: {cand_pid.upper():<14} ({cand.get('gender')}, age {cand.get('age')})")
                print(f"      ├─ Distance:            {dist_str}")
                print(f"      ├─ Self->Wants Sim:     {cos_sim:.4f} (dist: {cand.get('cosine_distance', 0.0):.4f})")
                print(f"      ├─ Wants<-Self Sim:     {rev_str}")
                print(f"      └─ 🎯 Combined Score:   {combined:.4f}")
                print()

        # STEP 5: EXPORT SUMMARY REPORT TO tests/results/results_stage1_retrieval.md
        results_dir = TESTS_DIR / "results"
        results_dir.mkdir(exist_ok=True)
        report_path = results_dir / "results_stage1_retrieval.md"

        report_lines = [
            "# Stage 1 Candidate Retrieval Report (Bangalore 10-User Ecosystem)",
            "",
            "## Baseline Configuration",
            "- **Location**: Bangalore, India (Lat: 12.9716, Lon: 77.5946, 50km radius)",
            "- **Hard Constraints**: Mutual age bounds, mutual gender preferences, and location distance satisfied 100%.",
            "- **Retrieval Method**: pgvector Cosine Distance on 1536-dim text-embedding-3-small embeddings.",
            "- **Scoring Formula**: `Combined Score = 0.5 * (Self->Wants Sim) + 0.5 * (Wants<-Self Sim)`.",
            "",
            "## Stage 1 Candidate Retrieval Matrix",
            "",
            "| Primary User | Gender/Age | Candidates Retrieved | #1 Top Candidate | #1 Combined Score | #1 Self->Wants Sim | #2 Candidate | #2 Combined Score |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]

        for pid, u in simulated_users.items():
            cands = retrieval_matrix.get(pid, [])
            demo = u.persona.demographics
            gender_age = f"{demo.get('gender')}, {demo.get('age')}"

            if not cands:
                report_lines.append(f"| `{pid}` | {gender_age} | 0 | None | 0.0000 | 0.0000 | None | 0.0000 |")
                continue

            c1 = cands[0]
            c1_pid = user_id_to_pid.get(c1.get("user_id", ""), c1.get("name") or "unknown")
            c1_score = c1.get("combined_score", 0.0)
            c1_sim = c1.get("cosine_similarity", 0.0)

            if len(cands) > 1:
                c2 = cands[1]
                c2_pid = user_id_to_pid.get(c2.get("user_id", ""), c2.get("name") or "unknown")
                c2_score = c2.get("combined_score", 0.0)
            else:
                c2_pid = "None"
                c2_score = 0.0

            report_lines.append(
                f"| `{pid}` | {gender_age} | {len(cands)} | `{c1_pid}` | **{c1_score:.4f}** | {c1_sim:.4f} | `{c2_pid}` | {c2_score:.4f} |"
            )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        logger.info(f"✅ Stage 1 retrieval summary report exported to {report_path}")

    print("\n" + "=" * 85)
    print("STAGE 1 CANDIDATE RETRIEVAL TEST COMPLETE!")
    print("=" * 85)


if __name__ == "__main__":
    asyncio.run(run_ecosystem_test())
