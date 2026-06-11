"""
Tracker — appends a completed application to applications.csv.
Also syncs the applications table in the DB.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from .database import add_application, get_contacts, get_job

CONFIG_PATH  = Path(__file__).parent.parent / "config.yaml"
CSV_PATH     = Path(__file__).parent.parent / "applications.csv"

CSV_HEADERS = [
    "applied_date", "company", "job_title", "job_url", "source", "location",
    "contact_name", "contact_email", "contact_linkedin",
    "application_mode", "cv_path", "cover_letter_path",
    "status", "follow_up_date", "notes",
]


def _load_follow_up_days() -> int:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f).get("follow_up_days", 7)
    except Exception:
        return 7


def record_application(
    job_id: int,
    cv_path: str,
    cover_letter_path: str,
    application_mode: str = "manual",
    notes: str = "",
    csv_path: Path = CSV_PATH,
) -> None:
    """
    Write the application to both applications.csv and the DB.
    Creates the CSV with headers if it doesn't exist yet.
    """
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found in database.")

    follow_up_days = _load_follow_up_days()
    follow_up_date = (
        datetime.now() + timedelta(days=follow_up_days)
    ).strftime("%Y-%m-%d")
    applied_date = datetime.now().strftime("%Y-%m-%d")

    # Pull first contact if one exists
    contacts     = get_contacts(job_id)
    contact      = contacts[0] if contacts else None
    contact_name    = contact["name"]         if contact else ""
    contact_email   = contact["email"]        if contact else ""
    contact_linkedin = contact["linkedin_url"] if contact else ""

    row = {
        "applied_date":       applied_date,
        "company":            job["company"],
        "job_title":          job["title"],
        "job_url":            job["url"],
        "source":             job["source"],
        "location":           job["location"],
        "contact_name":       contact_name,
        "contact_email":      contact_email,
        "contact_linkedin":   contact_linkedin,
        "application_mode":   application_mode,
        "cv_path":            cv_path,
        "cover_letter_path":  cover_letter_path,
        "status":             "applied",
        "follow_up_date":     follow_up_date,
        "notes":              notes,
    }

    _append_csv(row, csv_path)

    add_application(
        job_id=job_id,
        cv_path=cv_path,
        cover_letter_path=cover_letter_path,
        application_mode=application_mode,
        follow_up_date=follow_up_date,
        notes=notes,
    )


def _append_csv(row: dict, csv_path: Path) -> None:
    needs_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)
