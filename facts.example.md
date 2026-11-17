# Facts (single source of truth)

Everything in a CV, cover note or application form must trace to a line here. If it is not here, do not
claim it. Ask the candidate and add it only after they confirm. Keep this file private.

## Identity and contact
- Name: <Full Name>
- Email: <you@example.com>
- Phone: <+00 000 000 00 00>
- Location: <City, Country>
- Links: <github.com/example>, <linkedin.com/in/example>

## Targets
- Roles: <junior backend developer, support engineer>
- Work mode: <on-site in City, hybrid, remote>
- Pay expectation: <figure and currency, or "platform default">
- Relocation: <yes/no, where, what is needed>

## Education
- <Degree>, <University>, <years>. GPA: <value on a stated scale, only if the candidate wants it shown>.
- Hard limits worth knowing: <GPA cutoffs this GPA fails, missing licenses>

## Experience (each item: what was done, what was built, verifiable detail)
- <Project or job name> (<dates>): <one factual sentence>. Evidence: <repo, live URL, reference>.
- ...

## Skills
- Strong: <skills the candidate can discuss at depth>
- Working: <skills used in real projects>
- Basic: <skills only used briefly; do not list as strengths>

## Languages
- <Language>: <level>

## Constraints on applications
- Military service / work permit / notice period: <status and wording to use on forms>
- Will not apply to: <e.g. roles that ban AI tools in the work, night shifts>
- Will not do: <live algorithm tests, video interviews, anything the human wants to keep>

## Forbidden
Things the CV must never say. `ats_check.py` fails a PDF that contains any of these words or phrases.
One per line.
- <skill claimed but not held>
- <inflated title or years of experience>
- <employer name the candidate cannot cite>
