#!/usr/bin/env python3
"""Voltorb local scraper — run from YOUR machine to pull tournament data the
hosted agent cannot reach (The Hendon Mob, CardPlayer, PokerNews chip counts, PGT).

Why this exists: those sites block datacenter IPs / automated fetches with Cloudflare,
anti-bot, JavaScript, or logins. A REAL browser on YOUR network gets through. This opens
a visible Chromium so you can solve any "I'm human" check and log in (e.g. PokerGO) ONCE
— the session is saved in a local profile and reused.

For each target URL it writes into data/incoming/:
  <slug>.html   fully rendered HTML
  <slug>.txt    visible text (good for live-blog / re-entry mentions)
  <slug>.json   page title + EVERY HTML table as rows + all links

Then either paste the .txt/.json contents back to Claude, or commit data/incoming/ and
tell Claude — it parses them into data/events/*.json and rebuilds the leaderboard.

--- Setup (once) ---
  python3 -m venv .venv && source .venv/bin/activate
  pip install playwright
  playwright install chromium

--- Usage ---
  python scraper/scrape.py "https://pokerdb.thehendonmob.com/event.php?a=r&n=1028367"
  python scraper/scrape.py --targets scraper/targets.txt
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright not installed. Run:\n  pip install playwright && playwright install chromium")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "incoming"
DEFAULT_PROFILE = ROOT / ".scraper-profile"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


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


def extract(page):
    tables = []
    for tbl in page.query_selector_all("table"):
        rows = []
        for tr in tbl.query_selector_all("tr"):
            cells = [c.inner_text().strip() for c in tr.query_selector_all("th,td")]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    links = []
    for a in page.query_selector_all("a[href]"):
        txt = (a.inner_text() or "").strip()
        href = a.get_attribute("href") or ""
        if txt and href and not href.startswith("javascript"):
            links.append({"text": txt[:120], "href": href})
    return tables, links


def read_targets(path):
    urls = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            urls.append(line.split("|")[0].strip())
    return urls


def main():
    ap = argparse.ArgumentParser(description="Local headful scraper for tournament data.")
    ap.add_argument("urls", nargs="*", help="target URLs")
    ap.add_argument("--targets", help="file with one URL per line (# comments and '| note' allowed)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE),
                    help="persistent browser profile dir (keeps logins/cookies) — DO NOT COMMIT")
    ap.add_argument("--headless", action="store_true", help="run without a visible window (no CAPTCHA solving)")
    ap.add_argument("--wait", type=float, default=3.0, help="extra seconds to wait after each load")
    ap.add_argument("--auto", action="store_true", help="never pause for manual CAPTCHA/login")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.targets:
        urls += read_targets(args.targets)
    if not urls:
        sys.exit("No URLs. Pass them as args or via --targets <file>.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seen_domains = set()
    index = []

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            args.profile, headless=args.headless,
            viewport={"width": 1400, "height": 1000}, user_agent=UA)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for i, url in enumerate(urls, 1):
            dom = urlparse(url).netloc
            print(f"\n[{i}/{len(urls)}] {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"  ! navigation error: {e}")
            time.sleep(args.wait)
            title = page.title()
            text = page.inner_text("body") if page.query_selector("body") else ""

            first_visit = dom not in seen_domains
            if (not args.headless and not args.auto
                    and (first_visit or looks_blocked(title, text))):
                print("  → If you see a CAPTCHA, cookie wall, or login, handle it in the browser now.")
                print("    (For PokerGO/PGT, log in on the first visit so the session is saved.)")
                input("    Press Enter here once the REAL page is visible… ")
                time.sleep(1.0)
                title = page.title()
                text = page.inner_text("body") if page.query_selector("body") else ""
            seen_domains.add(dom)

            if looks_blocked(title, text):
                print("  ! still looks blocked — capture may be empty. Re-run and solve the challenge.")

            tables, links = extract(page)
            slug = f"{i:02d}-{slugify(url)}"
            (out / f"{slug}.html").write_text(page.content(), encoding="utf-8")
            (out / f"{slug}.txt").write_text(text, encoding="utf-8")
            rec = {
                "url": url, "title": title,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "tables": tables, "links": links[:300], "text_chars": len(text),
            }
            (out / f"{slug}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
            print(f"  ✓ saved {slug}.json  ({len(tables)} tables, {len(text)} chars of text)")
            index.append({"slug": slug, "url": url, "title": title, "tables": len(tables)})

        (out / "_index.json").write_text(json.dumps(index, indent=2))
        print(f"\nDone. Captured {len(index)} page(s) → {out}")
        if not args.headless:
            input("Press Enter to close the browser… ")
        ctx.close()


if __name__ == "__main__":
    main()
