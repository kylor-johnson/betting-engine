"""The live model-picks page (Kylor, Nov 23): only picks the model sent to Telegram, never his own bets or paper picks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from test_review18 import _pb_con

NOW = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)


def _pick(con, key, dollars, units, nominal):
    from engine.picks import playbook as pb
    pb._insert_pick(con, [key, (NOW - timedelta(hours=2)).replace(tzinfo=None), "NFL", "e1", "A at B", "side", "home", f"pick {key}", -3.0, -110,
                          "B", 0.05, -4.0, -3.0, -5.0, units, dollars, "B -3.5", (NOW + timedelta(days=1)).replace(tzinfo=None), "w", "why", "v",
                          nominal, 0.01])


def test_only_staked_model_picks_reach_the_page(monkeypatch):
    from engine.bets import public_page, tracker
    con = _pb_con()
    _pick(con, "staked", 25.0, 0.5, 0.5)
    _pick(con, "paper", 0.0, 0.0, 0.5)
    monkeypatch.setattr(tracker, "wagers", lambda since: (_ for _ in ()).throw(AssertionError("must not read Kylor's own bets")))
    d = public_page.data(con, {}, NOW)
    assert [p["pick"] for p in d["picks"]] == ["pick staked"]
    assert d["picks"][0]["stake"] == 25.0 and d["picks"][0]["status"] == "upcoming"
    assert not any(k in d["picks"][0] for k in ("wagers", "bet", "you_net", "you_risk"))
    assert "</script>" not in public_page.html(d).split("const D=")[1].split(";\n")[0]


def test_publish_skips_unchanged_picks_and_reports_a_login_problem(tmp_path, monkeypatch):
    from engine import config
    from engine.bets import public_page
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "load_env", lambda: {})
    con = _pb_con()
    _pick(con, "staked", 25.0, 0.5, 0.5)
    calls = []
    ok = lambda cmd, **kw: (calls.append(cmd), SimpleNamespace(returncode=0, stdout="https://x.vercel.app\n", stderr=""))[1]
    assert public_page.publish(con, {}, runner=ok).startswith("Live picks page published")
    assert public_page.publish(con, {}, runner=ok) == ""                      # same picks: no second deploy
    assert len(calls) == 1 and "--prod" in calls[0]
    bad = lambda cmd, **kw: SimpleNamespace(returncode=1, stdout="", stderr="Error: No existing credentials found. Please run `vercel login`")
    assert "credentials" in public_page.publish(con, {}, force=True, runner=bad)
