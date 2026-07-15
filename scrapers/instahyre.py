"""Instahyre scraper.

Unlike Naukri, Instahyre's public job search API (jobs.instahyre.com's
api/v1/job_search) is genuinely open -- no signed token, no captcha, works
from a plain HTTP client with no session at all. It only takes single
keyword values though (comma-separated values are rejected outright), so
`target` is one keyword/phrase like "spring boot", not a full boolean query.

The one limitation: this endpoint returns keywords/title/location/company
but not the full job description -- that's rendered client-side from an
authenticated endpoint. Rather than fall back to Playwright per job (which
would erase the speed advantage of having an open API at all), the
`keywords` tag list is used as a lightweight description proxy. It's less
rich than a real JD, but still gives the matcher real signal.
"""
import httpx

from models.job import Job, Platform
from scrapers.base import JobScraper

BASE_URL = "https://www.instahyre.com"
SEARCH_API = f"{BASE_URL}/api/v1/job_search"
MAX_PAGES = 5  # the server caps each page at 35 regardless of a requested `limit`


class InstahyreScraper(JobScraper):
    def fetch_jobs(self, target: str) -> list[Job]:
        jobs = []
        url = SEARCH_API
        params = {"company_size": 0, "job_type": 0, "offset": 0, "source": "opportunities", "skills": target}

        for _ in range(MAX_PAGES):
            response = httpx.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
            payload = response.json()

            for item in payload.get("objects", []):
                employer = item.get("employer", {})
                keywords = item.get("keywords", [])
                jobs.append(
                    Job(
                        external_id=str(item["id"]),
                        platform=Platform.INSTAHYRE,
                        company=employer.get("company_name", "Unknown"),
                        title=item["title"],
                        location=item.get("locations"),
                        description=f"Skills: {', '.join(keywords)}" if keywords else "",
                        url=item["public_url"],
                    )
                )

            next_path = payload.get("meta", {}).get("next")
            if not next_path:
                break
            url = BASE_URL + next_path
            params = None  # the next URL already carries its own query string

        return jobs
