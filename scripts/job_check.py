"""Job posting pre-check: is it still open, any scam signals?

  python job_check.py URL [URL ...]
  python job_check.py --selftest

Prints LIVE / CLOSED / UNKNOWN plus red flags. Does not apply anywhere.
shortcut: plain HTTP fetch plus phrase match. JS-rendered or login-walled pages come back UNKNOWN; check
those in a browser.
"""
import re, sys, urllib.error, urllib.request

CLOSED = [r"no longer accepting", r"position (has been )?filled", r"job (is )?(closed|expired)", r"this job has expired",
          r"applications? (are )?closed", r"not accepting applications", r"page not found", r"job was removed",
          r"no longer available", r"not available anymore", r"posting (has been )?removed"]
RED_FLAGS = {
    "pays to apply / training fee": r"(registration|training|starter|application) fee|pay (a|the) fee",
    "chat-app only contact": r"\b(telegram|whatsapp|signal)\b.{0,40}(contact|reach|message|interview)",
    "check / crypto payment": r"\b(cashier'?s check|send (you )?a check|crypto|usdt|bitcoin)\b",
    "personal data too early": r"\b(ssn|passport number|bank (account|details)|national id (number|no))\b",
    "too good to be true": r"\$\s?\d{3,},?\d*\s*(per|/)\s*(day|hour)|no experience.{0,30}high pay",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 job-check"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            # Some boards redirect a closed posting to a generic listing page: the last path
            # segment of the original URL then no longer appears in the final URL.
            moved = url.rstrip("/").rsplit("/", 1)[-1] not in r.geturl()
            return (404 if moved else r.status), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return e.code, ""
        raise


def classify(status, html):
    text = re.sub(r"<[^>]+>", " ", html)
    if status in (404, 410) or any(re.search(p, text, re.I) for p in CLOSED):
        return "CLOSED", text
    return ("LIVE" if len(text.split()) > 150 else "UNKNOWN"), text


def selftest():
    assert classify(200, "<p>This job is no longer accepting applications</p>")[0] == "CLOSED"
    assert classify(200, "word " * 200)[0] == "LIVE"
    assert classify(200, "short page")[0] == "UNKNOWN"
    assert classify(410, "")[0] == "CLOSED"
    assert re.search(RED_FLAGS["pays to apply / training fee"], "A small training fee applies", re.I)
    print("selftest OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest(); sys.exit(0)
    if not sys.argv[1:] or sys.argv[1] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    for url in sys.argv[1:]:
        try:
            status, html = fetch(url)
            state, text = classify(status, html)
        except Exception as e:
            state, text = f"UNKNOWN ({type(e).__name__})", ""
        flags = [name for name, p in RED_FLAGS.items() if re.search(p, text, re.I)]
        print(f"{state:8} {url}" + (f"\n   red flags: {', '.join(flags)}" if flags else ""))
