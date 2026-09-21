"""
Belong Platform - Comprehensive Profile, Onboarding & Compatibility Inspector
============================================================================
Fetches the 2 latest user profiles, maps their individual onboarding dialogues
(Q&A), displays the latest compatibility match result, AND saves the complete
log into `results.md`.

USAGE:
    python tests/get_latest_results.py
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
TESTS_DIR = Path(__file__).parent
RESULTS_FILE = TESTS_DIR / "results.md"


class TeeOutput:
    """Duplicates stdout writes to both console and a markdown file."""

    def __init__(self, filepath: Path):
        self.file = open(filepath, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data: str):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def run_psql_query(query_sql: str):
    """Executes a SQL query against belong-postgres and returns parsed JSON array."""
    json_query = f"SELECT json_agg(t) FROM ({query_sql}) t;"
    cmd = [
        "docker", "exec", "-i", "belong-postgres",
        "psql", "-U", "belong_user", "-d", "belong", "-t", "-A", "-c",
        json_query
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        if not out or out == "null":
            return []
        return json.loads(out)
    except Exception as e:
        print(f"Error executing psql query via docker: {e}")
        return None


def print_user_conversation(user_id: str):
    """Fetches and prints all onboarding Q&A messages for a given user_id."""
    conv_sql = f"""
        SELECT 
            c.id AS conversation_id,
            c.user_id,
            c.status,
            c.created_at,
            (
                SELECT json_agg(m ORDER BY m.created_at ASC)
                FROM conversation_messages m
                WHERE m.conversation_id = c.id
            ) AS messages
        FROM conversations c
        WHERE c.user_id = '{user_id}'
        ORDER BY c.created_at DESC
        LIMIT 1
    """
    conv_list = run_psql_query(conv_sql)
    if not conv_list or not conv_list[0].get("messages"):
        print("   Onboarding Dialogue: (No conversation recorded for this profile)\n")
        return

    conv = conv_list[0]
    messages = conv.get("messages", [])
    print(f"   Conversation ID : {conv.get('conversation_id')}")
    print(f"   Status          : {conv.get('status')}")
    print(f"   Started At      : {conv.get('created_at')}\n")

    q_num = 1
    for i in range(len(messages)):
        msg = messages[i]
        role = msg.get("role")
        content = msg.get("content")
        q_id = msg.get("question_id")

        if role == "assistant":
            q_tag = f" ({q_id})" if q_id else ""
            print(f"   Q{q_num}{q_tag}: {content}")
        elif role == "user":
            print(f"   A{q_num}: {content}\n")
            q_num += 1


def fetch_and_print_latest_data():
    print("=" * 85)
    print("         BELONG PLATFORM - COMPLETE PROFILES, DIALOGUES & MATCH INSPECTOR")
    print("=" * 85)

    # Fetch 2 Latest Profiles
    profiles_sql = """
        SELECT 
            user_id,
            name,
            age,
            gender,
            orientation,
            relationship_goal,
            latitude,
            longitude,
            preferred_age_min,
            preferred_age_max,
            max_distance_km,
            preferred_genders,
            required_relationship_goal,
            created_at,
            profile
        FROM profiles
        ORDER BY created_at DESC
        LIMIT 2
    """
    profiles = run_psql_query(profiles_sql)
    if profiles is None:
        print("Error: Could not connect to PostgreSQL container 'belong-postgres'.")
        sys.exit(1)

    if not profiles:
        print("\nNo profiles found in the database.")
    else:
        for idx, p in enumerate(profiles, start=1):
            user_id = p.get('user_id')
            user_name = p.get('name') or '<No Name>'
            print(f"\n================================================================================")
            print(f"USER PROFILE #{idx}: {user_name} (User ID: {user_id})")
            print(f"================================================================================")
            print(f"Age / Gender       : {p.get('age')} / {p.get('gender')}")
            print(f"Orientation / Goal : {p.get('orientation')} / {p.get('relationship_goal')}")
            print(f"Location (Lat/Lon) : {p.get('latitude')}, {p.get('longitude')}")
            print(f"Preferences        : Age {p.get('preferred_age_min')}-{p.get('preferred_age_max')}, Dist {p.get('max_distance_km')}km, Genders {p.get('preferred_genders')}")
            print(f"Created At         : {p.get('created_at')}")
            print("\nExtracted Profile JSON:")
            print(json.dumps(p.get("profile"), indent=2))

            print("\n--------------------------------------------------------------------------------")
            print(f"ONBOARDING DIALOGUE FOR PROFILE #{idx} ({user_name})")
            print("--------------------------------------------------------------------------------")
            print_user_conversation(user_id)

    # Fetch Single Latest Compatibility Result
    print("\n================================================================================")
    print("LATEST COMPATIBILITY MATCH RESULT")
    print("================================================================================")
    results_sql = """
        SELECT 
            id,
            user_a_id,
            user_b_id,
            dimension_results,
            strong_alignments,
            potential_conflicts,
            dealbreaker_violations,
            uncertainties,
            model_name,
            reasoning_version,
            created_at
        FROM compatibility_results
        ORDER BY created_at DESC
        LIMIT 1
    """
    results = run_psql_query(results_sql)
    if not results:
        print("No compatibility results found in database.")
    else:
        r = results[0]
        print(f"Match Record ID : {r.get('id')}")
        print(f"User A ID       : {r.get('user_a_id')}")
        print(f"User B ID       : {r.get('user_b_id')}")
        print(f"Model / Version : {r.get('model_name')} ({r.get('reasoning_version')})")
        print(f"Created At      : {r.get('created_at')}")
        print("\nDimension Results:")
        print(json.dumps(r.get("dimension_results"), indent=2))
        print("\nStrong Alignments:")
        print(json.dumps(r.get("strong_alignments"), indent=2))
        print("\nPotential Conflicts:")
        print(json.dumps(r.get("potential_conflicts"), indent=2))
        print("\nDealbreaker Violations:")
        print(json.dumps(r.get("dealbreaker_violations"), indent=2))
        print("\nUncertainties:")
        print(json.dumps(r.get("uncertainties"), indent=2))

    print("\n" + "=" * 85)
    print("INSPECTION COMPLETED")
    print("=" * 85)


if __name__ == "__main__":
    tee = TeeOutput(RESULTS_FILE)
    sys.stdout = tee
    try:
        fetch_and_print_latest_data()
        print(f"\n[INFO] Log saved to: {RESULTS_FILE}")
    finally:
        sys.stdout = tee.stdout
        tee.close()
