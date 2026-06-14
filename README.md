# Voltorb

A net **profit & loss study of the high-stakes professional poker cohort** — live
tournaments with buy-ins of **$7,000+**. The goal is to triangulate, across every event,
who is actually *winning or losing* once you subtract buy-ins from winnings.

**Live site:** https://sooflee.github.io/voltorb/

> Status: **early release.** The methodology, pipeline, and site are complete and
> running on a fully-verified event set (4 included events, 2023–2025). A multi-agent
> field-sweep evaluated dozens more and rejected those without a complete public field.
> The dataset keeps expanding — see [Expanding the dataset](#expanding-the-dataset).

## The core idea (and the honest caveat)

Net P&L = winnings − **every** buy-in, including the events a player entered and busted
before the money. Doing that correctly needs a **complete entrant list** for each event.

Most public sources — including The Hendon Mob — only record *cashes*, not the full field.
So a pro who fires a $25k and busts pre-money often leaves no public trace of that buy-in.
The high-roller circuit is the exception: fields are small (often 20–100 players) and
frequently named in full in event coverage, which makes reconstruction feasible.

We turn that constraint into a rule:

- A tournament feeds the leaderboard **only if its full field is published**
  (`status: "included"`, `field_completeness: "full"`).
- Everything else is **excluded** and listed — with a reason — on the site's Coverage
  page, so it's always clear *which tournaments are used and which are not*.

Backing/staking is ignored (figures are gross of any deals or swaps), and re-entry counts
default to 1 per player unless explicitly recorded.

## How it works

```
data/events/*.json        one file per tournament (see SCHEMA.md)
data/players/aliases.json  name-variant -> canonical name
pipeline/build.py          validate + compute net P&L  ->  docs/data/*.json
docs/index.html            static GitHub Pages leaderboard + coverage manifest
```

Rebuild after editing data:

```bash
python3 pipeline/build.py     # no dependencies; Python 3.8+
```

It validates every event (buy-in ≥ $15k, payouts ⊆ prize pool, every result player is in
the entrant list for included events), then writes `docs/data/leaderboard.json` and
`docs/data/coverage.json`. The site reads those JSON files directly.

## Current dataset

**Included (12 events, true net P&L), all freezeouts with complete named fields:**

| Event | Date | Buy-in | Field |
|---|---|---|---|
| The Big One for One Drop | Jul 2012 | $1.0M | 48 |
| The Big One for One Drop | Jul 2014 | $1.0M | 42 |
| Super High Roller Bowl II | May 2016 | $300k | 49 |
| The Big One for One Drop | Jul 2018 | $1.0M | 27 |
| Super High Roller Bowl V | Dec 2018 | $300k | 36 |
| Triton Million – London | Aug 2019 | £1.05M | 54 |
| Super High Roller Bowl London | Sep 2019 | £250k | 12 |
| Super High Roller Bowl VII | Oct 2022 | $300k | 24 |
| Super High Roller Bowl VIII | Sep 2023 | $300k | 20 |
| WPT Big One for One Drop | Dec 2023 | $1.0M | 17 |
| Super High Roller Bowl IX | Aug 2024 | $306k | 24 |
| Super High Roller Bowl X | Dec 2025 | $100k | 23 |

Every one has a complete, named field and payouts that reconcile to the published prize pool.
**Excluded:** 6 events on file (full payouts but re-entry / no full roster) + 12 more the
field-sweep evaluated and rejected — all listed with reasons on the site's Coverage page.

With **164 players across 12 events (2012–2025)** the leaderboard triangulates deeply:
Antonio Esfandiari (+$15.0M, won 2012), Bryn Kenney (8 events, +$18.1M), Daniel Negreanu
(8 events, +$7.3M), Cary Katz (10 events, −$1.95M), Phil Ivey (5 events, −$4.3M, three $1M
One Drops cashed none).

Why only freezeouts: exact net P&L needs every buy-in, including busts → a complete field.
That is only knowable for freezeouts (one entry per player). Re-entry events can't be made
exact even with full scraping — see [`SOURCING.md`](SOURCING.md) and the WSOP $250k test in
`data/events/2024-06-23-wsop-e55-250k-shr.json`.

## Expanding the dataset

1. Add a `data/events/YYYY-MM-DD-slug.json` file following [`SCHEMA.md`](SCHEMA.md).
2. To make it count toward P&L, supply the **complete** `entrants` list and set
   `status: "included"`, `field_completeness: "full"`. Otherwise mark it `excluded` with
   an `exclusion_reason`.
3. Add any new name spellings to `data/players/aliases.json`.
4. Run `python3 pipeline/build.py` and commit. The Pages site updates from `docs/`.

Best candidate series (small, well-documented fields): Super High Roller Bowl, Triton
invitational/main events, WSOP $250k SHR, EPT/PGT super high rollers, WPT World Championship
high rollers. Earlier years can be added the same way.
