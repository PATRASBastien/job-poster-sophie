#!/usr/bin/env python3
"""
Export new jobs to a CSV for Sophie to review in Excel / Google Sheets.
Fill the 'action' column with:  approve | reject  (or leave blank to skip)
Then run: python scripts/import_review.py

Usage: python scripts/export_for_review.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.exporter import export_new_jobs


def main() -> None:
    csv_path = export_new_jobs()

    if not csv_path:
        print("No new jobs to export.")
        return

    print(f"Exported to: {csv_path}")
    print()
    print("Open in Excel or Google Sheets.")
    print("Fill the 'action' column:  approve | reject  (blank = skip)")
    print()
    print(f"When done, run:")
    print(f"  python scripts/import_review.py")


if __name__ == "__main__":
    main()
