from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    LINKEDIN = "linkedin"
    WELLFOUND = "wellfound"
    NAUKRI = "naukri"
    INSTAHYRE = "instahyre"
    FOUNDIT = "foundit"


class Job(BaseModel):
    id: Optional[int] = None
    external_id: str = Field(..., description="Job ID/slug from the source platform, used for dedup")
    platform: Platform
    company: str
    title: str
    location: Optional[str] = None
    description: str = ""
    url: str
    salary: Optional[str] = None
    posted_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
