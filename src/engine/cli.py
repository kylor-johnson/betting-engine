"""Command line entry point: `engine <command>`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.nosync"


def cmd_audit(args) -> int:
    from engine.bets import audit, store
    from engine.bets.history import load_wagers, weekly_figures
    from engine.reports import audit_report

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    pull = Path(args.history) if args.history else max((DATA / "raw").glob("wagerhouse_graded_wagers_pull_*.json"), default=None)
    if pull is None or not pull.exists():
        print("No history pull found in data.nosync/raw/. Nothing audited.", file=sys.stderr)
        return 2
    wagers = load_wagers(pull)
    priced = audit.price_all(wagers, cfg["margin_sd"], DATA / "raw" / "espn")
    store.save_audit(DATA / "engine.duckdb", wagers, priced)
    text = audit_report.build(wagers, priced, weekly_figures(pull), cfg, cfg["timezone_display"])
    out = ROOT / "docs" / "research" / "01-bet-audit.md"
    out.write_text(text)
    print(f"Audited {len(wagers)} wagers from {pull.name}. Report: {out.relative_to(ROOT)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="price past bets against closing lines and write the report")
    a.add_argument("--history", help="path to a Wagerhouse pull file (default: newest in data.nosync/raw)")
    a.set_defaults(func=cmd_audit)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
