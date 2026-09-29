"""
CLI Discovery Script for JobPilot AI.
Executes multi-query job search across target countries and role families,
expands role titles, deduplicates incoming records, and commits new jobs to the database.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jobpilot.core.feature_flags import get_settings
from jobpilot.database.repository import Repository, get_default_db_path
from jobpilot.database.models import utcnow_str
from jobpilot.discovery.searxng import SearXNGSource
from jobpilot.discovery.query_builder import QueryBuilder
from jobpilot.discovery.deduplicator import Deduplicator, compute_url_hash, compute_content_hash
from jobpilot.discovery.role_expander import RoleExpander

console = Console(safe_box=True)


async def execute_discovery(
    countries: List[str],
    roles: List[str],
    limit_per_query: int = 15,
    auto_approve_roles: bool = False,
):
    console.print(Panel.fit("[bold cyan]JobPilot AI - Discovered Job Postings Pipeline[/bold cyan]"))

    settings = get_settings()
    searx_url = settings.get("searxng", {}).get("base_url", "http://localhost:8080")
    db_path = get_default_db_path()
    repo = Repository(db_path)
    repo.init_db()

    # 1. Role Expansion
    expander = RoleExpander()
    expansion = await expander.expand(roles)
    console.print(f"[bold]Target Role Families:[/bold] {', '.join(roles)}")
    console.print(f"[bold green]Exact titles ({len(expansion.exact_titles)}):[/bold green] {', '.join(expansion.exact_titles[:4])}...")
    console.print(f"[bold cyan]Adjacent titles ({len(expansion.adjacent_titles)}):[/bold cyan] {', '.join(expansion.adjacent_titles[:4])}...")
    console.print(f"[bold yellow]Stretch titles ({len(expansion.stretch_titles)}):[/bold yellow] {', '.join(expansion.stretch_titles[:4])}...")

    if auto_approve_roles:
        expander.approve_expansion()
        console.print("[dim]Role expansions auto-approved for this run.[/dim]")

    # 2. Build search queries
    qb = QueryBuilder()
    all_role_terms = expansion.exact_titles + expansion.adjacent_titles[:3]
    queries = qb.build_ats_queries(role_keywords=all_role_terms, countries=countries, remote=True)
    queries.extend(qb.build_immigration_queries(role_keywords=expansion.exact_titles, countries=countries))

    console.print(f"[bold]Generated {len(queries)} dynamic search queries across {len(countries)} countries.[/bold]")

    # 3. Create Search Run record
    run_id = f"run_{utcnow_str().replace(':', '').replace('-', '')[:15]}"
    repo.create_search_run({
        "run_id": run_id,
        "query_count": len(queries),
        "status": "RUNNING",
    })

    # 4. Execute SearXNG queries
    searx = SearXNGSource(base_url=searx_url, request_delay=0.5)
    healthy = await searx.health_check()
    if not healthy:
        console.print(f"[bold yellow]WARNING:[/bold yellow] SearXNG not reachable at {searx_url}.")
        console.print("To start SearXNG locally: [cyan]docker run -d -p 8080:8080 searxng/searxng[/cyan]")
        console.print("[dim]Using simulated demonstration discovery for this run.[/dim]")

    discovered_jobs = []
    if healthy:
        for i, q in enumerate(queries[:10]):  # Run top queries
            try:
                jobs = await searx.search(q, limit=limit_per_query)
                discovered_jobs.extend(jobs)
            except Exception as e:
                console.print(f"[dim]Query error on '{q}': {e}[/dim]")
    else:
        # Fallback demonstration batch so pipeline flow can be verified end-to-end
        from jobpilot.core.schemas import JobRecord, RemotePolicy, EmploymentType, RoleTier
        for r in all_role_terms[:3]:
            for c in countries[:2]:
                job_id = f"mock_{r.lower().replace(' ', '_')}_{c.lower()}"
                mock_job = JobRecord(
                    job_id=job_id,
                    company="Innovate AI Corp",
                    title=f"{r}",
                    description="Building end-to-end LLM applications and automated pipelines.",
                    location=c,
                    country=c,
                    remote_policy=RemotePolicy.REMOTE,
                    employment_type=EmploymentType.FULL_TIME,
                    skills=["Python", "LLMs", "RAG", "Make.com"],
                    role_family="AI_ENGINEER",
                    role_tier=RoleTier.EXACT,
                    job_url=f"https://boards.greenhouse.io/innovateai/{job_id}",
                    source="searxng_mock",
                    date_found=utcnow_str(),
                )
                discovered_jobs.append(mock_job)

    # 5. Deduplicate
    existing_jobs = repo.list_jobs(limit=5000)
    seen_urls = {compute_url_hash(j.job_url) for j in existing_jobs if j.job_url}
    seen_contents = {compute_content_hash(j.company, j.title, j.country) for j in existing_jobs}
    deduper = Deduplicator(seen_urls, seen_contents)

    unique_jobs, duplicate_records = deduper.filter_unique(discovered_jobs)

    # 6. Save to Database
    new_saved_count = 0
    for j in unique_jobs:
        repo.upsert_job(j)
        new_saved_count += 1

    # 7. Finish Search Run
    repo.finish_search_run(run_id, {
        "status": "COMPLETED",
        "jobs_found": len(discovered_jobs),
        "jobs_new": new_saved_count,
        "jobs_duplicate": len(duplicate_records),
    })

    # Summary table
    table = Table(title="Discovery Run Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Count", style="green")
    table.add_row("Total Queries Planned", str(len(queries)))
    table.add_row("Raw Postings Found", str(len(discovered_jobs)))
    table.add_row("New Unique Jobs Saved", str(new_saved_count))
    table.add_row("Duplicates Skipped", str(len(duplicate_records)))
    console.print(table)
    console.print(f"[bold green][OK] Search run '{run_id}' finished successfully.[/bold green]")


@click.command()
@click.option("--countries", "-c", multiple=True, default=["India", "Germany"], help="Target countries for search.")
@click.option("--roles", "-r", multiple=True, default=["AI_ENGINEER", "AI_AUTOMATION"], help="Target role families.")
@click.option("--limit", "-l", default=15, help="Results limit per query.")
@click.option("--auto-approve-roles", is_flag=True, default=False, help="Automatically approve role expansions.")
def main(countries, roles, limit, auto_approve_roles):
    parsed_countries = []
    for c in countries:
        for item in c.replace(",", " ").split():
            if item.strip():
                parsed_countries.append(item.strip())

    parsed_roles = []
    for r in roles:
        for item in r.replace(",", " ").split():
            if item.strip():
                parsed_roles.append(item.strip())

    asyncio.run(execute_discovery(
        countries=parsed_countries or ["India", "Germany"],
        roles=parsed_roles or ["AI_ENGINEER"],
        limit_per_query=limit,
        auto_approve_roles=auto_approve_roles,
    ))


if __name__ == "__main__":
    main()
