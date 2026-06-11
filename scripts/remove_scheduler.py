#!/usr/bin/env python3
"""Remove the Windows Task Scheduler task for the daily job collector."""
import subprocess
import sys

TASK_NAME = "JobPosterSophie-Collector"

result = subprocess.run(
    ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
    capture_output=True,
    text=True,
)

if result.returncode == 0:
    print(f"✓ Task '{TASK_NAME}' removed from Windows Task Scheduler.")
else:
    print(f"✗ Could not remove task: {result.stderr.strip()}")
    sys.exit(1)
