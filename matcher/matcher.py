"""Resume-to-job matching.

Uses an LLM to compare the master resume against a job description and
return a match percentage plus reasoning, when an OpenAI key is configured.
Falls back to plain keyword overlap otherwise, so the pipeline still runs
end-to-end with zero API cost while you're setting things up.
"""
import json
import os
import re
from dataclasses import dataclass

from models.job import Job

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]{1,}")


@dataclass
class MatchResult:
    percent: float
    reasoning: str


def match_job(job: Job, master_resume: dict) -> MatchResult:
    if os.getenv("OPENAI_API_KEY"):
        return _match_with_llm(job, master_resume)
    return _match_with_keywords(job, master_resume)


def _match_with_keywords(job: Job, master_resume: dict) -> MatchResult:
    resume_terms = _terms(" ".join(master_resume.get("skills", [])))
    job_terms = _terms(job.title + " " + job.description)
    if not job_terms:
        return MatchResult(percent=0.0, reasoning="Job description had no extractable text.")

    overlap = resume_terms & job_terms
    percent = round(100 * len(overlap) / max(len(job_terms), 1), 1)
    percent = min(percent, 100.0)
    reasoning = f"Keyword overlap fallback (no OPENAI_API_KEY set). Matched terms: {', '.join(sorted(overlap)) or 'none'}"
    return MatchResult(percent=percent, reasoning=reasoning)


def _match_with_llm(job: Job, master_resume: dict) -> MatchResult:
    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    prompt = f"""You are scoring how well a candidate's resume matches a job description.
Resume (JSON, source of truth -- do not assume anything beyond it):
{json.dumps(master_resume)}

Job title: {job.title}
Job description:
{job.description[:6000]}

Return strict JSON: {{"match_percent": <0-100 number>, "reasoning": "<one short paragraph>"}}
Base the score only on real overlap between resume content and job requirements."""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return MatchResult(percent=float(data["match_percent"]), reasoning=data["reasoning"])


def _terms(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text)}
