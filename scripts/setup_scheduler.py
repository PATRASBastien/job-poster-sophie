#!/usr/bin/env python3
"""
Set up Windows Task Scheduler to run the job collector daily.
Usage:
  python scripts/setup_scheduler.py           # defaults to 08:00
  python scripts/setup_scheduler.py --time 07:30
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent
BAT_FILE  = ROOT / "run_daily.bat"
TASK_NAME = "JobPosterSophie-Collector"


def main() -> None:
    parser = argparse.ArgumentParser(description="Register the daily collector in Windows Task Scheduler.")
    parser.add_argument("--time", default="08:00", metavar="HH:MM",
                        help="Time to run each day in 24h format (default: 08:00)")
    args = parser.parse_args()

    if not BAT_FILE.exists():
        print(f"Error: {BAT_FILE} not found.")
        print("Run this script from the project root or after cloning the repo.")
        sys.exit(1)

    # Validate time format
    try:
        h, m = args.time.split(":")
        assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except Exception:
        print(f"Error: --time must be HH:MM (e.g. 08:00), got '{args.time}'")
        sys.exit(1)

    print(f"Registering task '{TASK_NAME}' to run daily at {args.time}...")

    result = subprocess.run(
        [
            "schtasks", "/create",
            "/tn", TASK_NAME,
            "/tr", str(BAT_FILE),
            "/sc", "DAILY",
            "/st", args.time,
            "/f",                  # overwrite if already exists
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        log_path = ROOT / "logs" / "collector.log"
        print(f"\n✓ Task registered: '{TASK_NAME}'")
        print(f"  Schedule : every day at {args.time}")
        print(f"  Script   : {BAT_FILE}")
        print(f"  Log file : {log_path}")
        print()
        print("Useful commands:")
        print(f'  Run now   : schtasks /run /tn "{TASK_NAME}"')
        print(f'  Pause     : schtasks /change /tn "{TASK_NAME}" /disable')
        print(f'  Resume    : schtasks /change /tn "{TASK_NAME}" /enable')
        print(f'  Remove    : python scripts/remove_scheduler.py')
        print(f'  Change time: python scripts/setup_scheduler.py --time HH:MM')
    else:
        stderr = result.stderr.strip()
        print(f"\n✗ Failed to create task.")
        print(f"  {stderr}")
        print()
        if "Access is denied" in stderr or "privilege" in stderr.lower():
            print("Try running this script from an Administrator command prompt.")
        sys.exit(1)


if __name__ == "__main__":
    main()
