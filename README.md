# Voltorb

A net **profit & loss study of the high-stakes professional poker cohort** — live
tournaments (2023–present) with buy-ins of **$11,000+**. The goal is to triangulate, across every event,
who is actually *winning or losing* once you subtract buy-ins from winnings.

**Live site:** https://sooflee.github.io/voltorb/

> Status: **sample release.** The methodology, pipeline, and site are complete and
> running on a small, fully-verified event set. The dataset is being expanded — see
> [Expanding the dataset](#expanding-the-dataset).

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

## Current sample

| | |
|---|---|
| **Included (1)** | Super High Roller Bowl IX — Cyprus, Aug 2024 · $306k · 24 entrants, full field |
| **Excluded (4)** | SHRB X 2025, SHRB $100k PLO 2024, WSOP $250k SHR 2024, Triton Montenegro GG MILLION$ $25k — full fields not published |

Super High Roller Bowl IX is fully reconstructable: all 24 entrants are named and the four
payouts sum exactly to the published $7,056,000 prize pool.

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
