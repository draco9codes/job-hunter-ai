from abc import ABC, abstractmethod

from models.job import Job


class JobScraper(ABC):
    """Common interface every job board scraper must implement.

    New platforms (LinkedIn, Wellfound, Instahyre, Naukri, Foundit) plug in
    by subclassing this and registering in scrapers/registry.py -- nothing
    else in the pipeline needs to change.
    """

    @abstractmethod
    def fetch_jobs(self, target: str) -> list[Job]:
        """Fetch open jobs for one target (a company slug/token, or a search query)."""
        raise NotImplementedError
