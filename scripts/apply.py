#!/usr/bin/env python3
"""
Apply skill — walks Sophie through submitting each adapted application manually,
then records the submission in applications.csv and the DB.

Usage: python scripts/apply.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import webbrowser
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.text import Text

from pipeline.database import get_jobs, get_job, get_contacts, update_job_status
from pipeline.tracker import record_application

console = Console()

ROOT       = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"


def _find_output(job) -> Path | None:
    """Find the most recent output folder for this job."""
    slug = _slugify(job["company"])
    matches = sorted(OUTPUT_DIR.glob(f"{slug}_{job['id']}_*"), reverse=True)
    return matches[0] if matches else None


def _slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40]


def _load_meta(out_dir: Path) -> dict:
    meta_path = out_dir / "meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def _render_checklist(job, out_dir: Path) -> None:
    meta        = _load_meta(out_dir)
    cv_path     = out_dir / "cv_adapted.md"
    cl_path     = out_dir / "cover_letter.md"
    cv_pdf      = out_dir / "cv_adapted.pdf"
    cl_pdf      = out_dir / "cover_letter.pdf"
    themes      = ", ".join(meta.get("key_themes", []))
    score       = meta.get("match_score", "?")
    notes       = meta.get("match_notes", "")

    console.print(Panel(
        Text.assemble(
            ("Company:  ", "dim"), (job["company"], "bold cyan"), "\n",
            ("Role:     ", "dim"), (job["title"],   "bold white"), "\n",
            ("Location: ", "dim"), (job["location"] or "—", ""), "\n",
            ("Source:   ", "dim"), (job["source"]   or "—", ""), "\n\n",
            ("Match score: ", "dim"), (str(score), "bold green" if str(score).isdigit() and int(score) >= 70 else "yellow"), "\n",
            ("Themes:   ", "dim"), (themes, ""), "\n\n",
            (notes, "dim"),
        ),
        title="[bold]Application Summary[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))

    console.print("[bold cyan]Pre-submission checklist:[/bold cyan]\n")

    # 1. Review documents
    cv_file  = cv_pdf  if cv_pdf.exists()  else cv_path
    cl_file  = cl_pdf  if cl_pdf.exists()  else cl_path

    console.print(f"  [dim]1.[/dim] CV:           [blue]{cv_file}[/blue]")
    console.print(f"  [dim]2.[/dim] Cover letter: [blue]{cl_file}[/blue]")
    if job["url"]:
        console.print(f"  [dim]3.[/dim] Job URL:      [blue]{job['url']}[/blue]")

    contacts = get_contacts(job["id"])
    if contacts:
        c = contacts[0]
        if c["email"]:
            console.print(f"  [dim]4.[/dim] Contact:      {c['name']} <{c['email']}>")

    console.print()


def _ask_open(label: str, path: Path) -> None:
    if path.exists():
        if Confirm.ask(f"  Open {label} now?", default=True):
            import os
            os.startfile(str(path))  # Windows — opens with default app


def main() -> None:
    jobs = get_jobs(status="approved")

    # Filter to only those that have been adapted (output folder exists)
    ready = [(job, _find_output(job)) for job in jobs]
    ready = [(job, out) for job, out in ready if out is not None]

    if not ready:
        console.print("\n[yellow]No adapted applications ready to submit.[/yellow]")
        console.print("[dim]Run python scripts/run_adapter.py first.[/dim]\n")
        return

    console.print(f"\n[bold blue]{len(ready)} application(s) ready to submit.[/bold blue]")
    console.print("[dim]For each: review docs → open job URL → submit → confirm here.[/dim]\n")

    submitted = skipped = 0

    for job, out_dir in ready:
        console.print(Rule(style="dim"))
        _render_checklist(job, out_dir)

        cv_pdf = out_dir / "cv_adapted.pdf"
        cl_pdf = out_dir / "cover_letter.pdf"
        cv_md  = out_dir / "cv_adapted.md"
        cl_md  = out_dir / "cover_letter.md"
        cv_file = cv_pdf if cv_pdf.exists() else cv_md
        cl_file = cl_pdf if cl_pdf.exists() else cl_md

        # Offer to open documents
        _ask_open("CV", cv_file)
        _ask_open("cover letter", cl_file)

        # Offer to open job URL
        if job["url"]:
            if Confirm.ask("  Open job URL in browser?", default=True):
                webbrowser.open(job["url"])

        console.print()
        console.print("[bold yellow]→ Submit your application now, then come back here.[/bold yellow]")
        console.print()

        action = Prompt.ask(
            "  Did you submit?",
            choices=["y", "s", "q"],
            default="y",
            show_choices=False,
            show_default=False,
            prompt_suffix=" ([green]y[/green]=yes  [dim]s[/dim]=skip  [dim]q[/dim]=quit) ",
        )

        if action == "y":
            mode = Prompt.ask(
                "  Application mode",
                choices=["manual", "email", "linkedin"],
                default="manual",
            )
            notes = Prompt.ask("  Notes (optional)", default="")

            record_application(
                job_id=job["id"],
                cv_path=str(cv_file.relative_to(ROOT)),
                cover_letter_path=str(cl_file.relative_to(ROOT)),
                application_mode=mode,
                notes=notes,
            )
            console.print(f"  [green]✓ Recorded — follow-up scheduled in 7 days.[/green]\n")
            submitted += 1

        elif action == "s":
            console.print("  [dim]Skipped — job stays in approved queue.[/dim]\n")
            skipped += 1

        elif action == "q":
            console.print("\n[dim]Quit early.[/dim]")
            break

    console.print(Rule(style="dim"))
    console.print(
        f"\n[bold]Session:[/bold] "
        f"[green]{submitted} submitted[/green]  "
        f"[dim]{skipped} skipped[/dim]\n"
    )

    if submitted > 0:
        console.print(
            "[dim]Applications recorded in [bold]applications.csv[/bold]. "
            "Run [bold]python scripts/followup.py[/bold] to check for due follow-ups.[/dim]\n"
        )


if __name__ == "__main__":
    main()
