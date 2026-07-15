from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    MATCHED = "matched"
    RESUME_GENERATED = "resume_generated"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    HR_ROUND = "hr_round"
    OFFER = "offer"
    REJECTED = "rejected"


class Application(BaseModel):
    id: Optional[int] = None
    job_id: int
    resume_version_id: Optional[int] = None
    match_percent: Optional[float] = None
    status: ApplicationStatus = ApplicationStatus.MATCHED
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
