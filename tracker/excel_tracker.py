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
]


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
    """Insert a row for (Company, Role), or update the existing one in place if already synced."""
    ensure_workbook(path)
    wb = load_workbook(path)
    ws: Worksheet = wb["Applications"]

    for existing in ws.iter_rows(min_row=2):
        if existing[0].value == row.get("Company") and existing[1].value == row.get("Role"):
            for i, col in enumerate(COLUMNS):
                if col in row:
                    existing[i].value = row[col]
            wb.save(path)
            return

    ws.append([row.get(col, "") for col in COLUMNS])
    wb.save(path)


def update_status(path: str, company: str, role: str, column: str, value: str) -> bool:
    """Find the row matching company+role and update one status column. Returns True if found."""
    wb = load_workbook(path)
    ws: Worksheet = wb["Applications"]
    col_index = COLUMNS.index(column) + 1

    for row in ws.iter_rows(min_row=2):
        if row[0].value == company and row[1].value == role:
            row[col_index - 1].value = value
            wb.save(path)
            return True
    return False
