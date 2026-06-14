#!/usr/bin/env python3
"""Drive your REAL Safari to capture pages that block automated browser engines.

macOS only. This uses AppleScript to script the actual Safari app — the same browser,
profile, and session you use by hand — so there is NO webdriver/automation fingerprint.
Cloudflare sees exactly what it sees when you browse manually, which is why this works
where Playwright (WebKit/Chromium) gets blocked.

ONE-TIME SETUP:
  1. Safari ▸ Settings ▸ Advanced ▸ check "Show features for web developers"
     (older macOS: "Show Develop menu in menu bar").
  2. Safari ▸ Develop menu ▸ check "Allow JavaScript from Apple Events".
  3. First run pops a macOS prompt "Terminal wants to control Safari" → click OK
     (also approve under System Settings ▸ Privacy & Security ▸ Automation if asked).

USAGE:
  python scraper/safari_scrape.py --targets scraper/targets.txt
  python scraper/safari_scrape.py "https://pokerdb.thehendonmob.com/event.php?a=r&n=1028367"

For each URL it navigates your front Safari tab and writes into data/incoming/:
  <slug>.json   title + every HTML table as rows + links + visible text
  <slug>.txt    visible text
Then paste those back to Claude (or commit data/incoming/) for ingestion.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

if sys.platform != "darwin":
    sys.exit("safari_scrape.py is macOS-only. On other systems use scraper/scrape.py.")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "incoming"

# JS run INSIDE your Safari tab to serialise the page (tables/links/text).
EXTRACT_JS = r"""
(function(){
  function t(e){return ((e&&e.innerText)||'').replace(/[ \t]+\n/g,'\n').trim();}
  var tables=[].map.call(document.querySelectorAll('table'),function(tb){
    return [].map.call(tb.querySelectorAll('tr'),function(tr){
      return [].map.call(tr.querySelectorAll('th,td'),function(c){return t(c);});
    }).filter(function(r){return r.some(function(x){return x;});});
  }).filter(function(r){return r.length;});
  var links=[].slice.call(document.querySelectorAll('a[href]')).map(function(a){
    return {text:t(a).slice(0,120),href:a.href};
  }).filter(function(l){return l.text&&l.href;}).slice(0,400);
  return JSON.stringify({title:document.title,url:location.href,
    tables:tables,links:links,text:document.body?t(document.body):''});
})();
"""


def osa(script):
    r = subprocess.run(["osascript", "-"], input=script, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def set_url(url):
    osa(f'''tell application "Safari"
  activate
  if (count of documents) is 0 then make new document
  set URL of front document to "{url}"
end tell''')


def run_js_inline(js):
    # js must be a one-liner with no double quotes issues; used for tiny probes
    return osa(f'tell application "Safari" to do JavaScript "{js}" in front document')


def run_js_file(path):
    return osa(f'''tell application "Safari"
  set jsSrc to read POSIX file "{path}" as «class utf8»
  do JavaScript jsSrc in front document
end tell''')


def slugify(url):
    p = urlparse(url)
    base = (p.netloc + p.path).strip("/")
    q = p.query.replace("&", "_").replace("=", "-")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", base + (("-" + q) if q else "")).strip("-").lower()
    return s[:120] or "page"


def looks_blocked(title, text):
    t = (title or "").lower()
    head = (text or "")[:600].lower()
    return ("just a moment" in t or "attention required" in t
            or "verify you are human" in head or "checking your browser" in head)


def read_targets(path):
    urls = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            urls.append(line.split("|")[0].strip())
    return urls


def main():
    ap = argparse.ArgumentParser(description="Capture pages via your real Safari (macOS).")
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--targets")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--wait", type=float, default=2.5, help="settle seconds after load")
    ap.add_argument("--timeout", type=float, default=45, help="max seconds to wait for load")
    ap.add_argument("--auto", action="store_true", help="don't pause for manual CAPTCHA")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.targets:
        urls += read_targets(args.targets)
    if not urls:
        sys.exit("No URLs. Pass them as args or via --targets <file>.")

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    js_file = out / "_extract.js"
    js_file.write_text(EXTRACT_JS, encoding="utf-8")

    # sanity: confirm AppleScript control + JS-from-AppleEvents are enabled
    try:
        set_url("about:blank")
        run_js_inline("1")
    except RuntimeError as e:
        sys.exit("Safari isn't controllable yet.\n"
                 "  • Enable Safari ▸ Develop ▸ 'Allow JavaScript from Apple Events'\n"
                 "  • Approve the 'control Safari' prompt (System Settings ▸ Privacy ▸ Automation)\n"
                 f"AppleScript said: {e}")

    seen_domains, index = set(), []
    for i, url in enumerate(urls, 1):
        host = urlparse(url).netloc
        print(f"\n[{i}/{len(urls)}] {url}")
        set_url(url)
        time.sleep(1.5)
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            try:
                rs = run_js_inline("document.readyState")
                here = run_js_inline("location.host")
            except RuntimeError:
                rs, here = "", ""
            if rs == "complete" and host.split(":")[0] in here:
                break
            time.sleep(1.0)
        time.sleep(args.wait)

        try:
            raw = run_js_file(js_file)
            rec = json.loads(raw)
        except (RuntimeError, json.JSONDecodeError) as e:
            print(f"  ! extract failed: {e}")
            rec = {"title": "", "url": url, "tables": [], "links": [], "text": ""}

        first_visit = host not in seen_domains
        if not args.auto and (first_visit or looks_blocked(rec.get("title"), rec.get("text"))):
            if looks_blocked(rec.get("title"), rec.get("text")):
                print("  → Cloudflare/login wall detected. Solve it in the Safari window.")
            else:
                print("  → First visit to this site. If a wall appears, clear it in Safari.")
            input("    Press Enter once the REAL page is visible in Safari… ")
            time.sleep(1.0)
            try:
                rec = json.loads(run_js_file(js_file))
            except Exception:
                pass
        seen_domains.add(host)

        rec["captured_at"] = datetime.now(timezone.utc).isoformat()
        slug = f"{i:02d}-{slugify(url)}"
        (out / f"{slug}.txt").write_text(rec.get("text", ""), encoding="utf-8")
        (out / f"{slug}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
        ntab = len(rec.get("tables", []))
        print(f"  ✓ saved {slug}.json  ({ntab} tables, {len(rec.get('text',''))} chars)"
              + ("  ⚠ still looks blocked" if looks_blocked(rec.get('title'), rec.get('text')) else ""))
        index.append({"slug": slug, "url": url, "title": rec.get("title"), "tables": ntab})

    (out / "_index.json").write_text(json.dumps(index, indent=2))
    print(f"\nDone. Captured {len(index)} page(s) → {out}")


if __name__ == "__main__":
    main()
