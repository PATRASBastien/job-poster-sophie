"""Export new jobs to a review CSV for Sophie to fill in Excel / Google Sheets."""

import csv
from datetime import datetime
from pathlib import Path

from .database import get_jobs

ROOT       = Path(__file__).parent.parent
REVIEW_DIR = ROOT / "review"

CSV_HEADERS = [
    "action",       # Sophie fills: approve | reject  (blank = skip)
    "id",
    "title",
    "company",
    "location",
    "source",
    "salary",
    "language_req",
    "posted_date",
    "url",
    "description",
]


def export_new_jobs() -> Path | None:
    """
    Write all 'new' jobs to a dated CSV in review/.
    Returns the CSV path, or None if there are no new jobs.
    """
    jobs = get_jobs(status="new")
    if not jobs:
        return None

    REVIEW_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = REVIEW_DIR / f"jobs_{date_str}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig adds BOM so Excel opens it without garbling accents
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for job in jobs:
            desc = (job["description"] or "").strip()
            writer.writerow({
                "action":       "",
                "id":           job["id"],
                "title":        job["title"],
                "company":      job["company"],
                "location":     job["location"],
                "source":       job["source"],
                "salary":       job["salary"],
                "language_req": job["language_req"],
                "posted_date":  job["posted_date"],
                "url":          job["url"],
                "description":  desc[:500] + ("..." if len(desc) > 500 else ""),
            })

    return csv_path
