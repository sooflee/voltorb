#!/usr/bin/env python3
"""Voltorb pipeline: turn per-event JSON into a net-P&L leaderboard + coverage manifest.

Reads:   data/events/*.json, data/players/aliases.json
Writes:  docs/data/leaderboard.json, docs/data/coverage.json

Net P&L is computed ONLY from events with status == "included" (which the schema
requires to have a full, named field). Excluded events are reported in the coverage
manifest but never affect player numbers. Run:  python3 pipeline/build.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_DIR = ROOT / "data" / "events"
ALIASES_PATH = ROOT / "data" / "players" / "aliases.json"
OUT_DIR = ROOT / "docs" / "data"

MIN_BUY_IN = 7000


def load_aliases():
    raw = json.loads(ALIASES_PATH.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def canon(name, aliases):
    name = " ".join(name.strip().split())
    return aliases.get(name, name)


def validate(ev, aliases, errors):
    """Append human-readable problems for event `ev` to `errors`."""
    eid = ev.get("id", "<no id>")

    def err(msg):
        errors.append(f"[{eid}] {msg}")

    for field in ("id", "name", "series", "year", "buy_in_usd", "status",
                  "field_completeness", "entries"):
        if ev.get(field) in (None, ""):
            err(f"missing required field '{field}'")

    if isinstance(ev.get("buy_in_usd"), int) and ev["buy_in_usd"] < MIN_BUY_IN:
        err(f"buy_in_usd {ev['buy_in_usd']} is below the ${MIN_BUY_IN:,} threshold")

    if ev.get("status") not in ("included", "excluded"):
        err(f"status must be 'included' or 'excluded', got {ev.get('status')!r}")

    results = ev.get("results", []) or []
    places = [r.get("place") for r in results]
    if len(places) != len(set(places)):
        err("duplicate place values in results")
    for r in results:
        if not isinstance(r.get("payout_usd"), int) or r["payout_usd"] < 0:
            err(f"bad payout_usd for place {r.get('place')}")

    pool = ev.get("prize_pool_usd")
    if isinstance(pool, int) and results:
        paid = sum(r["payout_usd"] for r in results)
        if paid > pool + 1:  # allow rounding
            err(f"sum of payouts ${paid:,} exceeds prize pool ${pool:,}")

    if ev.get("status") == "included":
        if ev.get("field_completeness") != "full":
            err("included events must have field_completeness == 'full'")
        entrants = ev.get("entrants") or []
        if not entrants:
            err("included event has no entrants list")
        if ev.get("unique_entrants") not in (None, len(entrants)):
            err(f"unique_entrants ({ev.get('unique_entrants')}) != len(entrants) ({len(entrants)})")
        entrant_set = {canon(e, aliases) for e in entrants}
        for r in results:
            if canon(r["player"], aliases) not in entrant_set:
                err(f"result player {r['player']!r} not found in entrants list")


def main():
    aliases = load_aliases()
    event_files = sorted(EVENTS_DIR.glob("*.json"))
    if not event_files:
        print("No event files found.", file=sys.stderr)
        return 1

    events, errors = [], []
    for path in event_files:
        try:
            ev = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"[{path.name}] invalid JSON: {exc}")
            continue
        validate(ev, aliases, errors)
        events.append(ev)

    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 1

    included = [e for e in events if e["status"] == "included"]
    excluded = [e for e in events if e["status"] == "excluded"]

    # ---- aggregate player P&L over included events ----
    players = {}  # canonical name -> aggregate dict

    def player(name):
        return players.setdefault(name, {
            "player": name, "events_played": 0, "itm": 0,
            "buy_ins_usd": 0, "winnings_usd": 0, "net_usd": 0,
            "events": [],
        })

    for ev in included:
        entries_by_player = {canon(k, aliases): v
                             for k, v in (ev.get("entries_by_player") or {}).items()}
        payout_by_player = {}
        for r in ev["results"]:
            payout_by_player[canon(r["player"], aliases)] = (
                payout_by_player.get(canon(r["player"], aliases), 0) + r["payout_usd"])

        for raw_name in ev["entrants"]:
            name = canon(raw_name, aliases)
            n_entries = entries_by_player.get(name, 1)
            buy_ins = ev["buy_in_usd"] * n_entries
            winnings = payout_by_player.get(name, 0)
            p = player(name)
            p["events_played"] += 1
            p["buy_ins_usd"] += buy_ins
            p["winnings_usd"] += winnings
            p["net_usd"] += winnings - buy_ins
            if winnings:
                p["itm"] += 1
            p["events"].append({
                "id": ev["id"], "name": ev["name"], "date": ev.get("date"),
                "year": ev["year"], "buy_in_usd": ev["buy_in_usd"],
                "entries": n_entries, "winnings_usd": winnings,
                "net_usd": winnings - buy_ins,
            })

    leaderboard = sorted(players.values(), key=lambda p: p["net_usd"], reverse=True)
    for i, p in enumerate(leaderboard, 1):
        p["rank"] = i
        p["roi"] = round(p["net_usd"] / p["buy_ins_usd"], 4) if p["buy_ins_usd"] else None

    summary = {
        "events_total": len(events),
        "events_included": len(included),
        "events_excluded": len(excluded),
        "players": len(leaderboard),
        "pool_buy_ins_usd": sum(p["buy_ins_usd"] for p in leaderboard),
        "pool_winnings_usd": sum(p["winnings_usd"] for p in leaderboard),
        "years": sorted({e["year"] for e in events}),
        "buy_in_floor_usd": MIN_BUY_IN,
    }

    def event_summary(ev):
        return {
            "id": ev["id"], "name": ev["name"], "series": ev["series"],
            "stop": ev.get("stop"), "date": ev.get("date"), "year": ev["year"],
            "buy_in_usd": ev["buy_in_usd"], "entries": ev["entries"],
            "status": ev["status"], "field_completeness": ev["field_completeness"],
            "exclusion_reason": ev.get("exclusion_reason"),
            "sources": ev.get("sources", []),
        }

    # Events that were evaluated by the field-sweep but did not qualify (no full
    # field). Recorded for coverage transparency; never affect P&L.
    evaluated = []
    eval_path = ROOT / "data" / "evaluated_excluded.json"
    if eval_path.exists():
        for e in json.loads(eval_path.read_text()):
            evaluated.append({
                "id": None, "name": e["name"], "series": e.get("series"),
                "stop": None, "date": None, "year": e["year"],
                "buy_in_usd": e["buy_in_usd"], "entries": None,
                "status": "excluded", "field_completeness": "evaluated_not_full",
                "exclusion_reason": e.get("exclusion_reason"), "sources": [],
                "evaluated_only": True,
            })
    summary["events_evaluated_excluded"] = len(evaluated)

    excluded_rows = [event_summary(e) for e in
                     sorted(excluded, key=lambda e: (e["year"], e.get("date") or ""))]
    excluded_rows += sorted(evaluated, key=lambda e: (e["year"], e["name"]))

    coverage = {
        "summary": summary,
        "included": [event_summary(e) for e in
                     sorted(included, key=lambda e: (e["year"], e.get("date") or ""))],
        "excluded": excluded_rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "leaderboard.json").write_text(
        json.dumps({"summary": summary, "players": leaderboard}, indent=2))
    (OUT_DIR / "coverage.json").write_text(json.dumps(coverage, indent=2))

    print(f"OK  {len(included)} included / {len(excluded)} excluded events, "
          f"{len(leaderboard)} players")
    print(f"    buy-ins ${summary['pool_buy_ins_usd']:,} | "
          f"winnings ${summary['pool_winnings_usd']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
