from scrapers.base import JobScraper
from scrapers.foundit import FounditScraper
from scrapers.greenhouse import GreenhouseScraper
from scrapers.instahyre import InstahyreScraper
from scrapers.lever import LeverScraper
from scrapers.naukri import NaukriScraper

SCRAPERS: dict[str, JobScraper] = {
    "greenhouse": GreenhouseScraper(),
    "lever": LeverScraper(),
    "naukri": NaukriScraper(),
    "instahyre": InstahyreScraper(),
    "foundit": FounditScraper(),
}


def get_scraper(platform: str) -> JobScraper:
    try:
        return SCRAPERS[platform]
    except KeyError:
        raise ValueError(f"No scraper registered for platform '{platform}'. Available: {list(SCRAPERS)}")
