"""Render a card from the slate sheet plus the agent's decisions.

Numbers come only from the slate sheet. The decisions file carries status and
reasons; it cannot carry a line, a price or a stake. A Bet the numbers do not
support is refused.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

from engine.odds.espn import SourceError

STATUSES = ("Bet", "Conditional", "Pass")
REASON_KEYS = ("price", "matchup", "situation", "kills_it")
FORBIDDEN = ("line", "price_paid", "odds", "stake", "units", "edge", "value", "dont_bet_past")


def load_decisions(path) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    out = {}
    for d in data.get("decisions", []) or []:
        for k in FORBIDDEN:
            if k in d:
                raise SourceError(f"decisions file may not set '{k}' (numbers come from the slate sheet): {d.get('game')}")
        for k in ("game", "market", "side", "status"):
            if k not in d:
                raise SourceError(f"decision is missing '{k}': {d}")
        if d["status"] not in STATUSES:
            raise SourceError(f"status must be one of {STATUSES}: {d}")
        if d["status"] in ("Bet", "Conditional"):
            r = d.get("reasons") or {}
            missing = [k for k in REASON_KEYS if not str(r.get(k, "")).strip()]
            if missing:
                raise SourceError(f"{d['status']} on {d['game']} needs reasons: {missing}")
            if d["status"] == "Conditional" and not str(d.get("condition", "")).strip():
                raise SourceError(f"Conditional on {d['game']} needs the exact condition")
            if not str(d.get("summary", "")).strip():
                raise SourceError(f"{d['status']} on {d['game']} needs a one-sentence 'summary' of why it is a bet")
            if len(str(d["summary"]).split()) > 45:
                raise SourceError(f"'summary' on {d['game']} is too long; one plain sentence")
            if d["status"] == "Conditional" and len(str(d["condition"]).split()) > 30:
                raise SourceError(f"'condition' on {d['game']} is too long; one short checkable sentence")
        elif not str(d.get("why_pass", "")).strip():
            raise SourceError(f"Pass on {d['game']} needs 'why_pass'")
        out[(d["game"], d["market"], d["side"])] = d
    return out, data.get("slate_note", "")


def _fmt(x, signed=True):
    if x is None:
        return "n/a"
    return f"{x:+g}" if signed else f"{x:g}"


def fair_sentence(sheet: dict, pc: dict) -> str:
    """Describes how 'Fair' was built, from the same setting the number came from."""
    st = sheet.get("settings", {})
    use_model = st.get("use_model_leg", pc.get("use_model_leg", False))
    if use_model:
        w = st.get("market_weight", pc["market_weight"])
        return f"\"Fair\" is {round(100 * w)}% Pinnacle with the vig removed and {round(100 * (1 - w))}% model."
    return ("\"Fair\" is Pinnacle's line with the vig removed, 100%, moved only by this week's sourced adjustments "
            "(the model is switched off because it did not beat the closing line in testing). "
            "\"DraftKings first seen by us\" is the first number our own logger recorded (it began 2026-11-21), not a true opener.")


def _lane_block(cfg: dict, sport: str) -> list[str]:
    """Lane header generated from config and the database; empty when the config has no lanes section (tests)."""
    if not cfg.get("lanes"):
        return []
    from engine import config, lanes
    from engine.odds import snapshots
    try:
        con = snapshots.connect(config.DB, read_only=True)
    except Exception:
        con = None
    try:
        return lanes.card_block(cfg, con, sport)
    finally:
        if con is not None:
            con.close()


def build(sheet: dict, decisions: dict, note: str, cfg: dict, strict: bool = True) -> tuple[str, list[dict]]:
    """strict=False is for re-pricing an existing card: a Bet the fresh numbers no longer
    support becomes a Pass marked "value gone" instead of an error."""
    tz = ZoneInfo(cfg["timezone_display"])
    pc = cfg["picks"]
    from engine import config as _config
    unit = _config.unit_for(cfg, sheet.get("sport"))
    built = datetime.fromisoformat(sheet["built_utc"]).astimezone(tz)
    picks, passes, rows = [], [], []
    for g in sheet["games"]:
        kick = datetime.fromisoformat(g["start_utc"]).astimezone(tz)
        for m in g["markets"]:
            for s in m.get("sides", []):
                d = decisions.get((g["game"], m["market"], s["side"]))
                if d is None:
                    if s["numbers_say_bet"] and strict:
                        raise SourceError(f"the numbers flag {s['pick']} ({g['game']}) but there is no decision for it")
                    continue
                downgraded = None
                if d["status"] in ("Bet", "Conditional") and not s["numbers_say_bet"]:
                    if strict and d["status"] == "Bet":
                        raise SourceError(f"refused: Bet on {s['pick']} ({g['game']}) but the numbers do not support it")
                    if not strict:
                        downgraded = (f"Value gone: your book is now {s['pick']} ({int(s['price']):+d}), "
                                      f"which no longer clears the bar. Would be a bet again at {s['dont_bet_past'] or 'no nearby number'}.")
                        d = {**d, "status": "Pass", "why_pass": downgraded}
                if d["status"] == "Bet" and s.get("max_status") == "Conditional":
                    if strict:
                        raise SourceError(f"refused: Bet on {s['pick']} ({g['game']}); the {s.get('model')} model allows a Conditional at most")
                    d = {**d, "status": "Conditional", "condition": d.get("condition") or "Forecast still windy two hours before kickoff."}
                units = {"Bet": pc["max_units"], "Conditional": pc["conditional_units"], "Pass": 0}[d["status"]]
                rec = {"game": g["game"], "kick": kick, "market": m["market"], "pick": s["pick"], "price": s["price"],
                       "status": d["status"], "units": units, "dollars": units * unit, "value": s["value"],
                       "edge_points": s["edge_points"], "dont_bet_past": s["dont_bet_past"], "fair": m["fair_line"],
                       "book_line": m.get("book_line"), "decision": d, "numbers_say_bet": s["numbers_say_bet"],
                       "event_id": g["event_id"], "side": s["side"], "downgraded": downgraded,
                       "limit_line": s.get("limit_line")}
                (picks if d["status"] != "Pass" else passes).append(rec)
                rows.append(rec)

    # one position per game: a side and a total (or two sides) in the same game move together, so only the strongest stays live
    by_game: dict[str, list[dict]] = {}
    for r in picks:
        by_game.setdefault(r["event_id"], []).append(r)
    for group in by_game.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda r: (r["status"] == "Bet", r["value"]), reverse=True)
        keep = group[0]
        for r in group[1:]:
            msg = (f"Same game as {keep['pick']} ({keep['status']}). One position per game, because a side and a total in the same game "
                   f"are not independent bets; the stronger one stays.")
            r.update(status="Pass", units=0, dollars=0, downgraded=msg, decision={**r["decision"], "status": "Pass", "why_pass": msg})
            picks.remove(r)
            passes.append(r)

    if not sheet["games"]:
        why = "; ".join(sheet.get("problems") or ["your book has no games posted for this sport right now"])
        return f"# {sheet.get('sport', '')} card\n\nBuilt {built:%a %b %-d, %-I:%M %p} Mountain. Nothing to price: {why}\n", []
    first = min(datetime.fromisoformat(g["start_utc"]) for g in sheet["games"]).astimezone(tz)
    label = {"NFL": "NFL", "College": "College football", "NBA": "NBA"}.get(sheet.get("sport", "NFL"), sheet.get("sport", ""))
    out = [f"# {label} card for {first:%A %b %-d, %Y}", "",
           f"Built {built:%a %b %-d, %-I:%M %p} Mountain from Wagerhouse, Pinnacle and DraftKings prices at that minute. "
           f"Unit ${unit}; cap {pc['max_units']} unit a bet until the engine has 100 graded picks.", ""]
    out += _lane_block(cfg, sheet.get("sport", "NFL"))
    if note:
        out += [note.strip(), ""]
    out += ["## Picks", ""]
    if picks:
        out += ["| Game (kick MT) | Pick | Status | Stake | Don't bet past | Edge |", "|---|---|---|---|---|---|"]
        for r in picks:
            out.append(f"| {r['game']} ({r['kick']:%a %-I:%M %p}) | {r['pick']} ({int(r['price']):+d}) | {r['status']} | "
                       f"{r['units']:g}u / ${r['dollars']:g} | {r['dont_bet_past'] or 'this number only'} | "
                       f"{r['edge_points']:+.1f} pts, {100 * r['value']:+.1f}% |")
        out.append("")
        for r in picks:
            d = r["decision"]
            out += [f"**{r['pick']}** ({r['status']})", ""]
            out.append(f"- In one line: {' '.join(str(d['summary']).split())}")
            if d["status"] == "Conditional":
                out.append(f"- Bet only if: {' '.join(str(d['condition']).split())}")
            out += [f"- Price: {d['reasons']['price']}", f"- Matchup: {d['reasons']['matchup']}",
                    f"- Situation: {d['reasons']['situation']}", f"- What kills it: {d['reasons']['kills_it']}", ""]
    else:
        out += ["**No bets.** Nothing on this slate clears the bar at the current numbers.", ""]

    out += ["## Looked at and passed", ""]
    if passes:
        out += ["| Game | Side the numbers leaned to | Your book | Fair line | Why it is a pass | Would be a bet at |", "|---|---|---|---|---|---|"]
        for r in passes:
            would = r["dont_bet_past"] if not r["numbers_say_bet"] and r["dont_bet_past"] else ("only with a new reason" if r["numbers_say_bet"] else "no nearby number")
            out.append(f"| {r['game']} | {r['pick']} | {_fmt(r['book_line'], r['market'] == 'spread')} | "
                       f"{_fmt(r['fair'], r['market'] == 'spread')} | {' '.join(str(r['decision']['why_pass']).split())} | {would} |")
        out.append("")
    else:
        out += ["None needed a second look.", ""]

    use_model = sheet.get("settings", {}).get("use_model_leg", False)
    out += ["## Every game, every number", "",
            "Spreads are from the home team's side (negative means the home team is favored). "]
    if use_model:
        out[-1] += ("\"Market ratings\" is what the market's own closing lines said about these teams before this week. "
                    "\"Public systems\" is the average of about 50 published computer ratings. "
                    "\"Model\" is those two averaged, plus this week's adjustments. ")
    out[-1] += fair_sentence(sheet, pc)
    out.append("")
    if use_model:
        out += ["| Game | Market ratings | Public systems | Adjust | Model | Pinnacle | Fair | Your book | DraftKings first seen by us → now |", "|---|---|---|---|---|---|---|---|---|"]
    else:
        out += ["| Game | Adjust counted | Pinnacle | Fair | Your book | DraftKings first seen by us → now |", "|---|---|---|---|---|---|"]
    for g in sheet["games"]:
        sp = g["markets"][0]
        adj = _fmt(-sp['adjustment_points']) if sp['adjustment_points'] else '0'
        dk = f"{_fmt(sp.get('draftkings_open'))} → {_fmt(sp.get('draftkings_line'))}"
        if use_model:
            out.append(f"| {g['game']} | {_fmt(sp['rating_line'])} | {_fmt(sp['public_systems_line'])} | {adj} | "
                       f"{_fmt(sp['model_line'])} | {_fmt(sp.get('pinnacle_line'))} | {_fmt(sp['fair_line'])} | {_fmt(sp.get('book_line'))} | {dk} |")
        else:
            out.append(f"| {g['game']} | {adj} | {_fmt(sp.get('pinnacle_line'))} | {_fmt(sp['fair_line'])} | {_fmt(sp.get('book_line'))} | {dk} |")
    winds = [(g["game"], m["wind_model"]) for g in sheet["games"] for m in g["markets"] if m.get("wind_model")]
    if winds:
        out += ["", "## Wind model (open-air stadiums)", "",
                "Forecast wind over the first three hours, and what the tested wind model takes off the total. "
                "It is used only within 60 hours of kickoff and at 1 point or more; it can make a Conditional, not a Bet.", "",
                "| Game | Wind (mph) | Temp (F) | Rain (mm) | Total change | Used |", "|---|---|---|---|---|---|"]
        for game, w in winds:
            out.append(f"| {game} | {w['wind_mph']:g} | {_fmt(w['temp_f'], False)} | {_fmt(w['precip_mm'], False)} | {w['points']:+.1f} | {'yes' if w['used'] else 'no'} |")
    if use_model and sheet.get("sport") in ("NFL", "College") and not sheet.get("settings", {}).get("public_systems_available", True):
        out += ["", "Public systems: n/a. The weekly ratings file has not been published for this week yet, so that column is blank."]
    out += ["", "Totals are picked only from a tested model (wind) or a specific, sourced reason "
            "(a quarterback change, a star ruled out) entered as an adjustment.", ""]
    if sheet.get("settings", {}).get("history_note"):
        out += [sheet["settings"]["history_note"], ""]
    entered = [(g["game"], a) for g in sheet["games"] for a in g.get("adjustments", [])]
    out += ["## Adjustments entered, and how much still counts", "",
            "An injury or news adjustment counts only for the part Pinnacle's line has not already moved for. "
            "Where Pinnacle has moved, the news is priced and nothing is added on top.", ""]
    if entered:
        for game, a in entered:
            who = f"{a['team']} " if a["market"] == "spread" else "total "
            out.append(f"- {game}: {who}{float(a['points']):+g} entered, {float(a.get('applied_points', 0)):+g} counted. {a.get('status', '')}. "
                       f"{a['reason']} ([source]({a['source']}), added {a['added']})")
    else:
        out.append("None entered by hand.")
    notes = [f"- {g['game']}: {n}" for g in sheet["games"] for n in g["notes"]]
    if notes:
        out += ["", "## Notes", ""] + notes
    if sheet.get("problems"):
        out += ["", "## Problems on this build", ""] + [f"- {p}" for p in sheet["problems"]]
    out.append("")
    return "\n".join(out), rows
