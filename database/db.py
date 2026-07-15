"""SQLite access layer.

Deliberately raw sqlite3 instead of an ORM: the MVP has five tables and no
concurrent writers, so an ORM would add abstraction without buying anything.
Revisit this if/when the SaaS migration to PostgreSQL happens.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from models.application import Application, ApplicationStatus
from models.job import Job
from models.resume import ResumeVersion

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_job(conn: sqlite3.Connection, job: Job) -> Optional[int]:
    """Insert a job, skipping duplicates. Returns the new row id, or None if it already existed."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO jobs
            (external_id, platform, company, title, location, description, url, salary, posted_at, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.external_id,
            job.platform.value,
            job.company,
            job.title,
            job.location,
            job.description,
            job.url,
            job.salary,
            job.posted_at.isoformat() if job.posted_at else None,
            job.scraped_at.isoformat(),
        ),
    )
    return cursor.lastrowid if cursor.rowcount else None


def list_jobs(conn: sqlite3.Connection, unmatched_only: bool = False, platform: Optional[str] = None) -> list[Job]:
    query = "SELECT * FROM jobs"
    conditions = []
    params: list = []
    if unmatched_only:
        conditions.append("id NOT IN (SELECT job_id FROM applications)")
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    rows = conn.execute(query + " ORDER BY scraped_at DESC", params).fetchall()
    return [_row_to_job(row) for row in rows]


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        external_id=row["external_id"],
        platform=row["platform"],
        company=row["company"],
        title=row["title"],
        location=row["location"],
        description=row["description"],
        url=row["url"],
        salary=row["salary"],
        posted_at=row["posted_at"],
        scraped_at=row["scraped_at"],
    )


def insert_resume_version(conn: sqlite3.Connection, resume: ResumeVersion) -> int:
    cursor = conn.execute(
        "INSERT INTO resume_versions (job_id, file_path, summary, generated_at) VALUES (?, ?, ?, ?)",
        (resume.job_id, resume.file_path, resume.summary, resume.generated_at.isoformat()),
    )
    return cursor.lastrowid


def upsert_application(conn: sqlite3.Connection, application: Application) -> int:
    if application.id is not None:
        conn.execute(
            """
            UPDATE applications
            SET resume_version_id = ?, match_percent = ?, status = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                application.resume_version_id,
                application.match_percent,
                application.status.value,
                application.notes,
                application.updated_at.isoformat(),
                application.id,
            ),
        )
        return application.id

    cursor = conn.execute(
        """
        INSERT INTO applications
            (job_id, resume_version_id, match_percent, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            application.job_id,
            application.resume_version_id,
            application.match_percent,
            application.status.value,
            application.notes,
            application.created_at.isoformat(),
            application.updated_at.isoformat(),
        ),
    )
    return cursor.lastrowid


def list_applications(conn: sqlite3.Connection) -> list[Application]:
    rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
    return [
        Application(
            id=row["id"],
            job_id=row["job_id"],
            resume_version_id=row["resume_version_id"],
            match_percent=row["match_percent"],
            status=ApplicationStatus(row["status"]),
            notes=row["notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
