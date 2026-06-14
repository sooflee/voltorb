# Voltorb scraper — getting data the hosted agent can't reach

This runs on **your machine** in a **real, visible browser** so it gets past the Cloudflare /
anti-bot / login walls that block the hosted agent. You solve any "I'm human" check or log in
once; the session is saved and reused.

## 1. Install (once)

```bash
cd /Users/benson/Projects/voltorb
python3 -m venv .venv
source .venv/bin/activate
pip install playwright
playwright install chromium
```

## 2. Pick what to capture

For each event you want on the leaderboard, you want **two** pages:

| You need | Where | What it gives |
|---|---|---|
| **Full field** (every entrant) | a **chip-count / players** page | the roster → buy-ins for everyone, incl. busts |
| **Payouts** | the **results** table | winnings per cashing player |

A **freezeout** (one buy-in each) with both = exact net P&L → it can be `included`.
A **re-entry** event also needs re-entry counts; capture the **live-blog text** too — it often
says "X entries, Y unique" and "so-and-so re-entered". (Re-entry counts are the one thing that
may still be unrecoverable; we exclude what we genuinely can't pin down.)

### Where to get each page
- **Payouts:** search the event on [thehendonmob.com](https://www.thehendonmob.com), open the
  results page, copy the `event.php?a=r&n=…` URL. (Or CardPlayer's `/results` page.)
- **Full field:** on [pokernews.com](https://www.pokernews.com) open the event and click the
  **"Chip Counts"** tab — copy that URL. For PokerGO Tour events, log into **PokerGO** and use
  the event's live-reporting page.
- **Festival index:** a Hendon Mob `festival.php?a=r&n=…` page lists links to every event in a
  stop — capture it first to harvest the per-event URLs.

Put the URLs in `scraper/targets.txt` (copy `targets.example.txt` as a starting point).

## 3. Run

```bash
source .venv/bin/activate
python scraper/scrape.py --targets scraper/targets.txt
```

A Chromium window opens. On the **first** visit to each site:
- Hendon Mob / CardPlayer → solve the Cloudflare check if shown.
- PokerGO → log in.

Then switch back to the terminal and press **Enter** to capture. Output lands in
`data/incoming/` as `<slug>.html`, `.txt`, and `.json` (the `.json` has every table as rows).

## 4. Hand it back to Claude

Either:
- **Paste** the contents of the relevant `data/incoming/*.txt` or `*.json` into the chat, or
- **Commit** `data/incoming/` and say so — Claude parses it into `data/events/*.json`, runs
  `python3 pipeline/build.py`, and the leaderboard updates.

## Notes
- `.scraper-profile/` holds your cookies/logins — it is git-ignored. **Never commit it.**
- `data/incoming/` raw dumps are git-ignored too (large/copyright); only the distilled
  `data/events/*.json` gets committed.
- Be polite: this is for assembling a research dataset, not bulk redistribution. Respect each
  site's terms; keep volumes low.
