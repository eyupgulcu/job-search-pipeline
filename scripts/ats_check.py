"""Build CV PDFs from HTML and run ATS-style checks on them.

  python ats_check.py --dir cv/                       # rebuild every CV-*.html to PDF, then check
  python ats_check.py --dir cv/ --no-build            # check existing PDFs only
  python ats_check.py --dir cv/ --keywords job.txt CV-Backend.pdf   # also list job keywords missing from that CV
  python ats_check.py --selftest

Needs: pypdf (pip install pypdf) and, for building, Chrome or Chromium (--chrome or CHROME_PATH).
Config (--config, optional JSON): {"required": ["you@example.com", "..."], "headings": ["SUMMARY", ...],
"min_chars": 1000, "min_links": 3}. "required" are strings that must appear in the text layer.
Forbidden terms come from the "## Forbidden" section of facts.md (one "- term" per line): things the CV
must never say.
Exit code 1 if any check fails.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

DEFAULTS = {"required": [], "headings": ["SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION"], "min_chars": 1000, "min_links": 3}
CHROME_CANDIDATES = ["chrome", "google-chrome", "chromium", "chromium-browser",
                     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]


def find_chrome(explicit=None):
    for c in [explicit, os.environ.get("CHROME_PATH")] + CHROME_CANDIDATES:
        if c and (Path(c).exists() or shutil.which(c)):
            return c
    sys.exit("Chrome not found: pass --chrome or set CHROME_PATH")


def forbidden_terms(facts_path):
    text = Path(facts_path).read_text(encoding="utf-8")
    if "## Forbidden" not in text:
        return []
    section = re.split(r"^## ", text.split("## Forbidden", 1)[1], maxsplit=1, flags=re.M)[0]
    return [m.group(1).strip() for m in re.finditer(r"^- (.+)$", section, re.M)]


def build(html, chrome):
    pdf = html.with_suffix(".pdf")
    before = pdf.stat().st_mtime if pdf.exists() else 0
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri()], capture_output=True, timeout=60)
    # Chrome can fail silently and leave a stale PDF behind. Prove the file is new.
    if not pdf.exists() or pdf.stat().st_mtime <= before:
        sys.exit(f"BUILD FAILED: {pdf.name} was not rewritten")


def check(pdf, forbidden, cfg):
    from pypdf import PdfReader
    r = PdfReader(pdf)
    text = "".join(p.extract_text() or "" for p in r.pages)
    flat = text.upper()
    uris = [a.get_object()["/A"]["/URI"] for p in r.pages for a in (p.get("/Annots") or [])
            if "/URI" in a.get_object().get("/A", {})]
    fails = []
    if len(r.pages) != 1: fails.append(f"{len(r.pages)} pages (want 1)")
    if len(text) < cfg["min_chars"]: fails.append("little or no text layer")
    fails += [f"missing '{s}'" for s in cfg["required"] if s not in text]
    fails += [f"missing heading {h}" for h in cfg["headings"] if h.upper() not in flat]
    fails += [f"forbidden '{t}'" for t in forbidden if re.search(rf"\b{re.escape(t)}\b", text, re.I)]
    if "\ufffd" in text or "\ufb01" in text or "\ufb02" in text: fails.append("broken characters or ligatures")
    if len(uris) < cfg["min_links"]: fails.append(f"only {len(uris)} clickable links (want {cfg['min_links']})")
    print(("OK   " if not fails else "FAIL ") + Path(pdf).name + ("" if not fails else ": " + "; ".join(fails)))
    return not fails, text


def missing_keywords(job_file, text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9.+#/-]{2,}", Path(job_file).read_text(encoding="utf-8"))
    tech = {w for w in words if w[0].isupper() or any(c in w for c in ".+#")}
    return sorted(w for w in tech if w.lower() not in text.lower())


def _tiny_pdf(path, body):
    """Hand-built one-page PDF with a text layer, only for the selftest."""
    stream = f"BT /F1 12 Tf 20 700 Td ({body}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    Path(path).write_bytes(out)


def selftest():
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "facts.md").write_text("# Facts\n\n## Forbidden\n- Kubernetes expert\n- ten years\n\n## Other\n- keep me\n", encoding="utf-8")
    assert forbidden_terms(d / "facts.md") == ["Kubernetes expert", "ten years"]
    cfg = dict(DEFAULTS, required=["jane@example.com"], min_chars=20, min_links=0)
    _tiny_pdf(d / "a.pdf", "SUMMARY SKILLS EXPERIENCE EDUCATION jane@example.com")
    assert check(d / "a.pdf", ["Kubernetes expert"], cfg)[0] is True
    _tiny_pdf(d / "b.pdf", "SUMMARY SKILLS EXPERIENCE EDUCATION jane@example.com Kubernetes expert")
    assert check(d / "b.pdf", ["Kubernetes expert"], cfg)[0] is False
    _tiny_pdf(d / "c.pdf", "SUMMARY SKILLS")
    assert check(d / "c.pdf", [], cfg)[0] is False  # missing contact and headings
    (d / "job.txt").write_text("We use Python and Terraform with FastAPI", encoding="utf-8")
    assert missing_keywords(d / "job.txt", "python fastapi") == ["Terraform"]
    print("selftest OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build CV PDFs from HTML and run ATS-style checks.")
    ap.add_argument("pdfs", nargs="*", help="specific PDF names inside --dir (default: all CV-*.pdf)")
    ap.add_argument("--dir", default=".", help="folder holding CV-*.html / CV-*.pdf and facts.md")
    ap.add_argument("--facts", help="facts file (default: <dir>/facts.md)")
    ap.add_argument("--config", help="JSON config, see module docstring")
    ap.add_argument("--chrome", help="path to Chrome/Chromium")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--keywords", help="job posting text file; list its keywords missing from the CV")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    root = Path(a.dir)
    cfg = dict(DEFAULTS)
    if a.config:
        cfg.update(json.loads(Path(a.config).read_text(encoding="utf-8")))
    if not a.no_build and not a.keywords:
        chrome = find_chrome(a.chrome)
        for h in sorted(root.glob("CV-*.html")):
            build(h, chrome)
    targets = [root / p for p in a.pdfs] or sorted(root.glob("CV-*.pdf"))
    facts = Path(a.facts) if a.facts else root / "facts.md"
    forbidden = forbidden_terms(facts) if facts.exists() else []
    ok = True
    for pdf in targets:
        good, text = check(pdf, forbidden, cfg)
        ok &= good
        if a.keywords:
            print("  job keywords not in CV (add only if true, via facts.md):", ", ".join(missing_keywords(a.keywords, text)))
    sys.exit(0 if ok else 1)
