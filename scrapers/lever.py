import httpx

from models.job import Job, Platform
from scrapers.base import JobScraper

POSTINGS_API = "https://api.lever.co/v0/postings/{site}"


class LeverScraper(JobScraper):
    """Pulls jobs from Lever's public postings JSON API (same rationale as GreenhouseScraper)."""

    def fetch_jobs(self, target: str) -> list[Job]:
        url = POSTINGS_API.format(site=target)
        response = httpx.get(url, params={"mode": "json"}, timeout=30)
        response.raise_for_status()
        payload = response.json()

        jobs = []
        for item in payload:
            categories = item.get("categories", {})
            jobs.append(
                Job(
                    external_id=item["id"],
                    platform=Platform.LEVER,
                    company=target,
                    title=item["text"],
                    location=categories.get("location"),
                    description=item.get("descriptionPlain", item.get("description", "")),
                    url=item["hostedUrl"],
                )
            )
        return jobs
