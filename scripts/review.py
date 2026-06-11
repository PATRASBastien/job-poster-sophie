#!/usr/bin/env python3
"""
Interactive review CLI — browse new jobs one by one, approve or reject.
Approved jobs are queued for CV/cover letter adaptation.
Usage: python scripts/review.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import webbrowser

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from pipeline.database import get_jobs, update_job_status, stats

console = Console()


def _status_badge(language_req: str) -> str:
    if language_req:
        return f"[bold red]⚠ {language_req}[/bold red]"
    return "[green]✓ No language restriction[/green]"


def _render_job(job, index: int, total: int) -> Panel:
    lang_badge = _status_badge(job["language_req"])
    content = Text.assemble(
        (f"[{index}/{total}]  ", "dim"),
        (job["title"], "bold white"),
        "\n",
        ("Company:  ", "dim"), (job["company"] or "—", "cyan"),
        "\n",
        ("Location: ", "dim"), (job["location"] or "—", ""),
        "\n",
        ("Source:   ", "dim"), (job["source"] or "—", ""),
        "\n",
        ("Salary:   ", "dim"), (job["salary"] or "—", ""),
        "\n",
        ("Posted:   ", "dim"), (job["posted_date"] or "—", ""),
        "\n\n",
    )
    if job["description"]:
        excerpt = job["description"][:600].strip()
        if len(job["description"]) > 600:
            excerpt += "…"
        content.append(excerpt, style="dim")

    content.append("\n\n")
    content.append_text(Text.from_markup(lang_badge))

    if job["url"]:
        content.append(f"\n🔗 {job['url']}", style="dim blue")

    return Panel(content, title="[bold]Job Review[/bold]", border_style="blue", padding=(1, 2))


def main() -> None:
    jobs = get_jobs(status="new")

    if not jobs:
        console.print("\n[green]✓ No new jobs to review.[/green]\n")
        db = stats()
        j = db.get("jobs", {})
        console.print(
            f"[dim]DB: {j.get('approved', 0)} approved · "
            f"{j.get('applied', 0)} applied · "
            f"{j.get('rejected', 0)} rejected[/dim]\n"
        )
        return

    console.print(f"\n[bold blue]{len(jobs)} new job(s) to review.[/bold blue]")
    console.print("[dim]Commands: [a]pprove  [r]eject  [s]kip  [o]pen in browser  [q]uit[/dim]\n")

    approved = rejected = skipped = 0

    for i, job in enumerate(jobs, start=1):
        console.print(_render_job(job, i, len(jobs)))

        while True:
            choice = Prompt.ask(
                "[bold]Action[/bold]",
                choices=["a", "r", "s", "o", "q"],
                default="s",
                show_choices=False,
            ).strip().lower()

            if choice == "a":
                update_job_status(job["id"], "approved")
                console.print(f"[green]✓ Approved:[/green] {job['title']} @ {job['company']}\n")
                approved += 1
                break
            elif choice == "r":
                update_job_status(job["id"], "rejected")
                console.print(f"[red]✗ Rejected:[/red] {job['title']} @ {job['company']}\n")
                rejected += 1
                break
            elif choice == "s":
                console.print("[dim]Skipped (stays as 'new')[/dim]\n")
                skipped += 1
                break
            elif choice == "o":
                if job["url"]:
                    webbrowser.open(job["url"])
                    console.print("[dim]Opened in browser.[/dim]")
                else:
                    console.print("[yellow]No URL available.[/yellow]")
            elif choice == "q":
                console.print("\n[dim]Quit early.[/dim]")
                _print_summary(approved, rejected, skipped)
                return

    _print_summary(approved, rejected, skipped)

    if approved > 0:
        console.print(
            f"[yellow]▶ Run [bold]python scripts/run_adapter.py[/bold] to generate "
            f"tailored CV + cover letters for {approved} approved job(s).[/yellow]\n"
        )


def _print_summary(approved: int, rejected: int, skipped: int) -> None:
    console.print(
        f"\n[bold]Session summary:[/bold] "
        f"[green]{approved} approved[/green]  "
        f"[red]{rejected} rejected[/red]  "
        f"[dim]{skipped} skipped[/dim]\n"
    )


if __name__ == "__main__":
    main()
