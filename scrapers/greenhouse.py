from datetime import datetime

import httpx

from models.job import Job, Platform
from scrapers.base import JobScraper

BOARD_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


class GreenhouseScraper(JobScraper):
    """Pulls jobs from Greenhouse's public boards JSON API.

    No browser automation needed here: Greenhouse (like Lever) exposes an
    unauthenticated JSON endpoint for every public job board, which is
    faster and far more reliable than scraping the rendered page. Playwright
    is reserved for platforms that don't expose one (LinkedIn, Wellfound).
    """

    def fetch_jobs(self, target: str) -> list[Job]:
        url = BOARD_API.format(token=target)
        response = httpx.get(url, params={"content": "true"}, timeout=30)
        response.raise_for_status()
        payload = response.json()

        jobs = []
        for item in payload.get("jobs", []):
            jobs.append(
                Job(
                    external_id=str(item["id"]),
                    platform=Platform.GREENHOUSE,
                    company=target,
                    title=item["title"],
                    location=(item.get("location") or {}).get("name"),
                    description=item.get("content", ""),
                    url=item["absolute_url"],
                    posted_at=_parse_date(item.get("updated_at")),
                )
            )
        return jobs


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
