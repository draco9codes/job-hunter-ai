from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

COLUMNS = [
    "Company",
    "Role",
    "Platform",
    "Location",
    "Salary",
    "Match %",
    "Resume Used",
    "Applied",
    "Interview",
    "OA",
    "HR",
    "Offer",
    "Rejected",
    "Notes",
    "Job URL",
]
_URL_COL = COLUMNS.index("Job URL")


def ensure_workbook(path: str) -> None:
    if Path(path).exists():
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Applications"
    ws.append(COLUMNS)
    wb.save(path)


def upsert_row(path: str, row: dict) -> None:
    """Insert a row for this job's URL, or update the existing one in place if already synced.

    Keyed on URL rather than (Company, Role): distinct postings can share an
    identical title at the same company (e.g. multiple "Accenture - Custom
    Software Engineer" listings from one Naukri search), which used to
    silently collapse into a single row and lose real job records.
    """
    ensure_workbook(path)
    wb = load_workbook(path)
    ws: Worksheet = wb["Applications"]

    for existing in ws.iter_rows(min_row=2):
        if existing[_URL_COL].value == row.get("Job URL"):
            for i, col in enumerate(COLUMNS):
                if col in row:
                    existing[i].value = row[col]
            wb.save(path)
            return

    ws.append([row.get(col, "") for col in COLUMNS])
    wb.save(path)


def update_status(path: str, job_url: str, column: str, value: str) -> bool:
    """Find the row matching this job's URL and update one status column. Returns True if found."""
    wb = load_workbook(path)
    ws: Worksheet = wb["Applications"]
    col_index = COLUMNS.index(column)

    for row in ws.iter_rows(min_row=2):
        if row[_URL_COL].value == job_url:
            row[col_index].value = value
            wb.save(path)
            return True
    return False
