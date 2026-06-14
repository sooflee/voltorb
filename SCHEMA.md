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
| `buy_in_usd` | integer | yes | **Total cost to enter once, in USD, including fee.** Must be ≥ 15000. |
| `currency` | string | no | Original currency if not USD; `buy_in_usd` is always the USD figure used. |
| `entries` | integer | yes | Total entries incl. re-entries. |
| `unique_entrants` | integer | yes | Distinct players in the field. |
| `prize_pool_usd` | integer | no | Stated prize pool, used as a validation cross-check. |
| `status` | string | yes | `included` or `excluded`. Only `included` events feed the P&L. |
| `field_completeness` | string | yes | `full` (every entrant named), `itm_only` (only cashers known), `partial`. |
| `exclusion_reason` | string\|null | yes | Why excluded; `null` when included. |
| `sources` | string[] | yes | URLs the data was reconstructed from. |
| `entrants` | string[] | when `included` | **Complete** list of distinct entrants (canonical names). Required for `included`. |
| `entries_by_player` | object | no | `{ "Player": n }` overriding entry count for re-entry events; defaults to 1 each. |
| `results` | object[] | yes | In-the-money finishers: `{ "place": int, "player": str, "payout_usd": int }`. |

## Inclusion rule

An event may be `status: "included"` **only if `field_completeness == "full"`** — i.e. every
player who put money in is named in `entrants`. That is the only way net P&L (winnings minus
*all* buy-ins, including players who busted before the money) is exact.

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

- `buy_in_usd >= 15000`.
- Every `results[].player` must appear in `entrants` (for included events).
- `place` values are unique and positive.
- If `prize_pool_usd` is present, `sum(payout_usd)` must not exceed it.
- `len(entrants) == unique_entrants` for included events.
