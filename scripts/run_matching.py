"""
CLI Matching Script for JobPilot AI.
Loads unranked jobs from the SQLite database, executes 2-stage hybrid matching
against candidate profile, updates database records, and prints shortlisted opportunities.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jobpilot.database.repository import Repository, get_default_db_path
from jobpilot.core.schemas import JobRecord, MatchStatus
from jobpilot.matching.engine import MatchingEngine
from jobpilot.profiles.loader import ProfileLoader

console = Console(safe_box=True)


async def execute_matching(limit: int = 50, min_score: float = 0.50):
    console.print(Panel.fit("[bold cyan]JobPilot AI - Job Matching Engine[/bold cyan]"))

    repo = Repository(get_default_db_path())
    repo.init_db()

    # Load candidate profile
    loader = ProfileLoader()
    summary = loader.get_audit_summary()
    console.print(f"[bold]Candidate Profile:[/bold] {summary['profile_path']}")
    console.print(f"[dim]Verified facts: {summary['verified_facts_count']} | NEEDS_USER_INPUT: {summary['needs_user_input_count']}[/dim]")

    # Fetch jobs from database
    db_jobs = repo.list_jobs(limit=limit)
    if not db_jobs:
        console.print("[yellow]No jobs found in database. Run 'python scripts/run_discovery.py' first![/yellow]")
        return

    console.print(f"[bold]Loaded {len(db_jobs)} jobs for matching evaluation...[/bold]")

    # Convert to JobRecord instances
    import json
    job_records = []
    for j in db_jobs:
        skills = json.loads(j.skills) if j.skills else []
        record = JobRecord(
            job_id=j.job_id,
            company=j.company,
            title=j.title,
            description=j.description,
            location=j.location,
            country=j.country,
            remote_policy=j.remote_policy,
            employment_type=j.employment_type,
            salary_min=j.salary_min,
            salary_max=j.salary_max,
            currency=j.currency,
            experience_min=j.experience_min,
            experience_max=j.experience_max,
            skills=skills,
            job_url=j.job_url,
            source=j.source,
            date_found=j.date_found,
            visa_status=j.visa_status,
        )
        job_records.append(record)

    engine = MatchingEngine()
    results = await engine.match_batch(job_records)

    # Persist updated match scores to database
    shortlist_count = 0
    for r in results:
        repo.upsert_job({
            "job_id": r.job_id,
            "match_score": r.match_score,
            "match_status": r.match_status.value if hasattr(r.match_status, "value") else str(r.match_status),
            "recommended_resume": r.recommended_variant,
            "match_reasoning": {
                "dimensions": r.dimension_scores,
                "pros": r.pros,
                "cons": r.cons,
                "concerns": r.concerns,
                "reasoning": r.reasoning,
            },
            "status": "SHORTLISTED" if r.match_score >= min_score else "EVALUATED",
        })
        if r.match_score >= min_score:
            shortlist_count += 1

    # Output Rich Table
    table = Table(title="Top Matched Opportunities")
    table.add_column("Score", style="bold green", width=8)
    table.add_column("Status", style="bold", width=14)
    table.add_column("Title", style="cyan", width=25)
    table.add_column("Company", style="magenta", width=20)
    table.add_column("Country / Remote", style="blue", width=18)
    table.add_column("Resume Variant", style="yellow", width=18)

    for r in results[:15]:
        target_job = next((j for j in job_records if j.job_id == r.job_id), None)
        if not target_job:
            continue
        status_str = r.match_status.value if hasattr(r.match_status, "value") else str(r.match_status)
        score_pct = f"{int(r.match_score * 100)}%"
        rem_str = target_job.remote_policy.value if hasattr(target_job.remote_policy, "value") else str(target_job.remote_policy)
        table.add_row(
            score_pct,
            status_str,
            target_job.title[:24],
            target_job.company[:19],
            f"{target_job.country or 'Any'} ({rem_str})",
            r.recommended_variant,
        )

    console.print(table)
    console.print(f"[bold green][OK] Matching complete! {shortlist_count} opportunities qualified for shortlist.[/bold green]")


@click.command()
@click.option("--limit", "-l", default=50, help="Maximum number of jobs to evaluate.")
@click.option("--min-score", "-m", default=0.50, help="Minimum score threshold for shortlist.")
def main(limit, min_score):
    asyncio.run(execute_matching(limit=limit, min_score=min_score))


if __name__ == "__main__":
    main()
