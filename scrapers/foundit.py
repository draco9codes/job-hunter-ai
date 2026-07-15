"""Foundit (formerly Monster India) scraper.

Same situation as Naukri: the search API (middleware/jobsearch) sits behind
Akamai bot protection -- a plain HTTP call gets a generic 400 "content
negotiation failed" regardless of headers, which is Akamai's bot-mitigation
response rather than a real API error. As with Naukri, this drives a real,
visible browser to the search page and reads the JSON response the page's
own JavaScript legitimately requests, instead of trying to work around the
protection.

`target` is a search keyword (e.g. "java spring boot"), not a company --
Foundit doesn't expose per-company boards like Greenhouse/Lever.
"""
from datetime import datetime

from playwright.sync_api import sync_playwright

from models.job import Job, Platform
from scrapers.base import JobScraper

BASE_URL = "https://www.foundit.in"


class FounditScraper(JobScraper):
    def fetch_jobs(self, target: str) -> list[Job]:
        url = f"{BASE_URL}/srp/results?query={target.replace(' ', '%20')}"
        captured: dict = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            def handle_response(response):
                if "middleware/jobsearch" in response.url and response.ok:
                    try:
                        captured["data"] = response.json()
                    except Exception:  # noqa: BLE001 -- non-JSON responses just get skipped
                        pass

            page.on("response", handle_response)
            page.goto(url, timeout=30000)
            page.wait_for_timeout(4000)  # let the page's own API call land

            if "data" not in captured and "captcha" in page.content().lower():
                print(
                    f"Foundit is showing a captcha for '{target}'. Solve it in the "
                    "browser window that just opened, then re-run scrape."
                )
                page.wait_for_timeout(15000)

            browser.close()

        if "data" not in captured:
            return []

        jobs = []
        for item in captured["data"].get("jobSearchResponse", {}).get("data", []):
            # The feed mixes in sponsored/promo cards without a real jobId or title -- skip those.
            job_id = item.get("jobId") or item.get("id")
            title = item.get("title")
            if not job_id or not title:
                continue

            url = (BASE_URL + item["jdUrl"]) if item.get("jdUrl") else item.get("redirectUrl", "")
            if not url:
                continue

            jobs.append(
                Job(
                    external_id=str(job_id),
                    platform=Platform.FOUNDIT,
                    company=item.get("companyName", "Unknown"),
                    title=title,
                    location=item.get("locations"),
                    description=f"Skills: {item.get('skills', '')}" if item.get("skills") else "",
                    url=url,
                    salary=item.get("salary"),
                    posted_at=_parse_epoch_ms(item.get("createdAt")),
                )
            )
        return jobs


def _parse_epoch_ms(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.utcfromtimestamp(int(value) / 1000)
    except (ValueError, TypeError, OverflowError):
        return None
