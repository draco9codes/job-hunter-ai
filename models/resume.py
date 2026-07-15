from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResumeVersion(BaseModel):
    id: Optional[int] = None
    job_id: int
    file_path: str
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
