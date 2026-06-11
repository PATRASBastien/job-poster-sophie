#!/usr/bin/env python3
"""
Follow-up reminder — lists applications whose follow-up date has passed.
Usage: python scripts/followup.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import webbrowser
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from pipeline.database import get_due_followups, update_application_status

console = Console()


def main() -> None:
    due = get_due_followups()

    if not due:
        console.print("\n[green]✓ No follow-ups due today.[/green]\n")
        return

    console.print(f"\n[bold yellow]⏰ {len(due)} follow-up(s) due:[/bold yellow]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#",            width=4)
    table.add_column("Company",      style="cyan",  min_width=18)
    table.add_column("Role",         min_width=22)
    table.add_column("Applied",      width=12)
    table.add_column("Follow-up",    width=12, style="yellow")
    table.add_column("Contact",      min_width=20, style="dim")

    for idx, app in enumerate(due, start=1):
        table.add_row(
            str(idx),
            app["company"],
            app["title"],
            app["applied_date"],
            app["follow_up_date"],
            app["contact_email"] or app["contact_name"] or "—",
        )

    console.print(table)
    console.print("\n[dim]Commands: [o]pen URL  [d]one (mark followed up)  [s]kip  [q]uit[/dim]\n")

    for app in due:
        console.print(
            f"[bold]{app['company']}[/bold] — {app['title']}  "
            f"[dim](applied {app['applied_date']})[/dim]"
        )
        if app["url"]:
            console.print(f"  🔗 {app['url']}", style="dim blue")

        choice = Prompt.ask(
            "  Action",
            choices=["o", "d", "s", "q"],
            default="s",
            show_choices=False,
        ).strip().lower()

        if choice == "o":
            if app["url"]:
                webbrowser.open(app["url"])
                console.print("  [dim]Opened in browser.[/dim]")
            else:
                console.print("  [yellow]No URL available.[/yellow]")
            choice = Prompt.ask("  Mark as followed up?", choices=["y", "n"], default="y")
            if choice == "y":
                update_application_status(app["id"], "followed_up")
                console.print("  [green]✓ Marked as followed up.[/green]")
        elif choice == "d":
            update_application_status(app["id"], "followed_up")
            console.print("  [green]✓ Marked as followed up.[/green]")
        elif choice == "s":
            console.print("  [dim]Skipped.[/dim]")
        elif choice == "q":
            console.print("\n[dim]Quit early.[/dim]\n")
            return

        console.print()


if __name__ == "__main__":
    main()
