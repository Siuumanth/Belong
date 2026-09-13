import os
import glob
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "belong")
DB_USER = os.getenv("POSTGRES_USER", "belong_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "belong_password")

def get_connection_string() -> str:
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_connection():
    return psycopg.connect(get_connection_string(), row_factory=dict_row)

def run_migrations():
    """Apply all .sql migration scripts in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(glob.glob(str(migrations_dir / "*.sql")))

    print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT}...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create a simple migrations tracker table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            cur.execute("SELECT version FROM schema_migrations;")
            applied = {row["version"] for row in cur.fetchall()}

            for filepath in migration_files:
                filename = Path(filepath).name
                if filename in applied:
                    print(f"Skipping already applied migration: {filename}")
                    continue

                print(f"Applying migration: {filename}...")
                with open(filepath, "r", encoding="utf-8") as f:
                    sql = f.read()
                    cur.execute(sql)
                
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s);",
                    (filename,)
                )
                conn.commit()
                print(f"Successfully applied: {filename}")

    print("All migrations are up to date.")

if __name__ == "__main__":
    run_migrations()
