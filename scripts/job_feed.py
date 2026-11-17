"""Job feed builder on top of JobSpy. Reads public listing pages only: no login, no applying.

  python job_feed.py --config config.json --out-dir feed [--hours 48] [--sections AB] [--max-queries N]
  python job_feed.py --selftest

Output: <out-dir>/YYYY-MM-DD.md and .csv; listings already seen are kept in <out-dir>/seen.csv.
Optional: --tracker applications.md skips postings whose URL or company+title already appears in your log.

shortcut: keyword and regex matching is crude (false positives and negatives both happen). Treat the
feed as a lead list and read the posting before applying.
shortcut: LinkedIn guest search ignores the remote filter in JobSpy, so "remote" sections append the word
to the search term and check title/location text. Upgrade if JobSpy adds a real remote filter.
"""
import argparse, csv, json, re, sys, time
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PAUSE = 4  # seconds between queries, be polite to the sites

# Built-in defaults. Every one of them can be overridden from the config file.
DEFAULT_SENIOR = r"\b(senior|sr\.?|lead|principal|staff|head of|manager|director)\b"
DEFAULT_YEARS = (r"\b[5-9]\s*\+\s*(years|yrs)|\bminimum (of )?[5-9]\s*(years|yrs)|"
                 r"\bat least [5-9]\s*(years|yrs)|\b1\d\s*\+\s*years")
DEFAULT_FLAGS = {"CODING-TEST": r"coding test|technical assessment|live coding|hackerrank|codility"}
SPONSOR_RX = r"visa sponsorship|relocation package|relocation support|work permit|sponsor"
NO_SPONSOR = re.compile(r"(no|not|without|unable to|cannot|can't|won't|don't)\s+(\w+\s+){0,3}(visa )?sponsor|"
                        r"must (already )?(have|hold) (the )?(right|authori[sz]ation|permit)", re.I)
SPONSOR_YES = re.compile(r"visa sponsorship (is )?(available|provided)|we sponsor", re.I)
REMOTE_WORDS = re.compile(r"hybrid|remote|work from home", re.I)
HARD_CURRENCIES = ("USD", "EUR", "GBP", "CHF")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def canon_url(u):
    return re.sub(r"[?#].*$", "", str(u or "")).rstrip("/")


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("reject_title_regex", DEFAULT_SENIOR)
    cfg.setdefault("reject_description_regex", [{"pattern": DEFAULT_YEARS, "reason": "5+ years required"}])
    cfg.setdefault("flag_patterns", dict(DEFAULT_FLAGS))
    return cfg


def filter_job(title, desc, section, cfg):
    """Return a rejection reason, or None if the posting is kept.
    A rule may carry "sections": ["C"] to apply to those sections only."""
    if re.search(cfg["reject_title_regex"], title or "", re.I):
        return "senior title"
    for rule in cfg["reject_description_regex"]:
        if rule.get("sections") and section not in rule["sections"]:
            continue
        if re.search(rule["pattern"], desc or "", re.I):
            return rule["reason"]
    return None


def sponsor_tag(desc):
    if not desc:
        return None
    if NO_SPONSOR.search(desc) and not SPONSOR_YES.search(desc):
        return "NO-SPONSOR"
    return "SPONSOR" if re.search(SPONSOR_RX, desc, re.I) else None


def dedup_state(url, company, title, seen_urls, seen_ct, tracker_urls, tracker_lines):
    u, ct = canon_url(url), (norm(company), norm(title))
    if u in seen_urls or ct in seen_ct:
        return "seen"
    if u and u in tracker_urls:
        return "tracked"
    c, t = ct
    if c and t and any(c in l and t in l for l in tracker_lines):
        return "tracked"
    return None


def load_seen(feed_dir):
    urls, cts = set(), set()
    p = feed_dir / "seen.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            urls.add(r["url"]); cts.add((r["company"], r["title"]))
    return urls, cts


def load_tracker(path):
    if not path or not Path(path).exists():
        return set(), []
    text = Path(path).read_text(encoding="utf-8")
    urls = {canon_url(u) for u in re.findall(r"https?://[^\s|)>\]]+", text)}
    return urls, [norm(l) for l in text.splitlines()]


def salary(r):
    lo, hi, cur, iv = r.get("min_amount"), r.get("max_amount"), r.get("currency"), r.get("interval")
    isnum = lambda x: x is not None and x == x and x != 0  # NaN-safe
    if not isnum(lo) and not isnum(hi):
        return ""
    f = lambda x: f"{x:g}" if isnum(x) else ""
    return f"{f(lo)}-{f(hi)} {cur or ''}/{iv or ''}".strip()


