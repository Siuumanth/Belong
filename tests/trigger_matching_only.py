import asyncio
import json
import subprocess
import sys
import httpx

API_BASE = "http://localhost:8000"

# Fix Windows console UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def run_psql_query(query_sql: str):
    """Executes a SQL query against belong-postgres via docker exec."""
    json_query = f"SELECT json_agg(t) FROM ({query_sql}) t;"
    cmd = [
        "docker", "exec", "-i", "belong-postgres",
        "psql", "-U", "belong_user", "-d", "belong", "-t", "-A", "-c",
        json_query
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=False, check=True)
        out = res.stdout.decode('utf-8', errors='replace').strip()
        if not out or out == "null":
            return []
        return json.loads(out)
    except Exception as e:
        print(f"DB Error: {e}")
        return []

async def main():
    print("=" * 70)
    print("BELONG MATCH TRIGGER TEST (MATCHING ONLY)")
    print("=" * 70)

    # 1. Fetch available profiles from Postgres
    profiles = run_psql_query("""
        SELECT user_id, gender, relationship_goal, 
               (self_embedding IS NOT NULL) AS has_self_vec,
               (wants_embedding IS NOT NULL) AS has_wants_vec
        FROM profiles
        ORDER BY updated_at DESC
        LIMIT 5
    """)

    if not profiles:
        print("[ERROR] No profiles found in PostgreSQL.")
        return

    print("Found profiles in DB:")
    for r in profiles:
        print(f"  User {r['user_id']} | Gender: {r['gender']} | SelfVec: {r['has_self_vec']} | WantsVec: {r['has_wants_vec']}")

    target_user_id = str(profiles[0]["user_id"])
    print(f"\nTarget User for matching: {target_user_id}")

    # 2. Trigger matching via API with X-User-ID header
    headers = {"X-User-ID": target_user_id}
    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0) as client:
        print(f"Triggering POST /api/matches with header X-User-ID: {target_user_id}...")
        res = await client.post("/api/matches", headers=headers)
        if res.status_code not in (200, 202):
            print(f"[ERROR] Failed to request matches: {res.status_code} - {res.text}")
            return

        job_data = res.json()
        job_id = job_data.get("job_id")
        print(f"[OK] Match job queued! Job ID: {job_id}")

        # 3. Poll match job
        print("Polling job status...")
        for i in range(35):
            await asyncio.sleep(2)
            poll_res = await client.get(f"/api/matches/jobs/{job_id}")
            if poll_res.status_code == 200:
                poll_data = poll_res.json()
                status = poll_data.get("status")
                print(f"  [{(i+1)*2}s] Status: {status}")
                if status == "completed":
                    break
                elif status == "failed":
                    print(f"[ERROR] Job failed: {poll_data.get('error')}")
                    break
        else:
            print("[WARN] Polling timed out.")

        # 4. Fetch compatibility matches from API
        print("\nFetching match results from API...")
        match_res = await client.get(f"/api/matches/{target_user_id}", headers=headers)
        if match_res.status_code == 200:
            data = match_res.json()
            matches = data.get("matches", [])
            print(f"Total Matches Returned from API: {len(matches)}")
            for m in matches:
                print("\n" + "-" * 50)
                print(f"Matched User   : {m.get('matched_user_id')}")
                print(f"Overall Verdict: {m.get('overall_verdict')}")
                print(f"Combined Score : {m.get('combined_score')}")
                print(f"Reasoning      : {m.get('overall_reasoning')}")
                print(f"Alignments     : {m.get('complementary_alignments')}")
        else:
            print(f"Failed to fetch matches: {match_res.status_code} - {match_res.text}")

    # 5. Direct Database Verification
    c_rows = run_psql_query("""
        SELECT match_id, user_a_id, user_b_id, overall_reasoning,
               dimension_results, complementary_alignments, created_at
        FROM compatibility_results
        ORDER BY created_at DESC
        LIMIT 5
    """)
    print("\n" + "=" * 70)
    print(f"DIRECT DATABASE CHECK: {len(c_rows)} rows in compatibility_results")
    print("=" * 70)
    for cr in c_rows:
        dim_res = cr.get('dimension_results') or {}
        verdict = dim_res.get('overall_verdict', 'N/A') if isinstance(dim_res, dict) else 'N/A'
        print(f"Pair: {cr.get('user_a_id')} <-> {cr.get('user_b_id')}")
        print(f"Verdict: {verdict}")
        print(f"Reasoning: {cr.get('overall_reasoning')}")
        print(f"Created: {cr.get('created_at')}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
