"""Run pending SQL migrations in order. Safe to re-run."""
import sqlite3
import os
import glob
import sys


def run_migrations(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        id INTEGER PRIMARY KEY, filename TEXT UNIQUE, applied_at TEXT)""")
    conn.commit()
    applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
    migration_dir = os.path.dirname(os.path.abspath(__file__))
    sql_files = sorted(glob.glob(os.path.join(migration_dir, "*.sql")))
    for f in sql_files:
        name = os.path.basename(f)
        if name not in applied:
            print(f"Applying {name}...")
            conn.executescript(open(f).read())
            conn.execute(
                "INSERT INTO schema_migrations(filename, applied_at) VALUES(?,datetime('now'))",
                (name,),
            )
            conn.commit()
            print(f"  done: {name}")
    conn.close()
    print("Migrations complete.")


if __name__ == "__main__":
    db = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("QUANTUM_DB_PATH", "quantum_portal.db")
    )
    run_migrations(db)
