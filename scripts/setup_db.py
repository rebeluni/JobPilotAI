"""
Database and Profile Setup CLI Script for JobPilot AI.
Initializes the SQLite database outside OneDrive, creates all 12 tables,
loads the configured candidate profile, and prints a verification audit summary.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from jobpilot.database.repository import Repository, get_default_db_path
from jobpilot.profiles.loader import ProfileLoader
from jobpilot.profiles.answer_bank import AnswerBank

# Force UTF-8 on Windows terminal if supported, or safe ascii fallback
console = Console(safe_box=True)


def setup():
    console.print(Panel.fit("[bold cyan]JobPilot AI - Database & Profile Initialization[/bold cyan]"))

    db_path = get_default_db_path()
    console.print(f"[bold]Target Database Path:[/bold] {db_path}")

    # Check if path is outside OneDrive
    if "onedrive" in db_path.lower():
        console.print("[bold yellow]WARNING:[/bold yellow] Database path appears to be inside OneDrive. It is strongly recommended to keep it outside (e.g. C:/Users/Ankita/Desktop/JobPilotData).")
    else:
        console.print("[bold green][OK][/bold green] Database location confirmed outside OneDrive.")

    repo = Repository(db_path)
    repo.init_db()
    console.print("[bold green][OK][/bold green] All 12 database tables successfully initialized.")

    # Profile loading
    loader = ProfileLoader()
    summary = loader.get_audit_summary()
    console.print(f"[bold]User profile loaded from:[/bold] {summary['profile_path']}")
    console.print(f"[bold green]Verified facts:[/bold green] {summary['verified_facts_count']} | [bold yellow]NEEDS_USER_INPUT:[/bold yellow] {summary['needs_user_input_count']}")

    # Answer bank audit
    ab = AnswerBank()
    ab_summary = ab.get_audit_summary()
    console.print(f"[bold]Answer bank loaded from:[/bold] {ab_summary['path']}")
    console.print(f"[bold green]Verified entries:[/bold green] {ab_summary['verified_entries']} | [bold yellow]NEEDS_USER_INPUT:[/bold yellow] {ab_summary['needs_user_input_entries']}")

    # Populate basic profile facts into user_profile table
    profile_data = loader.load()
    personal = profile_data.get("personal", {})
    if personal.get("full_name"):
        repo.set_profile_fact("full_name", personal["full_name"], is_verified=1)
    if personal.get("location_city"):
        repo.set_profile_fact("location_city", personal["location_city"], is_verified=1)
    if personal.get("location_country"):
        repo.set_profile_fact("location_country", personal["location_country"], is_verified=1)

    console.print("[bold green][OK] Setup complete! Database and profiles are ready for discovery and application processing.[/bold green]")


if __name__ == "__main__":
    setup()
