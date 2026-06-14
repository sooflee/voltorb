# Event data schema

Each tournament is one JSON file in `data/events/`, named `YYYY-MM-DD-slug.json`.

The pipeline (`pipeline/build.py`) reads every file, canonicalizes player names via
`data/players/aliases.json`, and computes per-player net P&L from the **included** events.

## Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable unique id, usually the filename stem. |
| `name` | string | yes | Event name as published. |
| `series` | string | yes | e.g. `Super High Roller Bowl`, `Triton Super High Roller Series`. |
| `tour` | string | no | Sanctioning body, e.g. `PokerGO Tour (PGT)`, `WSOP`, `Triton`. |
| `stop` | string | no | Festival / stop, e.g. `SHRB Cyprus 2024`. |
| `location` | string | no | Venue, city, country. |
| `date` | string (YYYY-MM-DD) | yes | Day the event concluded (used for year bucketing). |
| `year` | integer | yes | Calendar year. |
| `game` | string | yes | e.g. `No-Limit Hold'em`, `Pot-Limit Omaha`. |
| `format` | string | no | `freezeout` or `re-entry`. |
| `buy_in_usd` | integer | yes | **Total cost to enter once, in USD, including fee.** Must be ≥ 7000. |
| `currency` | string | no | Original currency if not USD; `buy_in_usd` is always the USD figure used. |
| `entries` | integer | yes | Total entries incl. re-entries. |
| `unique_entrants` | integer | yes | Distinct players in the field. |
| `prize_pool_usd` | integer | no | Stated prize pool, used as a validation cross-check. |
| `status` | string | yes | `included` or `excluded`. Only `included` events feed the P&L. |
| `field_completeness` | string | yes | `full` (every entrant named), `full_named_plus_anon` (every seat accounted for, but N seats anonymous), `itm_only` (only cashers known), `partial`. |
| `anonymous_entrants` | integer | no | Count of seats that were real entrants but whom the source did not name (e.g. an anonymous businessman). Default 0. Requires `full_named_plus_anon`. These must be non-cashers; their buy-ins are counted in event/anonymous totals but never attributed to a named leaderboard player. |
| `exclusion_reason` | string\|null | yes | Why excluded; `null` when included. |
| `sources` | string[] | yes | URLs the data was reconstructed from. |
| `entrants` | string[] | when `included` | **Complete** list of distinct entrants (canonical names). Required for `included`. |
| `entries_by_player` | object | no | `{ "Player": n }` overriding entry count for re-entry events; defaults to 1 each. |
| `results` | object[] | yes | In-the-money finishers: `{ "place": int, "player": str, "payout_usd": int }`. |

## Inclusion rule

An event may be `status: "included"` only if **every seat is accounted for** — either
`field_completeness == "full"` (every entrant named in `entrants`), or
`field_completeness == "full_named_plus_anon"` (every entrant named **except** a known number
of anonymous non-cashing seats, recorded in `anonymous_entrants`). Both keep net P&L exact for
the named players: anonymous seats' buy-ins are tallied separately and never land on a named
player. A re-entry event whose per-player bullet counts are unknown can **not** be included this
way — that is a different problem (unknown buy-ins, not unknown names).

Events without a published full field are kept as `status: "excluded"` with an
`exclusion_reason`, so coverage is transparent — they appear on the site's coverage page but do
not affect the leaderboard. This is the "mark down which tournaments are used and which are not"
requirement.

## P&L definitions

For each `included` event and each entrant:

```
buy_ins   = buy_in_usd * (entries_by_player[player] or 1)
winnings  = payout_usd if the player cashed, else 0
net       = winnings - buy_ins
```

Aggregated across all included events per canonical player:

```
total_buy_ins, total_winnings, net_pnl = total_winnings - total_buy_ins
roi = net_pnl / total_buy_ins
```

## Validation (enforced by build.py)

- `buy_in_usd >= 7000`.
- Every `results[].player` must appear in `entrants` (for included events).
- `place` values are unique and positive.
- If `prize_pool_usd` is present, `sum(payout_usd)` must not exceed it.
- `len(entrants) + anonymous_entrants == unique_entrants` for included events.
