# job-hunter-ai

A personal, local-first tool to scrape jobs, match them against your resume,
generate a tailored (fabrication-free) resume, and track every application --
built to get interviews fast, with a SaaS version deferred until this MVP
proves itself.

## Why it's built this way

- **No auth, no frontend, no Docker.** Everything runs as a local CLI against
  SQLite and an Excel file. The only goal right now is applications going out
  the door.
- **Human in the loop, always.** The apply step opens a real browser at the
  application page and pauses for you to review and submit -- nothing is
  auto-submitted.
- **Resume integrity is enforced in code, not just prompted.** The generator
  checks that every skill/employer in a tailored resume already exists in
  your master resume (`resumes/master_resume.json`) and raises
  `ResumeIntegrityError` if the LLM invents anything.
- **Scrapers use public JSON APIs, not browser automation, where possible.**
  Greenhouse and Lever both expose unauthenticated JSON endpoints for public
  job boards -- far faster and more reliable than Playwright scraping. New
  platforms (LinkedIn, Wellfound, Instahyre, Naukri, Foundit) that don't
  expose an API will need real browser automation and should implement
  `scrapers/base.py`'s `JobScraper` interface.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # only needed for the `apply` command
cp .env.example .env          # add OPENAI_API_KEY to enable LLM matching/tailoring
```

Fill in `resumes/master_resume.json` with your real experience -- this is the
only source of truth the resume generator is allowed to draw from.

Edit `config.yaml` to list the companies you want to track (Greenhouse board
token or Lever site slug, taken from their public careers page URL).

## Usage

```bash
python main.py init              # create the SQLite DB and Excel tracker
python main.py scrape             # pull jobs from all configured targets
python main.py match              # score match % for every new job
python main.py generate-resume    # tailor a resume for jobs above the match threshold
python main.py apply <job_id>     # open the application page for manual review/submit
python main.py track              # sync everything into tracker/applications.xlsx
```

Without `OPENAI_API_KEY` set, `match` falls back to plain keyword overlap so
the pipeline still runs end-to-end at zero cost -- expect low, noisy scores
until you add a key. `generate-resume` requires the key (there's no
non-LLM fallback for tailoring).

## Architecture

```
CLI (main.py, Typer)
  -> scrapers/  (JobScraper interface; greenhouse.py, lever.py implementations)
  -> database/  (raw sqlite3, schema.sql -- no ORM, five tables, single writer)
  -> matcher/   (LLM match % with keyword-overlap fallback)
  -> resume/    (LLM tailoring + code-level integrity check against master resume)
  -> tracker/   (openpyxl Excel read/upsert)
```

## Sprint log

**Sprint 1 (2026-07-15):** Scaffolded the full pipeline skeleton --
models, SQLite schema, Greenhouse/Lever scrapers (verified live against
Stripe's board: 521 jobs fetched successfully), keyword-fallback matcher,
resume generator with integrity guardrails, Excel tracker, and the Typer CLI
wiring it all together end-to-end.

Known tech debt / backlog:
- `apply_engine.py` only opens the browser for manual fill-in; per-platform
  auto-fill of application form fields is not implemented yet.
- No dedup/staleness handling for jobs that get pulled or filled elsewhere.
- Matcher's keyword fallback is crude; real signal needs an OpenAI key.
- No tests yet -- fine for a single-user local tool at this size, revisit if
  scraper/matcher logic grows.

Next sprint: fill in your real `master_resume.json`, set `OPENAI_API_KEY`,
populate `config.yaml` with real target companies, and run the full
scrape -> match -> generate-resume -> apply loop against real jobs.
