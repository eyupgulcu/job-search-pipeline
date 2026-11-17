# job-search-pipeline

Run a job search as a repeatable pipeline. Builds a daily job feed from public listings, scores it, checks that a posting is still open and legitimate, tailors an ATS-safe CV to each posting using only a single facts file, runs ATS and made-up-claim checks on the PDF, and keeps an application log. Use when the user wants to find, rank, or apply to jobs, tailor a CV to a posting, or set up a job search workflow.

An agent skill in the Claude Code / Agent Skills format (`SKILL.md` with YAML frontmatter). Part of a small set of original skills: see [agent-skills](https://github.com/eyupgulcu/agent-skills) for the others.

## Install

```
git clone https://github.com/eyupgulcu/job-search-pipeline ~/.claude/skills/job-search-pipeline
```

On Windows, clone into `%USERPROFILE%\.claude\skills$n`. For a single project, clone into `<project>/.claude/skills/job-search-pipeline`. The skill loads when a task matches its description.

## Requirements

Python 3.10+, `pip install python-jobspy pypdf`. Each script has `--selftest` or `--help`. Personal data goes in `facts.md` (git-ignored), never in the repo.

## License

MIT, see `LICENSE`.

## Türkçe

İlan akışı, puanlama, ilanın açık ve güvenilir olduğunu kontrol, tek bir gerçekler dosyasından (facts.md) ATS uyumlu CV uyarlama ve başvuru günlüğü. Dosyada olmayan hiçbir şey CV'de iddia edilmez. SKILL.md İngilizcedir. Kurulum: depoyu `~/.claude/skills/job-search-pipeline` klasörüne klonlayın.
