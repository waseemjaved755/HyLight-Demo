"""
Supabase-style DB smoke test (sync psycopg2).
Run from backend/:  .venv/bin/python scripts/test_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import psycopg2

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    url = settings.sync_database_url
    print("Connecting with psycopg2 (Supabase Transaction pooler)...")
    conn = psycopg2.connect(url, sslmode="require")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("SELECT 1 =>", cur.fetchone()[0])
    cur.execute("SELECT to_regclass('public.users')")
    print("users table =>", cur.fetchone()[0])
    cur.close()
    conn.close()
    print("Database connection OK.")


if __name__ == "__main__":
    main()
