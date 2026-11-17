# Application log

A single markdown file the agent and the candidate both edit. Pass it to `job_feed.py --tracker` so the feed
never resurfaces something already logged.

## Header (fill once)

```
# Applications (<month year>)

Rules from the candidate (date, source):
- <e.g. may the agent submit forms by itself? exceptions?>
- <pay expectations to enter in forms>
- <hard limits, e.g. minimum-GPA postings are skipped>

Status vocabulary: candidate > assessed > applied > test > interview > offer; rejected, silent, dropped.
```

## Table

One table per group (for example "AI training platforms", "Remote full-stack", "Local engineering").

```
| Status | Score | Company | Role | Pay / note | Link |
|---|---|---|---|---|---|
| applied | 4.2 | Example Corp | Junior Developer | applied 2026-01-05, tailored CV | https://example.com/jobs/123 |
| dropped | 2.5 | Sample Industries | Support Engineer | closed on check 2026-01-05 | https://example.com/jobs/456 |
| candidate | ? | Another Ltd | Automation Specialist | remote, USD | https://example.com/jobs/789 |
```

`?` in Score means not yet scored. Keep the full URL in the row: the feed script matches on it.

## Lessons

Dated one-liners: what a rejection, a closed posting or a failed build taught you, and the rule or config
change that followed.

## What not to store here

IDs, tax numbers, bank details, passwords, one-time codes. The log can be read by an agent; keep sensitive
data out of it.
