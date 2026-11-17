"""Score a job_feed CSV with plain rules (no model calls).

  python score_feed.py feed/2026-01-01.csv --config score_config.json
  python score_feed.py --selftest

Writes <csv-stem>-scored.csv and <csv-stem>-scored.md next to the input.
Each posting is placed in the first track whose "match" regex hits the title, then scored with that track's
rules plus the shared ones. Score = clamp(1 + points * 0.6, 1, 5).

shortcut: scores only title, company, location and tags (the feed has no description). Use the score to
order your reading, never to decide on a posting you have not read.
"""
import argparse, csv, json, re, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def has(pattern, text):
    return bool(pattern) and re.search(pattern, text, re.I) is not None


def pick_track(cfg, title):
    for t in cfg["tracks"]:
        if has(t["match"], title):
            return t
    return None


def score(row, cfg):
    title = (row.get("title") or "").lower()
    comp = (row.get("company") or "").lower()
    loc = (row.get("location") or "").lower()
    tags = row.get("tags") or ""
    sec = row.get("section")
    track = pick_track(cfg, title)
    pts = sum(n["points"] for n in cfg.get("negatives", []) if has(n["pattern"], title))
    if track:
        pts += track.get("domain_points", 3) if has(track.get("domain"), title) else track.get("base_points", 1)
        pts += 1 if has(track.get("plus"), title) else 0
        pts += 1 if has(track.get("entry_level"), title) else 0
        pts -= 1 if has(track.get("seniorish"), title) else 0
        pts += 1 if has(cfg.get("preferred_employers"), comp + " " + title) else 0
    for p in cfg.get("company_penalties", []):
        if has(p["company_regex"], comp):
            pts += p["points"]  # e.g. an employer whose hard requirement you fail
    for place, bonus in cfg.get("location_bonus", {}).items():
        if place.lower() in loc:
            pts += bonus
            break
    for tag, bonus in cfg.get("tag_points", {}).items():
        if tag in tags:
            pts += bonus
    pts += cfg.get("section_points", {}).get(sec, 0)
    return (track["name"] if track else "Other"), max(1.0, min(5.0, round(1 + pts * 0.6, 1)))


def main(path, cfg):
    p = Path(path)
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    if not rows:
        sys.exit("empty feed")
    for r in rows:
        r["track"], r["score"] = score(r, cfg)
    rows.sort(key=lambda r: (-r["score"], r["section"]))
    out_csv = p.with_name(p.stem + "-scored.csv")
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["score", "track"] + [k for k in rows[0] if k not in ("score", "track")])
        w.writeheader(); w.writerows(rows)
    floor = cfg.get("summary_min_score", 3.0)
    lines = [f"# Scored feed ({p.stem})", "",
             f"> {len(rows)} postings. Score uses title, company, location and tags only. Read the posting before applying. Full list: {out_csv.name}", ""]
    for name in [t["name"] for t in cfg["tracks"]] + ["Other"]:
        pick = [r for r in rows if r["track"] == name and r["score"] >= floor]
        if pick:
            lines += [f"## {name}: {len(pick)} at or above {floor} (top 15)"]
            lines += [f"- **{r['score']}** | {r['title']} | {r['company']} | {r['location']} | {r['tags'] or '-'} | {r['url']}" for r in pick[:15]]
            lines.append("")
    out_md = p.with_name(p.stem + "-scored.md")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    for name in [t["name"] for t in cfg["tracks"]] + ["Other"]:
        sub = [r for r in rows if r["track"] == name]
        print(f"{name}: {len(sub)} postings, >=4.0: {sum(r['score'] >= 4 for r in sub)}, >=3.5: {sum(r['score'] >= 3.5 for r in sub)}")
    print(out_md)


EXAMPLE = {
    "tracks": [
        {"name": "Software", "match": r"software|developer|full ?stack|backend|frontend",
         "domain": r"software|developer", "plus": r"\bai\b|automation|api", "entry_level": r"junior|graduate|entry|trainee", "seniorish": r"\b(ii|iii)\b|specialist"},
        {"name": "Engineering", "match": r"electrical|embedded|hardware|plc|engineer",
         "domain": r"electrical|embedded|hardware", "plus": r"test|automation|commissioning", "entry_level": r"junior|graduate|trainee"},
    ],
    "negatives": [{"pattern": r"technician|intern\b|internship", "points": -4}, {"pattern": r"manager|director", "points": -3},
                  {"pattern": r"secret clearance|principal", "points": -8}],
    "preferred_employers": r"example corp|sample industries",
    "company_penalties": [{"company_regex": r"strict employer", "points": -4, "note": "requires a credential you do not hold"}],
    "location_bonus": {"example city": 1},
    "tag_points": {"[SPONSOR]": 2, "[CODING-TEST]": -1},
    "section_points": {"B": 1},
    "summary_min_score": 3.0,
}


def selftest():
    c = EXAMPLE
    row = lambda sec, title, comp="", loc="", tags="": {"section": sec, "title": title, "company": comp, "location": loc, "tags": tags}
    t, s = score(row("A", "Junior Software Developer", "Example Corp", "Example City"), c)
    assert t == "Software" and s >= 4.0, (t, s)
    assert score(row("A", "Electrical Technician"), c)[1] == 1.0
    assert score(row("A", "Embedded Engineer", "Strict Employer"), c)[1] < score(row("A", "Embedded Engineer", "Other Co"), c)[1]
    assert score(row("B", "Software Developer (Secret Clearance)"), c)[1] < 3.0
    assert score(row("C", "Graduate Software Engineer", tags="[SPONSOR]"), c)[1] > score(row("C", "Graduate Software Engineer"), c)[1]
    assert score(row("A", "Receptionist"), c)[0] == "Other"
    print("selftest OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Score a job feed CSV with rule-based points.")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--config", help="JSON scoring config (see score_config.example.json)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if not a.csv or not a.config:
        ap.error("csv and --config are required")
    main(a.csv, json.loads(Path(a.config).read_text(encoding="utf-8")))
