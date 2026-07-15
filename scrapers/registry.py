from scrapers.base import JobScraper
from scrapers.greenhouse import GreenhouseScraper
from scrapers.lever import LeverScraper

SCRAPERS: dict[str, JobScraper] = {
    "greenhouse": GreenhouseScraper(),
    "lever": LeverScraper(),
}


def get_scraper(platform: str) -> JobScraper:
    try:
        return SCRAPERS[platform]
    except KeyError:
        raise ValueError(f"No scraper registered for platform '{platform}'. Available: {list(SCRAPERS)}")
