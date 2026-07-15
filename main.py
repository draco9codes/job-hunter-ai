import json
from pathlib import Path

import typer
from rich import print
from rich.table import Table

from database.db import get_connection, init_db, insert_job, insert_resume_version, list_jobs, upsert_application
from matcher.matcher import match_job
from models.application import Application, ApplicationStatus
from models.job import Job
from resume.generator import ResumeIntegrityError, generate_tailored_resume
from resume.generator import PROMPT_PATH  # noqa: F401  (import guards prompt file exists)
from models.resume import ResumeVersion
from scrapers.registry import get_scraper
from tracker.excel_tracker import ensure_workbook, upsert_row
from utils.apply_engine import open_application
from utils.config import load_config

app = typer.Typer(help="AI Job Hunter -- scrape, match, tailor, and track job applications.")


def _db_path() -> str:
    return load_config()["paths"]["database"]


@app.command()
def init() -> None:
    """Create the SQLite database and Excel tracker if they don't exist yet."""
    config = load_config()
    init_db(config["paths"]["database"])
    ensure_workbook(config["paths"]["tracker_excel"])
    print("[green]Database and tracker initialized.[/green]")


@app.command()
def scrape() -> None:
    """Scrape all configured targets and store new jobs in the database."""
    config = load_config()
    init_db(config["paths"]["database"])

    total_new = 0
    with get_connection(config["paths"]["database"]) as conn:
        for platform, targets in config["targets"].items():
            scraper = get_scraper(platform)
            for target in targets:
                if not target:
                    continue
                try:
                    jobs = scraper.fetch_jobs(target)
                except Exception as exc:  # noqa: BLE001 -- one bad target shouldn't kill the run
                    print(f"[red]Failed to scrape {platform}/{target}: {exc}[/red]")
                    continue

                new_count = 0
                for job in jobs:
                    if insert_job(conn, job) is not None:
                        new_count += 1
                total_new += new_count
                print(f"[cyan]{platform}/{target}[/cyan]: {len(jobs)} fetched, {new_count} new")

    print(f"[green]Done. {total_new} new jobs stored.[/green]")


@app.command()
def match() -> None:
    """Match all unmatched jobs against the master resume and record match %."""
    config = load_config()
    master_resume = json.loads(Path(config["paths"]["master_resume"]).read_text())
    min_percent = config["matcher"]["min_match_percent"]

    with get_connection(config["paths"]["database"]) as conn:
        jobs = list_jobs(conn, unmatched_only=True)
        if not jobs:
            print("[yellow]No unmatched jobs found. Run `scrape` first.[/yellow]")
            return

        table = Table(title="Match results")
        table.add_column("Company")
        table.add_column("Title")
        table.add_column("Match %")

        for job in jobs:
            result = match_job(job, master_resume)
            status = ApplicationStatus.MATCHED
            upsert_application(
                conn,
                Application(job_id=job.id, match_percent=result.percent, status=status, notes=result.reasoning),
            )
            flag = "[green]" if result.percent >= min_percent else "[dim]"
            table.add_row(job.company, job.title, f"{flag}{result.percent}%[/]")

        print(table)


@app.command("generate-resume")
def generate_resume_cmd(min_match: float = None) -> None:
    """Generate a tailored resume for every matched job above the match threshold."""
    config = load_config()
    master_resume = json.loads(Path(config["paths"]["master_resume"]).read_text())
    threshold = min_match if min_match is not None else config["matcher"]["min_match_percent"]
    output_dir = Path(config["paths"]["resumes_dir"]) / "generated"

    with get_connection(config["paths"]["database"]) as conn:
        jobs_by_id = {job.id: job for job in list_jobs(conn)}
        from database.db import list_applications

        for application in list_applications(conn):
            if application.resume_version_id is not None:
                continue
            if (application.match_percent or 0) < threshold:
                continue
            job = jobs_by_id.get(application.job_id)
            if job is None:
                continue
            try:
                path = generate_tailored_resume(job, master_resume, output_dir)
            except ResumeIntegrityError as exc:
                print(f"[red]Integrity check failed for {job.company}/{job.title}: {exc}[/red]")
                continue

            resume_version = insert_resume_version(
                conn, ResumeVersion(job_id=job.id, file_path=str(path))
            )
            application.resume_version_id = resume_version
            application.status = ApplicationStatus.RESUME_GENERATED
            upsert_application(conn, application)
            print(f"[green]Generated resume for {job.company} / {job.title} -> {path}[/green]")


@app.command()
def apply(job_id: int) -> None:
    """Open a job's application page for manual review and submission."""
    config = load_config()
    with get_connection(config["paths"]["database"]) as conn:
        jobs = {job.id: job for job in list_jobs(conn)}
        job = jobs.get(job_id)
        if job is None:
            print(f"[red]No job with id {job_id}[/red]")
            raise typer.Exit(1)

        open_application(job.url)

        from database.db import list_applications

        for application in list_applications(conn):
            if application.job_id == job_id:
                application.status = ApplicationStatus.APPLIED
                upsert_application(conn, application)
                break


@app.command()
def track() -> None:
    """Sync all applications into the Excel tracker."""
    config = load_config()
    ensure_workbook(config["paths"]["tracker_excel"])

    with get_connection(config["paths"]["database"]) as conn:
        jobs_by_id = {job.id: job for job in list_jobs(conn)}
        from database.db import list_applications

        for application in list_applications(conn):
            job = jobs_by_id.get(application.job_id)
            if job is None:
                continue
            upsert_row(
                config["paths"]["tracker_excel"],
                {
                    "Company": job.company,
                    "Role": job.title,
                    "Platform": job.platform.value,
                    "Location": job.location or "",
                    "Salary": job.salary or "",
                    "Match %": application.match_percent if application.match_percent is not None else "",
                    "Resume Used": application.resume_version_id if application.resume_version_id is not None else "",
                    "Applied": "Y" if application.status == ApplicationStatus.APPLIED else "",
                    "Notes": application.notes,
                },
            )
    print("[green]Tracker synced.[/green]")


if __name__ == "__main__":
    app()
