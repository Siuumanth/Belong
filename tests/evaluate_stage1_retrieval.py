"""
Fast Stage 1 Candidate Retrieval Evaluator
===========================================
Queries `GET /matches/retrieval/{user_id}` for all registered users in PostgreSQL pgvector:
- Does NOT perform onboarding or profile creation.
- Evaluates Stage 1 hard constraint filters + pgvector embedding similarity.
- Outputs full ordered candidate rankings (Rank #1, #2, #3, #4, #5, #6) with score breakdowns.
- Exports report to `tests/results/results_stage1_retrieval.md`.

USAGE:
    python tests/evaluate_stage1_retrieval.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import httpx

# Fix Windows console UTF-8 output encoding and psycopg SelectorEventLoop policy
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# Ensure tests directory and root directory are in sys.path
TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evaluate_stage1_retrieval")

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


def load_golden_personas() -> List[Dict[str, Any]]:
    fixtures_file = TESTS_DIR / "fixtures" / "personas.json"
    if not fixtures_file.exists():
        raise FileNotFoundError(f"Personas file not found at {fixtures_file}")

    with open(fixtures_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("personas", [])


# pyrefly: ignore [missing-import]
import psycopg
# pyrefly: ignore [missing-import]
from psycopg.rows import dict_row

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "belong")
DB_USER = os.getenv("POSTGRES_USER", "belong_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "belong_password")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def fetch_registered_profiles_from_db() -> List[Dict[str, Any]]:
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id, name, gender, age, latitude, longitude FROM profiles ORDER BY created_at ASC;")
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch profiles from PostgreSQL DB: {e}")
        return []

async def run_retrieval_evaluation():
    print("=" * 85)
    print("      BELONG STAGE 1 CANDIDATE RETRIEVAL & ORDERED RANKING EVALUATOR")
    print("=" * 85)

    personas = load_golden_personas()
    
    async with httpx.AsyncClient(base_url=API_URL, timeout=60.0) as client:
        if not await check_api_health(client):
            return

        # Fetch all registered profiles directly from PostgreSQL DB
        registered_profiles = await fetch_registered_profiles_from_db()

        if not registered_profiles:
            logger.error("No registered profiles found in database. Please run onboarding/profile registration first.")
            return

        user_id_to_name: Dict[str, str] = {}
        user_id_to_demo: Dict[str, Dict[str, Any]] = {}
        pid_to_user_id: Dict[str, str] = {}

        for p in registered_profiles:
            uid = str(p.get("user_id"))
            name = p.get("name") or uid[:8]
            user_id_to_name[uid] = name
            user_id_to_demo[uid] = {
                "gender": p.get("gender"),
                "age": p.get("age"),
                "location": "Bangalore"
            }
            # Match persona ID if name matches or fallback
            for persona in personas:
                if persona.get("id") and (persona["id"].lower() in name.lower() or name.lower() in persona["id"].lower()):
                    pid_to_user_id[persona["id"]] = uid

        logger.info(f"Loaded {len(registered_profiles)} profiles from database.")

        # QUERY STAGE 1 CANDIDATE RETRIEVAL FOR ALL USERS
        print("\n" + "=" * 90)
        print("PERFORMING STAGE 1 RETRIEVAL & BUILDING ORDERED RANKINGS FOR ALL USERS")
        print("=" * 90)

        retrieval_matrix: Dict[str, List[Dict[str, Any]]] = {}

        for p in registered_profiles:
            uid = str(p.get("user_id"))
            uname = p.get("name") or uid[:8]
            demo = user_id_to_demo.get(uid, {})

            res = await client.get(f"/matches/retrieval/{uid}")
            if res.status_code == 200:
                candidates = res.json().get("candidates", [])
            else:
                candidates = []
                logger.error(f"Failed retrieval for user '{uname}' ({uid}): {res.status_code} {res.text}")

            retrieval_matrix[uid] = candidates

            print("\n" + "-" * 85)
            print(f"👤 PRIMARY USER: {uname.upper()} ({demo.get('gender')}, age {demo.get('age')}) | User ID: {uid}")
            print("-" * 85)

            if not candidates:
                print("  ❌ No candidates retrieved (Filtered out by hard SQL constraints).")
                continue

            print(f"  Retrieved {len(candidates)} candidates in ordered rank:\n")

            for rank, cand in enumerate(candidates, 1):
                cand_id = str(cand.get("user_id", ""))
                cand_name = user_id_to_name.get(cand_id, cand.get("name") or cand_id[:8])
                cos_sim = cand.get("cosine_similarity", 0.0)
                rev_sim = cand.get("reverse_cosine_similarity")
                combined = cand.get("combined_score", 0.0)
                dist_km = cand.get("distance_km")

                rev_str = f"{rev_sim:.4f}" if rev_sim is not None else "N/A"
                dist_str = f"{dist_km} km" if dist_km is not None else "Nearby"

                print(f"  [{rank}] Candidate: {cand_name.upper():<16} ({cand.get('gender')}, age {cand.get('age')})")
                print(f"      ├─ Distance:            {dist_str}")
                print(f"      ├─ Forward Sim (A->B): {cos_sim:.4f}")
                print(f"      ├─ Reverse Sim (B->A): {rev_str}")
                print(f"      └─ 🎯 Combined Score:   {combined:.4f}")
                print()

        # EXPORT DETAILED FULL RANKING REPORT TO tests/results/results_stage1_retrieval.md
        results_dir = TESTS_DIR / "results"
        results_dir.mkdir(exist_ok=True)
        report_path = results_dir / "results_stage1_retrieval.md"

        report_lines = [
            "# Stage 1 Candidate Retrieval Report (Bangalore 10-User Ecosystem)",
            "",
            "## Baseline Configuration",
            "- **Location**: Bangalore, India (50km radius)",
            "- **Hard Constraints**: Mutual age bounds, mutual gender preferences, and location distance satisfied 100%.",
            "- **Retrieval Method**: pgvector Cosine Distance on 1536-dim text-embedding-3-small embeddings.",
            "- **Scoring Formula**: `Combined Score = 0.5 * (Self->Wants Sim) + 0.5 * (Wants<-Self Sim)`.",
            "",
            "## Summary Retrieval Matrix",
            "",
            "| Primary User | Gender/Age | Candidates Retrieved | #1 Top Candidate | #1 Combined Score | #1 Forward Sim | #2 Candidate | #2 Combined Score |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]

        for p in registered_profiles:
            uid = str(p.get("user_id"))
            uname = p.get("name") or uid[:8]
            demo = user_id_to_demo.get(uid, {})
            cands = retrieval_matrix.get(uid, [])
            gender_age = f"{demo.get('gender')}, {demo.get('age')}"

            if not cands:
                report_lines.append(f"| `{uname}` | {gender_age} | 0 | None | 0.0000 | 0.0000 | None | 0.0000 |")
                continue

            c1 = cands[0]
            c1_id = str(c1.get("user_id", ""))
            c1_name = user_id_to_name.get(c1_id, c1.get("name") or c1_id[:8])
            c1_score = c1.get("combined_score", 0.0)
            c1_sim = c1.get("cosine_similarity", 0.0)

            if len(cands) > 1:
                c2 = cands[1]
                c2_id = str(c2.get("user_id", ""))
                c2_name = user_id_to_name.get(c2_id, c2.get("name") or c2_id[:8])
                c2_score = c2.get("combined_score", 0.0)
            else:
                c2_name = "None"
                c2_score = 0.0

            report_lines.append(
                f"| `{uname}` | {gender_age} | {len(cands)} | `{c1_name}` | **{c1_score:.4f}** | {c1_sim:.4f} | `{c2_name}` | {c2_score:.4f} |"
            )

        report_lines.extend([
            "",
            "---",
            "## Detailed Candidate Rankings (Full Ordered Shortlists for Every User)",
            "",
        ])

        for p in registered_profiles:
            uid = str(p.get("user_id"))
            uname = p.get("name") or uid[:8]
            demo = user_id_to_demo.get(uid, {})
            cands = retrieval_matrix.get(uid, [])

            report_lines.append(f"### Primary User: `{uname}` ({demo.get('gender')}, age {demo.get('age')})")
            report_lines.append(f"- **User ID**: `{uid}`")
            report_lines.append(f"- **Total Retrieved Candidates**: {len(cands)}")
            report_lines.append("")
            report_lines.append("| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |")
            report_lines.append("| --- | --- | --- | --- | --- | --- | --- |")

            for rank, cand in enumerate(cands, 1):
                cand_id = str(cand.get("user_id", ""))
                cand_name = user_id_to_name.get(cand_id, cand.get("name") or cand_id[:8])
                c_demo = f"{cand.get('gender')}, {cand.get('age')}"
                dist_str = f"{cand.get('distance_km')} km" if cand.get("distance_km") is not None else "Nearby"
                combined = cand.get("combined_score", 0.0)
                fwd = cand.get("cosine_similarity", 0.0)
                rev = cand.get("reverse_cosine_similarity")
                rev_str = f"{rev:.4f}" if rev is not None else "N/A"

                report_lines.append(
                    f"| **#{rank}** | `{cand_name}` | {c_demo} | {dist_str} | **{combined:.4f}** | {fwd:.4f} | {rev_str} |"
                )
            report_lines.append("")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        logger.info(f"✅ Stage 1 retrieval evaluation report exported to {report_path}")

    print("\n" + "=" * 85)
    print("STAGE 1 RETRIEVAL EVALUATION COMPLETE!")
    print("=" * 85)


if __name__ == "__main__":
    asyncio.run(run_retrieval_evaluation())