def build_queries(cfg, sections):
    qs = []
    for sec in cfg["sections"]:
        if sec["id"] not in sections:
            continue
        for term in sec["terms"]:
            for loc in sec["locations"]:
                qs.append(dict(
                    sec=sec["id"],
                    term=f"{term} remote" if sec.get("append_remote") else term,
                    loc=loc["name"], country=loc.get("country", "usa"),
                    remote_only=loc.get("remote_only", False),
                    require_remote=sec.get("require_remote", False),
                    sites=sec.get("sites", ["linkedin", "indeed"]),
                    n=sec.get("results", 20), desc=sec.get("fetch_description", False),
                    sponsor=sec.get("sponsor_tags", False)))
    return qs


def run(cfg, feed_dir, tracker, hours, sections, max_queries):
    from jobspy import scrape_jobs  # imported late so --selftest needs no dependency
    feed_dir.mkdir(parents=True, exist_ok=True)
    seen_urls, seen_ct = load_seen(feed_dir)
    t_urls, t_lines = load_tracker(tracker)
    stats = dict(queries=0, raw=0, elim={}, dup_seen=0, dup_tracked=0, errors=[])
    kept, run_keys = [], set()
    queries = build_queries(cfg, sections)[:max_queries]
    flags = {k: re.compile(v, re.I) for k, v in cfg["flag_patterns"].items()}
    for i, q in enumerate(queries, 1):
        stats["queries"] += 1
        label = f"{q['sec']} | {q['term']} | {q['loc']}"
        try:
            kw = dict(site_name=q["sites"], search_term=q["term"], location=q["loc"], results_wanted=q["n"],
                      hours_old=hours, country_indeed=q["country"], verbose=0)
            if q["desc"]:
                kw["fetch_description"] = True
            df = scrape_jobs(**kw)
        except Exception as e:
            stats["errors"].append(f"{label}: {type(e).__name__}: {str(e)[:120]}")
            print(f"[{i}/{len(queries)}] ERR {label}", flush=True); time.sleep(PAUSE); continue
        for site, err in df.attrs.get("errors", {}).items():
            stats["errors"].append(f"{label} [{site}]: {str(err)[:120]}")
        print(f"[{i}/{len(queries)}] {len(df)} {label}", flush=True)
        for r in df.to_dict("records"):
            stats["raw"] += 1
            title, comp = str(r.get("title") or ""), str(r.get("company") or "")
            desc, url, loc = str(r.get("description") or ""), r.get("job_url"), str(r.get("location") or "")
            is_remote = bool(r.get("is_remote"))
            reason = filter_job(title, desc, q["sec"], cfg)
            if not reason and q["require_remote"] and not (is_remote or REMOTE_WORDS.search(title + " " + loc)):
                reason = "not remote"
            if not reason and q["remote_only"] and not (is_remote or REMOTE_WORDS.search(title + " " + loc + " " + desc)):
                reason = "on-site only (wanted hybrid/remote)"
            if reason:
                stats["elim"][reason] = stats["elim"].get(reason, 0) + 1
                continue
            d = dedup_state(url, comp, title, seen_urls, seen_ct, t_urls, t_lines)
            key = (norm(comp), norm(title))
            if d == "seen" or key in run_keys or canon_url(url) in run_keys:
                stats["dup_seen"] += 1; continue
            if d == "tracked":
                stats["dup_tracked"] += 1; continue
            run_keys.add(key); run_keys.add(canon_url(url))
            tags = []
            if q["sponsor"]:
                sp = sponsor_tag(desc)
                if sp:
                    tags.append(sp)
            for name, rx in flags.items():
                if rx.search(desc):
                    tags.append(name)  # flagged, not filtered: you decide
            if r.get("currency") in HARD_CURRENCIES:
                tags.append("HARD-CURRENCY")
            kept.append(dict(section=q["sec"], title=title, company=comp, location=loc,
                             remote="yes" if is_remote else "no", salary=salary(r),
                             date=str(r.get("date_posted") or ""), url=url,
                             tags=" ".join(f"[{t}]" for t in tags), site=r.get("site")))
        time.sleep(PAUSE)
    write_outputs(cfg, kept, stats, hours, feed_dir)
    with (feed_dir / "seen.csv").open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["url", "company", "title", "first_seen"])
        for k in kept:
            w.writerow([canon_url(k["url"]), norm(k["company"]), norm(k["title"]), date.today().isoformat()])
    return kept, stats


def line(k):
    sal = f" | {k['salary']}" if k["salary"] else ""
    return f"- {k['title']} | {k['company']} | {k['location']} | remote: {k['remote']}{sal} | {k['date']} | {k['url']} {k['tags']}".rstrip()


