#!/usr/bin/env python3
"""
Read a reviewed CSV and update job statuses in the DB.
Run after Sophie has filled the 'action' column in the review CSV.

Usage:
  python scripts/import_review.py                    # auto-finds latest review CSV
  python scripts/import_review.py jobs_2026-06-08.csv
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.database import update_job_status

ROOT       = Path(__file__).parent.parent
REVIEW_DIR = ROOT / "review"


def _latest_csv() -> Path | None:
    csvs = sorted(REVIEW_DIR.glob("jobs_*.csv"), reverse=True)
    return csvs[0] if csvs else None


def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        csv_path = Path(arg) if Path(arg).is_absolute() else REVIEW_DIR / arg
    else:
        csv_path = _latest_csv()

    if not csv_path or not csv_path.exists():
        print("No review CSV found. Run: python scripts/export_for_review.py first.")
        sys.exit(1)

    print(f"Importing: {csv_path.name}")

    approved = rejected = skipped = errors = 0

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = row.get("action", "").strip().lower()
            try:
                job_id = int(row["id"])
            except (ValueError, KeyError):
                errors += 1
                continue

            if action in ("approve", "approved", "a", "yes", "y", "oui", "o"):
                update_job_status(job_id, "approved")
                approved += 1
            elif action in ("reject", "rejected", "r", "no", "n", "non"):
                update_job_status(job_id, "rejected")
                rejected += 1
            else:
                skipped += 1

    print()
    print(f"  Approved : {approved}")
    print(f"  Rejected : {rejected}")
    print(f"  Skipped  : {skipped} (blank action — stays as 'new')")
    if errors:
        print(f"  Errors   : {errors} rows skipped (bad id)")
    print()

    if approved > 0:
        print(f"Run next: python scripts/run_adapter.py")


if __name__ == "__main__":
    main()
