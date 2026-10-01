"""
Small Script: Fetch Candidate Matches using X-User-ID Header
============================================================
Sends a POST request to `/matches/candidates` using the `X-User-ID` header
(simulating requests coming through the Go Auth Gateway).

USAGE:
    python tests/test_find_matches_header.py [<user_id>]
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
import httpx
import psycopg
from psycopg.rows import dict_row

API_URL = os.getenv("BELONG_API_URL", "http://localhost:8000")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "belong")
DB_USER = os.getenv("POSTGRES_USER", "belong_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "belong_password")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Fix Windows console UTF-8 output encoding & psycopg event loop
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


async def fetch_sample_user_id() -> Optional[str]:
    """Fetches the first registered user profile ID from PostgreSQL database."""
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id, name, gender, age FROM profiles ORDER BY created_at ASC LIMIT 1;")
                row = await cur.fetchone()
                if row:
                    print(f"📋 Selected User from DB: {row['name']} ({row['gender']}, age {row['age']}) | ID: {row['user_id']}")
                    return str(row["user_id"])
    except Exception as e:
        print(f"⚠️ Error querying DB for sample user: {e}")
    return None


async def fetch_matches_with_header(user_id: str):
    headers = {
        "X-User-ID": user_id,
        "Content-Type": "application/json"
    }

    print("\n" + "=" * 70)
    print(f"🚀 Fetching Candidate Matches for User ID: {user_id}")
    print(f"   Header: X-User-ID = {user_id}")
    print("=" * 70)

    urls_to_try = [API_URL]
    if API_URL == "http://localhost:8000":
        urls_to_try.append("http://127.0.0.1:8000")
    elif API_URL == "http://127.0.0.1:8000":
        urls_to_try.append("http://localhost:8000")

    res = None
    last_err = None

    for url in urls_to_try:
        try:
            async with httpx.AsyncClient(base_url=url, timeout=60.0) as client:
                res = await client.post("/matches/candidates", headers=headers, json={})
                if res.status_code == 200:
                    break
        except httpx.HTTPError as ce:
            last_err = ce
            continue

    if res is None or res.status_code != 200:
        if res is not None:
            print(f"❌ Error {res.status_code}: {res.text}")
        else:
            print(f"❌ Could not connect to API server at {urls_to_try}. Error: {last_err}")
        return

    data = res.json()
    candidates = data.get("candidates", [])

    print(f"✅ Found {len(candidates)} candidate matches!\n")

    for rank, cand in enumerate(candidates, 1):
        cand_id = cand.get("user_id")
        cand_name = cand.get("name") or str(cand_id)[:8]
        dist_km = cand.get("distance_km")
        dist_str = f"{dist_km} km" if dist_km is not None else "Nearby"
        fwd_sim = cand.get("cosine_similarity", 0.0)
        rev_sim = cand.get("reverse_cosine_similarity")
        rev_str = f"{rev_sim:.4f}" if rev_sim is not None else "N/A"
        combined = cand.get("combined_score", 0.0)
        compat_pct = cand.get("compatibility_percentage", 0)

        print(f"  [{rank}] Candidate: {cand_name.upper():<16} ({cand.get('gender')}, age {cand.get('age')})")
        print(f"      ├─ ID:                  {cand_id}")
        print(f"      ├─ Distance:            {dist_str}")
        print(f"      ├─ Forward Sim (A->B): {fwd_sim:.4f}")
        print(f"      ├─ Reverse Sim (B->A): {rev_str}")
        print(f"      ├─ Combined Score:      {combined:.4f}")
        print(f"      └─ 🎯 Compatibility:     {compat_pct}%")
        print()


async def main():
    target_user_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not target_user_id:
        target_user_id = await fetch_sample_user_id()

    if not target_user_id:
        print("❌ No user ID provided and no profiles found in database.")
        sys.exit(1)

    await fetch_matches_with_header(target_user_id)


if __name__ == "__main__":
    asyncio.run(main())
