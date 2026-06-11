#!/usr/bin/env python3
"""
Run the Claude adapter for all approved jobs.
Generates a tailored CV + cover letter for each and saves them to output/.
Usage: python scripts/run_adapter.py
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
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pipeline.adapter import adapt_all_approved
from pipeline.database import get_jobs

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
console = Console()


def main() -> None:
    approved = get_jobs(status="approved")

    if not approved:
        console.print("\n[yellow]No approved jobs to adapt.[/yellow]")
        console.print("[dim]Run python scripts/review.py first to approve jobs.[/dim]\n")
        return

    console.print(f"\n[bold blue]Adapting {len(approved)} approved job(s)...[/bold blue]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Calling Claude...", total=None)
        results = adapt_all_approved()
        progress.update(task, completed=True)

    if not results:
        console.print("[dim]All jobs already adapted — nothing new to do.[/dim]\n")
        return

    # Summary table
    table = Table(title="Adaptation Results", header_style="bold cyan")
    table.add_column("Company",     style="cyan",  min_width=20)
    table.add_column("Role",        min_width=24)
    table.add_column("Match",       justify="center", width=8)
    table.add_column("PDF",         justify="center", width=6)
    table.add_column("Output",      style="dim",   min_width=30)

    for r in results:
        job = r.get("job", {})
        if "error" in r:
            table.add_row(
                job.get("company", "?"),
                job.get("title", "?"),
                "[red]ERROR[/red]",
                "—",
                r["error"][:50],
            )
            continue

        score    = r.get("match_score", "?")
        score_str = _score_colour(score)
        pdf_str  = "[green]✓[/green]" if r.get("pdf_generated") else "[dim]—[/dim]"
        out_path = str(r["output_dir"].relative_to(Path.cwd())) if r.get("output_dir") else "—"

        table.add_row(job.get("company", "?"), job.get("title", "?"), score_str, pdf_str, out_path)

    console.print(table)

    # Detail panels for each successful result
    for r in results:
        if "error" in r:
            continue
        job = r["job"]
        themes = ", ".join(r.get("key_themes", []))
        notes  = r.get("match_notes", "")
        out    = r.get("output_dir", Path("output"))

        console.print(Panel(
            f"[bold]{job['company']}[/bold] — {job['title']}\n\n"
            f"[cyan]Key themes:[/cyan] {themes}\n\n"
            f"[cyan]Match notes:[/cyan] {notes}\n\n"
            f"[dim]Files:\n"
            f"  {out / 'cv_adapted.md'}\n"
            f"  {out / 'cover_letter.md'}[/dim]",
            title=f"[bold]Match score: {r.get('match_score', '?')}[/bold]",
            border_style="green" if (r.get("match_score") or 0) >= 70 else "yellow",
            padding=(1, 2),
        ))

    console.print(
        "\n[yellow]▶ Review the generated documents, then run "
        "[bold]python scripts/apply.py[/bold] to record your applications.[/yellow]\n"
    )


def _score_colour(score) -> str:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return str(score)
    if s >= 75:
        return f"[bold green]{s}[/bold green]"
    if s >= 50:
        return f"[yellow]{s}[/yellow]"
    return f"[red]{s}[/red]"


if __name__ == "__main__":
    main()
