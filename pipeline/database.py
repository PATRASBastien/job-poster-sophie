import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

_DEFAULT_DB = Path(__file__).parent.parent / "jobs.db"

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hash         TEXT    UNIQUE NOT NULL,
    title        TEXT    NOT NULL,
    company      TEXT    NOT NULL,
    url          TEXT    DEFAULT '',
    description  TEXT    DEFAULT '',
    requirements TEXT    DEFAULT '',
    location     TEXT    DEFAULT '',
    salary       TEXT    DEFAULT '',
    posted_date  TEXT    DEFAULT '',
    deadline     TEXT    DEFAULT '',
    source       TEXT    DEFAULT '',
    language_req TEXT    DEFAULT '',
    status       TEXT    NOT NULL DEFAULT 'new',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id       INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    name         TEXT    DEFAULT '',
    email        TEXT    DEFAULT '',
    linkedin_url TEXT    DEFAULT '',
    company      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS applications (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    applied_date      TEXT    NOT NULL,
    cv_path           TEXT    DEFAULT '',
    cover_letter_path TEXT    DEFAULT '',
    application_mode  TEXT    DEFAULT 'manual',
    status            TEXT    NOT NULL DEFAULT 'applied',
    follow_up_date    TEXT    DEFAULT '',
    notes             TEXT    DEFAULT '',
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# Valid job statuses in lifecycle order
JOB_STATUSES = ("new", "reviewed", "approved", "rejected", "applied", "followed_up", "closed")
APP_STATUSES  = ("applied", "interview", "offer", "rejected", "closed")


def _connect(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = _DEFAULT_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _job_hash(company: str, title: str, url: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Jobs ──────────────────────────────────────────────────────────────────────

def add_job(
    title: str,
    company: str,
    url: str = "",
    description: str = "",
    requirements: str = "",
    location: str = "",
    salary: str = "",
    posted_date: str = "",
    deadline: str = "",
    source: str = "",
    language_req: str = "",
    db_path: Path = _DEFAULT_DB,
) -> Optional[int]:
    """Insert a job. Returns its id, or None if it already exists (deduplication)."""
    h = _job_hash(company, title, url)
    with _connect(db_path) as conn:
        if conn.execute("SELECT 1 FROM jobs WHERE hash = ?", (h,)).fetchone():
            return None
        cur = conn.execute(
            """INSERT INTO jobs
               (hash, title, company, url, description, requirements,
                location, salary, posted_date, deadline, source, language_req)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (h, title, company, url, description, requirements,
             location, salary, posted_date, deadline, source, language_req),
        )
        return cur.lastrowid


def get_jobs(status: str = "new", db_path: Path = _DEFAULT_DB) -> list[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()


def get_job(job_id: int, db_path: Path = _DEFAULT_DB) -> Optional[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def update_job_status(job_id: int, status: str, db_path: Path = _DEFAULT_DB) -> None:
    if status not in JOB_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {JOB_STATUSES}")
    with _connect(db_path) as conn:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))


def search_jobs(query: str, db_path: Path = _DEFAULT_DB) -> list[sqlite3.Row]:
    like = f"%{query}%"
    with _connect(db_path) as conn:
        return conn.execute(
            """SELECT * FROM jobs
               WHERE title LIKE ? OR company LIKE ? OR description LIKE ?
               ORDER BY created_at DESC""",
            (like, like, like),
        ).fetchall()


# ── Contacts ──────────────────────────────────────────────────────────────────

def add_contact(
    job_id: int,
    name: str = "",
    email: str = "",
    linkedin_url: str = "",
    company: str = "",
    db_path: Path = _DEFAULT_DB,
) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO contacts (job_id, name, email, linkedin_url, company) VALUES (?,?,?,?,?)",
            (job_id, name, email, linkedin_url, company),
        )
        return cur.lastrowid


def get_contacts(job_id: int, db_path: Path = _DEFAULT_DB) -> list[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM contacts WHERE job_id = ?", (job_id,)
        ).fetchall()


# ── Applications ──────────────────────────────────────────────────────────────

def add_application(
    job_id: int,
    cv_path: str,
    cover_letter_path: str,
    application_mode: str = "manual",
    follow_up_date: str = "",
    notes: str = "",
    db_path: Path = _DEFAULT_DB,
) -> int:
    applied_date = datetime.now().strftime("%Y-%m-%d")
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO applications
               (job_id, applied_date, cv_path, cover_letter_path,
                application_mode, follow_up_date, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (job_id, applied_date, cv_path, cover_letter_path,
             application_mode, follow_up_date, notes),
        )
        conn.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", (job_id,))
        return cur.lastrowid


def update_application_status(
    application_id: int, status: str, db_path: Path = _DEFAULT_DB
) -> None:
    if status not in APP_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {APP_STATUSES}")
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?", (status, application_id)
        )


def get_applications(db_path: Path = _DEFAULT_DB) -> list[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            """SELECT a.*, j.title, j.company, j.url, j.location, j.source
               FROM applications a
               JOIN jobs j ON j.id = a.job_id
               ORDER BY a.applied_date DESC"""
        ).fetchall()


def get_due_followups(db_path: Path = _DEFAULT_DB) -> list[sqlite3.Row]:
    today = datetime.now().strftime("%Y-%m-%d")
    with _connect(db_path) as conn:
        return conn.execute(
            """SELECT a.*, j.title, j.company, j.url
               FROM applications a
               JOIN jobs j ON j.id = a.job_id
               WHERE a.status = 'applied'
                 AND a.follow_up_date != ''
                 AND a.follow_up_date <= ?
               ORDER BY a.follow_up_date""",
            (today,),
        ).fetchall()


# ── Stats ─────────────────────────────────────────────────────────────────────

def stats(db_path: Path = _DEFAULT_DB) -> dict:
    with _connect(db_path) as conn:
        job_counts = {
            row["status"]: row["cnt"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status"
            ).fetchall()
        }
        app_counts = {
            row["status"]: row["cnt"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM applications GROUP BY status"
            ).fetchall()
        }
    return {"jobs": job_counts, "applications": app_counts}
