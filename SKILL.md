---
name: job-search-pipeline
description: Run a job search as a repeatable pipeline. Builds a daily job feed from public listings, scores it, checks that a posting is still open and legitimate, tailors an ATS-safe CV to each posting using only a single facts file, runs ATS and made-up-claim checks on the PDF, and keeps an application log. Use when the user wants to find, rank, or apply to jobs, tailor a CV to a posting, or set up a job search workflow.
---

# Job search pipeline

A job search has a lot of repeated, checkable steps. This skill keeps those steps in scripts and rules so the
agent does the labor and the human keeps the decisions.

## Core rules

1. **One facts file is the source of truth.** Everything the CV, cover note, or application form says about
   the candidate must trace to a line in `facts.md`. If a posting asks for something that is not in the file,
   do not claim it. Ask the candidate, and add it to the file only after they confirm it.
2. **Tailor every application to its posting.** Pick the closest base CV variant, then adjust summary,
   headline, bullet order and keywords from the posting text. Use only facts from the file. A generic CV is
   a fallback for forms that take no tailored upload.
3. **Verify the build.** After every CV change, rebuild the PDF and run the ATS check. Do not call a CV
   ready from the HTML alone. A silent build failure once shipped a stale PDF, so the script proves the
   file was rewritten.
4. **Skip postings whose hard requirements the candidate fails.** Examples: a minimum GPA, a required
   license, a citizenship or clearance requirement, a banned-tool rule. Write the reason in the log and move
   on. Do not spend a tailored CV on a posting that will auto-reject.
5. **Humans do the human parts.** The agent never opens accounts, never enters ID, tax or bank data, never
   takes assessments, video or voice interviews, and never solves CAPTCHAs. It prepares everything up to
   the final submit step and says what is left.
6. **No bulk automation on login-walled sites.** Feed scripts read public listing pages only. Do not script
   logins or mass-apply on professional networks; accounts get closed.
7. **A feed is a lead list.** Keyword filters are crude. Read the posting before applying.

## Workflow, per posting

| # | Step | Tool |
|---|------|------|
| 1 | Add the posting to the log as `candidate` (link, role, pay) | log table |
| 2 | Check it is open and not a scam; stop on red flags | `scripts/job_check.py URL` |
| 3 | Score it; apply at 4.0+, consider 3.0 to 3.9, drop below 3.0 | rubric in `references/scoring-rubric.md` |
| 4 | Save the posting text in an archive folder (it disappears when the posting closes, and you need it for interviews) | `postings/<company>-<role>.md` |
| 5 | Choose and tailor the CV from `facts.md` | `CV-*.html` |
| 6 | Claim audit: every sentence in the CV and note maps to a fact | read against `facts.md` |
| 7 | Rebuild the PDF and check ATS, links, forbidden terms, missing keywords | `scripts/ats_check.py` |
| 8 | Fill the form, stop before the final submit | browser |
| 9 | Human approves and submits; set status `applied` with the date | log table |
| 10 | Follow up after about 7 days if the platform allows; mark `silent` after about 21 | log table |
| 11 | Record the outcome and the reason; adjust the rubric if the reason was a pattern | log table |

Whether the agent may submit on its own after step 8 is the candidate's call. Ask once at the start, write the
answer into the log file header, and respect any exception the candidate names (night shifts, relocation
commitments, anything that binds their life).

## Setup

1. Copy `facts.example.md` to `facts.md` in the candidate's job folder and fill it in with the candidate.
   Keep it out of version control (the repo `.gitignore` already does). Fill the `## Forbidden` section:
   things the CV must never say.
2. Create the log from `references/application-log.md`.
3. Copy `scripts/config.example.json` and `scripts/score_config.example.json`, then edit queries, locations,
   scoring tracks and penalties for the candidate.
4. Install dependencies: `pip install python-jobspy pypdf`. Use a virtual environment.

## Scripts

All scripts take paths and config as arguments. None contain personal data. Each has `--selftest` or
`--help`.

- `scripts/job_feed.py --config config.json --out-dir feed --tracker applications.md --hours 48`
  Pulls public listings through JobSpy, drops senior titles and "5+ years" postings and anything your config
  rejects, tags coding tests, visa sponsorship and hard-currency pay, de-duplicates against earlier runs and
  your log, and writes a dated `.md` and `.csv`. It never logs in or applies.
- `scripts/score_feed.py feed/<date>.csv --config score_config.json`
  Rule-based 1 to 5 score from title, company, location and tags. Tracks let different role families use
  different criteria. A `company_penalties` entry encodes an employer whose hard requirement the candidate
  fails. No model calls.
- `scripts/job_check.py URL [URL ...]`
  Prints LIVE, CLOSED or UNKNOWN and any scam red flags. UNKNOWN means open it in a browser.
- `scripts/ats_check.py --dir cv/ [--keywords posting.txt CV-X.pdf]`
  Rebuilds `CV-*.html` to PDF with headless Chrome, then checks: one page, a text layer, required contact
  strings, section headings, forbidden terms from `facts.md`, broken ligatures, clickable links. With
  `--keywords` it lists capitalized terms from the posting that are missing from the CV. Add one only if it
  is true and in `facts.md`.

## CV format that passes ATS

Single column, real text, standard headings (Summary, Skills, Experience, Education), links as text plus a
clickable annotation, one page. No tables for layout, no text in images, no icon fonts. Details and the
check list are in `references/ats-cv-rules.md`.

## Turkey notes (Türkiye)

Public feeds cover LinkedIn and Indeed. Kariyer.net and eleman.net have no scraping-friendly public API, so
check them by hand or by saved search emails and paste promising postings into the log. Turkish employers
often ask about military service status and expected net salary in the form; those answers are the
candidate's to give, never guessed by the agent. See `references/ats-cv-rules.md` for the Turkish character
check (İ, ı, ş, ğ) on the PDF text layer.

## When something is off

- The feed returns nothing: LinkedIn rate-limited that query. The summary header lists failed queries; rerun
  later with `--sections` to narrow.
- `ats_check.py` says BUILD FAILED: Chrome did not write the PDF. Close any viewer that locks the file and
  rerun; do not upload the old PDF.
- A posting closed between reading and applying: log it as `dropped`, keep the archived text.
