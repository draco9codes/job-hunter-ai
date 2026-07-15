"""Infers Remote / Hybrid / Onsite from a job's text fields.

None of the scrapers (Greenhouse, Lever, Naukri) expose a clean, consistent
structured field for this -- Naukri's per-job payload doesn't carry the
wfhType its search-page filters aggregate, and Greenhouse/Lever don't have
the concept at all. Keyword matching against location/title/description is
the only signal available across all of them.
"""
import re

from models.job import Job

_REMOTE_RE = re.compile(r"\b(remote|work from home|wfh|fully distributed)\b", re.IGNORECASE)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)


def infer_job_type(job: Job) -> str:
    haystack = " ".join([job.location or "", job.title, job.description[:500]])
    if _HYBRID_RE.search(haystack):
        return "Hybrid"
    if _REMOTE_RE.search(haystack):
        return "Remote"
    return "Onsite"
