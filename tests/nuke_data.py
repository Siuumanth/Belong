"""
Belong Platform - PostgreSQL Data Wipe Script (Python Edition)
===============================================================
Wipes all user profiles, conversations, messages, jobs, and match results
from the PostgreSQL database while preserving database schema & structure.

USAGE:
    python tests/nuke_data.py
"""

import subprocess

def nuke_data():
    print("==================================================================")
    print(">>> NUKING ALL BELONG POSTGRESQL DATA...")
    print("==================================================================")
    
    cmd = [
        "docker", "exec", "-i", "belong-postgres",
        "psql", "-U", "belong_user", "-d", "belong", "-c",
        "TRUNCATE TABLE profiles, conversations, conversation_messages, jobs, compatibility_results RESTART IDENTITY CASCADE;"
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout.strip())
        print("SUCCESS: All PostgreSQL data tables have been nuked clean!")
        print("==================================================================")
    except Exception as e:
        print(f"Error nuking database: {e}")

if __name__ == "__main__":
    nuke_data()
