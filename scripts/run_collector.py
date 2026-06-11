#!/usr/bin/env python3
"""
Run the job collector and print a summary of new jobs found.
Usage: python scripts/run_collector.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from rich.console import Console
from rich.table import Table

from pipeline.collector import run_all
from pipeline.database import stats

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
console = Console()


def main() -> None:
    console.print("\n[bold blue]Running job collector...[/bold blue]\n")

    results = run_all()
    total   = sum(results.values())

    table = Table(title="Collection Results", show_header=True, header_style="bold cyan")
    table.add_column("Source",   style="cyan", min_width=20)
    table.add_column("New jobs", justify="right", style="green")

    for source, count in results.items():
        table.add_row(source.capitalize(), str(count))

    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold green]{total}[/bold green]")
    console.print(table)

    db = stats()
    jobs = db.get("jobs", {})
    apps = db.get("applications", {})

    console.print(
        f"\n[dim]DB status — "
        f"new: {jobs.get('new', 0)}  "
        f"approved: {jobs.get('approved', 0)}  "
        f"applied: {jobs.get('applied', 0)}  "
        f"total applications: {sum(apps.values())}[/dim]\n"
    )

    if total > 0 and jobs.get("new", 0) > 0:
        from pipeline.exporter import export_new_jobs
        csv_path = export_new_jobs()
        if csv_path:
            console.print(f"\n[green]Review CSV created:[/green] {csv_path.name}")
            console.print(
                "[yellow]>> Open review/ CSV, fill 'action' column (approve/reject), "
                "then run: python scripts/import_review.py[/yellow]\n"
            )


if __name__ == "__main__":
    main()
