import sqlite3
from pathlib import Path

from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the SQLite database and create required tables if they do not exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Certificates table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            register_number TEXT NOT NULL,
            course TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            student_email TEXT NOT NULL,
            cid TEXT NOT NULL,
            blockchain_index INTEGER NOT NULL,
            pdf_filename TEXT NOT NULL,
            image_filename TEXT NOT NULL,
            image_data BLOB,
            created_at TEXT NOT NULL
        );
        """
    )

    conn.commit()
    conn.close()
    _ensure_columns()


def _ensure_columns():
    """Add new columns for AI and blockchain metadata if missing."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(certificates)")
    cols = [row[1] for row in cur.fetchall()]
    # Add ai_score, heatmap, blockchain_tx, image_data if they don't exist
    if "department" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN department TEXT DEFAULT ''")
    if "year" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN year TEXT DEFAULT ''")
    if "student_email" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN student_email TEXT DEFAULT ''")
    if "ai_score" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN ai_score REAL DEFAULT NULL")
    if "heatmap" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN heatmap TEXT DEFAULT NULL")
    if "blockchain_tx" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN blockchain_tx TEXT DEFAULT NULL")
    if "image_data" not in cols:
        cur.execute("ALTER TABLE certificates ADD COLUMN image_data BLOB DEFAULT NULL")
    conn.commit()
    conn.close()


def init_db_with_columns() -> None:
    init_db()
    _ensure_columns()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {Path(DATABASE_PATH)}")

