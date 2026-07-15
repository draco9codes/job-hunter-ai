"""Opens a job's application page for manual review before submission.

Sprint 1 scope: launch a real, visible browser at the application URL so you
can review and fill it yourself -- never auto-submits. Per-platform field
auto-fill (mapping resume data into Greenhouse/Lever form fields) is tracked
as backlog work once the scrape -> match -> tailor loop is proven out.
"""
from playwright.sync_api import sync_playwright


def open_application(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        input(f"Application page open for review: {url}\nPress Enter here once you're done (browser stays open until then)... ")
        browser.close()
