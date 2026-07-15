"""Tailored resume generation.

The LLM is only allowed to reorder/rephrase content that already exists in
the master resume (see prompts/resume_prompt.txt). `_verify_integrity` is a
second, code-level guardrail on top of the prompt: it checks the generated
skill list is a subset of the master list, since prompts can be ignored by
the model but set arithmetic cannot.
"""
import json
from pathlib import Path

from models.job import Job
from utils.llm_client import get_client, get_model, parse_json_response

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "resume_prompt.txt"


class ResumeIntegrityError(Exception):
    """Raised when the generated resume introduces content not present in the master resume."""


def generate_tailored_resume(job: Job, master_resume: dict, output_dir: Path) -> Path:
    client = get_client()
    model = get_model()

    prompt = PROMPT_PATH.read_text().format(
        master_resume_json=json.dumps(master_resume),
        job_title=job.title,
        job_description=job.description[:6000],
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    tailored = parse_json_response(response.choices[0].message.content)

    _verify_integrity(tailored, master_resume)
    _verify_not_empty(tailored)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
    safe_title = "".join(c if c.isalnum() else "_" for c in job.title)[:40]
    out_path = output_dir / f"{safe_company}_{safe_title}.md"
    out_path.write_text(_render_markdown(master_resume["name"], tailored))
    return out_path


def _verify_integrity(tailored: dict, master_resume: dict) -> None:
    master_skills = {s.lower() for s in master_resume.get("skills", [])}
    tailored_skills = {s.lower() for s in tailored.get("skills", [])}
    fabricated = tailored_skills - master_skills
    if fabricated:
        raise ResumeIntegrityError(
            f"Generated resume introduced skills not in master resume: {fabricated}"
        )

    master_companies = {e["company"].lower() for e in master_resume.get("experience", [])}
    tailored_companies = {e["company"].lower() for e in tailored.get("experience", [])}
    fabricated_companies = tailored_companies - master_companies
    if fabricated_companies:
        raise ResumeIntegrityError(
            f"Generated resume introduced employers not in master resume: {fabricated_companies}"
        )


def _verify_not_empty(tailored: dict) -> None:
    """Local reasoning models occasionally return well-formed but empty/degenerate JSON.
    Fail loudly instead of silently writing a blank resume file."""
    has_bullets = any(exp.get("bullets") for exp in tailored.get("experience", []))
    if not tailored.get("summary") or not tailored.get("skills") or not has_bullets:
        raise ResumeIntegrityError(
            "Generated resume came back empty or incomplete (missing summary/skills/bullets) -- retry."
        )


def _render_markdown(name: str, tailored: dict) -> str:
    lines = [f"# {name}", "", tailored.get("summary", ""), "", "## Skills", ""]
    lines.append(", ".join(tailored.get("skills", [])))
    lines.append("")
    lines.append("## Experience")
    for exp in tailored.get("experience", []):
        lines.append("")
        lines.append(f"**{exp['title']}, {exp['company']}** ({exp.get('duration', '')})")
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
    lines.append("")
    lines.append("## Projects")
    for project in tailored.get("projects", []):
        lines.append("")
        lines.append(f"**{project['name']}**")
        for bullet in project.get("bullets", []):
            lines.append(f"- {bullet}")
    return "\n".join(lines)
