# Data sourcing — how to make excluded events includable

## The two gaps that block inclusion

A re-entry event can only become `included` (exact net P&L) if we can recover **both**:

1. **The complete entrant roster** — every distinct player who put money in, not just the
   in-the-money finishers.
2. **Per-player re-entry counts** — how many bullets each fired (a $25k with 3 re-entries
   cost that player $100k, not $25k).

Gap (1) is *recoverable* for high-roller events (small fields, named in live coverage).
Gap (2) is the hard one: re-entry counts are **rarely published anywhere**, even for humans.
For **freezeouts / fixed invitationals** gap (2) doesn't exist (one bullet each), which is
exactly why every currently-included event is a freezeout.

## Why the canonical databases don't solve it

**The Hendon Mob only records cashes, not fields.** Confirmed: THM stores the names/ranks/
winnings of players who finished *in the money* and does **not** keep records of players
eliminated before the cash. So THM — even with full access — gives accurate **payouts** but
**cannot** supply the busted-player buy-ins that net P&L needs. CardPlayer/GPI are the same
shape (results, not fields).

## Source accessibility (probed June 2026)

| Source | Has full fields? | Has re-entry counts? | Reachable by this agent | Reachable by a human |
|---|---|---|---|---|
| Hendon Mob (pokerdb) | ❌ cashes only | ❌ | ❌ Cloudflare CAPTCHA | ✅ |
| CardPlayer results | ❌ cashes only | ❌ | ❌ 403 anti-bot | ✅ |
| **PGT / PokerGO live reporting** | ✅ chip-count/players pages | ⚠️ derivable from live blog | ❌ 403 / login | ✅ (PokerGO sub) |
| **PokerNews live reporting** | ✅ "Chip Counts"/"Players" tab | ⚠️ derivable from live blog | ⚠️ JS-rendered, partial | ✅ |
| WSOP.com | ✅ entries + chip counts | ⚠️ total entries vs unique | ⚠️ partial | ✅ |
| Triton official site | ❌ champions only (public) | ❌ | ⚠️ summary only | ✅ |
| **tritonpoker.plus** | likely ✅ (detail platform) | unknown | ❌ SPA/login | ✅ |
| Wikipedia (incl. de/other langs) | ✅ for marquee events | n/a (freezeouts) | ✅ | ✅ |
| 25kfantasy.com | ⚠️ draft rosters, not reliable | ❌ | ✅ but thin | ✅ |

**Takeaway:** the full-field data exists almost exclusively in **live-reporting "chip count /
players" pages** (PGT, PokerNews, WSOP, Triton). Those are precisely the pages walled off from
an automated agent by login + anti-bot + JavaScript. A human in a normal browser can read them.

## What you (a human) can do that I can't

Ranked by leverage:

1. **PokerGO subscription → PGT live reporting.** Unlocks the full field (and, via the live
   blog, re-entries) for *every* PokerGO Tour event — SHRB series, Poker Masters, U.S. Poker
   Open, PGT Championship. That alone covers a large share of the excluded list. Open the
   event's "Chip Counts / Players" page and copy it (or save the HTML) → I parse it.
2. **Open anti-bot pages in your browser and hand me the data.** THM (payouts), CardPlayer,
   PokerNews chip-count tabs, tritonpoker.plus. Paste text, save HTML, or screenshot — any
   of those I can turn into event JSON.
3. **Request data access / licensing.** The Hendon Mob runs a partner **data feed/API**;
   PokerGO/PGT and Triton have media teams; Poker Industry PRO (pokerfuse) sells structured
   high-roller datasets. A real identity + email can request these; I can't authenticate or
   negotiate. Press kits frequently contain complete results.
4. **Run a real-browser scraper from your own machine/residential IP.** Datacenter IPs and my
   fetch are blocked; a headful Playwright/Puppeteer session on your network (solving the
   occasional CAPTCHA) can pull THM/CardPlayer/PGT pages at scale. I can write that script.
5. **Drop local files in `data/incoming/`.** Any spreadsheet, PDF, screenshot, or saved HTML
   of an entrant list / chip count — I'll parse it into the schema.

## Recommended model change: data tiers (optional)

Today inclusion is binary (full freezeout field or nothing). To safely absorb re-entry events
once you can supply rosters, add a completeness **tier** instead:

- **Tier A — exact.** Freezeout/fixed field, full roster. Net P&L exact. *(current bar)*
- **Tier B — lower-bound.** Re-entry event, full roster, but re-entry counts unknown → count
  1 buy-in per player. Flag clearly: "buy-ins are a lower bound; true losses ≥ shown." Net
  P&L is then a *conservative* number, not a guess.
- **Tier C — excluded.** No full roster → stays in the manifest with a reason. *(current)*

Tier B would let most Triton invitationals and WSOP high rollers onto the board (clearly
labelled) the moment you can supply their rosters, without overstating precision. It's opt-in —
say the word and I'll implement the flag + a tier filter on the site.

## Fastest concrete path

1. You pull the **PGT/PokerNews chip-count page** for a target excluded event (e.g. WSOP $250k
   SHR 2024, a Triton invitational) and paste it here.
2. I reconcile it against THM/official payouts, build the event JSON, and (Tier A or B) add it.
3. Repeat / batch. If you authorize a residential-IP scraper, I'll script the bulk pull.
