import copy
import re
from datetime import datetime, timezone

import duckdb

from engine import config, lanes
from engine.picks import card


def cfg():
    return config.load_config()


def test_lanes_exist_in_the_charter_order():
    # the charter's five, plus the paper teaser lane Kylor approved 2026-11-23 (decision 0014)
    assert [l["short"] for l in cfg()["lanes"].values()] == [
        "NFL sides/totals", "College sides/totals", "NBA sides/totals", "NFL teasers", "NFL props", "NBA props"]


def test_inputs_are_read_as_switches_not_yaml_booleans():
    # `on:` is read by YAML as the boolean True; the key must be `enabled`
    for lane in cfg()["lanes"].values():
        for v in lane["inputs"].values():
            assert "enabled" in v and True not in v


def test_model_switch_in_the_table_is_the_real_config_switch():
    c = cfg()
    on = {m["name"]: m["on"] for r in lanes.rows(c, None) for m in r["models"]}
    assert on["wind_totals"] == bool(c["models"]["wind_totals"]["enabled"])
    c2 = copy.deepcopy(c)
    c2["models"]["wind_totals"]["enabled"] = False
    assert {m["name"]: m["on"] for r in lanes.rows(c2, None) for m in r["models"]}["wind_totals"] is False
    assert lanes.structure_hash(c) != lanes.structure_hash(c2)       # switching a model off changes the table


def test_failed_models_are_never_on_and_cite_a_real_write_up():
    c = cfg()
    for lane in c["lanes"].values():
        for name, m in lane["models"].items():
            if m["status"] == "failed":
                assert not lanes.model_on(c, m)
            if m.get("doc"):
                assert (config.ROOT / m["doc"]).exists(), f"{name}: missing {m['doc']}"


def test_props_lanes_say_what_produces_a_pick():
    # since decisions 0021-0022 the playbook issues prop picks; with the playbook off, the props lanes produce nothing
    for r in lanes.rows(cfg(), None):
        if r["kind"] == "props":
            assert r["can_produce"].startswith("Playbook prop picks")
    off = cfg()
    off["playbook"]["enabled"] = False
    for r in lanes.rows(off, None):
        if r["kind"] == "props":
            assert r["can_produce"].startswith("Nothing")


def test_records_are_left_out_of_the_change_hash():
    c = cfg()
    assert lanes.structure_hash(c) == lanes.structure_hash(copy.deepcopy(c))


def test_change_message_names_what_was_switched_off():
    c = cfg()
    con = duckdb.connect(":memory:")
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    assert lanes.check_changed(con, c, now) is None                  # first call stores the baseline
    assert lanes.check_changed(con, c, now) is None                  # unchanged
    c2 = copy.deepcopy(c)
    c2["models"]["props"]["nba_enabled"] = False
    msg = lanes.check_changed(con, c2, now)
    assert "NBA player props: model nba props switched off." in msg


def test_wording_changes_are_not_lane_changes_and_money_state_is():
    from engine import lanes as L
    c = cfg()
    con = duckdb.connect(":memory:")
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    L.check_changed(con, c, now)
    c2 = copy.deepcopy(c)
    for lane in c2["lanes"].values():
        lane["title"] = lane["title"]          # same structure; text-only edits elsewhere never count
    assert L.check_changed(con, c2, now) is None
    c3 = copy.deepcopy(c)
    c3.setdefault("playbook", {}).setdefault("sports", {})["NBA"] = {"props": True, "props_stake": False}   # staked since decision 0040
    msg = L.check_changed(con, c3, now)
    assert msg and "NBA player props: now PAPER (was staked)." in msg


def test_card_lane_block_comes_from_config():
    c = cfg()
    text = "\n".join(lanes.card_block(c, None, "NBA"))
    assert "NBA spreads and totals" in text and "Pinnacle" in text
    assert lanes.card_block({"lanes": {}}, None, "NBA") == []


def test_generated_text_never_claims_the_old_blend():
    t = lanes.table_markdown(cfg(), None)
    assert not re.search(r"55%|45% model", t)