def write_outputs(cfg, kept, stats, hours, feed_dir):
    day = date.today().isoformat()
    out = [f"# Job feed {day} (last {hours} hours)", "",
           f"> Queries: {stats['queries']} | raw: {stats['raw']} | new: {len(kept)} | seen before: {stats['dup_seen']} | already in tracker: {stats['dup_tracked']}",
           "> Filtered out: " + (", ".join(f"{v} {k}" for k, v in stats["elim"].items()) or "none"),
           f"> Failed queries: {len(stats['errors'])}" + "".join(f"\n>   - {e}" for e in stats["errors"]),
           "> Keyword matching is crude. Read each posting before applying. Nothing was applied to.", ""]
    for sec in cfg["sections"]:
        rows = [k for k in kept if k["section"] == sec["id"]]
        out += [f"## {sec['id']}) {sec.get('name', '')} ({len(rows)})", ""] + [line(k) for k in rows] + [""]
    (feed_dir / f"{day}.md").write_text("\n".join(out), encoding="utf-8")
    cols = ["section", "title", "company", "location", "remote", "salary", "date", "url", "tags", "site"]
    with (feed_dir / f"{day}.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(kept)


def selftest():
    cfg = dict(reject_title_regex=DEFAULT_SENIOR,
               reject_description_regex=[{"pattern": DEFAULT_YEARS, "reason": "5+ years required"},
                                         {"pattern": r"fluent (in )?german", "reason": "language required", "sections": ["C"]}],
               flag_patterns=dict(DEFAULT_FLAGS),
               sections=[dict(id="A", name="Local", terms=["a", "b"], locations=[dict(name="X"), dict(name="Y")]),
                         dict(id="B", name="Remote", terms=["a"], locations=[dict(name="Z")], append_remote=True, require_remote=True)])
    assert filter_job("Senior Engineer", "", "A", cfg) == "senior title"
    assert filter_job("Head of Support", "", "A", cfg) == "senior title"
    assert filter_job("Junior Engineer", "", "A", cfg) is None
    assert filter_job("Engineer", "We need 5+ years of experience", "A", cfg) == "5+ years required"
    assert filter_job("Engineer", "minimum 5 years in field", "A", cfg) == "5+ years required"
    assert filter_job("Engineer", "2+ years experience", "A", cfg) is None
    assert filter_job("Engineer", "Fluent German required", "C", cfg) == "language required"
    assert filter_job("Engineer", "Fluent German required", "A", cfg) is None  # rule is section-scoped
    assert sponsor_tag("We offer visa sponsorship and relocation support") == "SPONSOR"
    assert sponsor_tag("We do not provide visa sponsorship") == "NO-SPONSOR"
    assert sponsor_tag("Nice team, free coffee") is None
    assert canon_url("https://x.com/jobs/view/12?trk=a") == "https://x.com/jobs/view/12"
    lines = [norm("| candidate | ? | Acme GmbH | Field Service Engineer | link |")]
    assert dedup_state("https://n.com/1", "Acme GmbH", "Field Service Engineer", set(), set(), set(), lines) == "tracked"
    assert dedup_state("https://n.com/1?x=1", "B", "T", {"https://n.com/1"}, set(), set(), []) == "seen"
    assert dedup_state("https://n.com/2", "B", "T", set(), {("b", "t")}, set(), []) == "seen"
    assert dedup_state("https://n.com/4", "New Co", "Role", set(), set(), set(), lines) is None
    qs = build_queries(cfg, "AB")
    assert len(qs) == 5 and qs[-1]["term"] == "a remote"
    assert salary({"min_amount": float("nan"), "max_amount": None}) == ""
    print("selftest OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build a de-duplicated job feed from public listings.")
    ap.add_argument("--config", help="JSON config (see config.example.json)")
    ap.add_argument("--out-dir", default="feed")
    ap.add_argument("--tracker", help="optional markdown file with your application log, used for de-duplication")
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--sections", default="", help="section ids to run, e.g. AB (default: all)")
    ap.add_argument("--max-queries", type=int, default=10**6)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if not a.config:
        ap.error("--config is required")
    cfg = load_config(a.config)
    secs = a.sections.upper() or "".join(s["id"] for s in cfg["sections"])
    out = Path(a.out_dir)
    kept, st = run(cfg, out, a.tracker, a.hours, secs, a.max_queries)
    print(f"new {len(kept)} | raw {st['raw']} | filtered {st['elim']} | errors {len(st['errors'])} -> {out / (date.today().isoformat() + '.md')}")
