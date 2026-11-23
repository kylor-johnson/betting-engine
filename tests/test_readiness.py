from engine import readiness as r

RULES = r.DEFAULTS


def m(**kw):
    base = {"freeze_utc": 1, "weeks": 4.0, "graded": 12, "bets": 6, "clv_n": 8, "avg_clv": 0.3, "versions": 1,
            "missing_limit": 0, "ungraded_finished": 0, "profit_units": 0.0}
    base.update(kw)
    return base


def test_stage_one_needs_every_criterion():
    assert r.stage(m(), RULES)[0] == 1
    for bad in ({"weeks": 2.0}, {"graded": 9}, {"clv_n": 4}, {"avg_clv": -0.1}, {"missing_limit": 1}, {"ungraded_finished": 1}, {"avg_clv": None}):
        assert r.stage(m(**bad), RULES)[0] == 0, bad


def test_full_unit_needs_a_hundred_and_positive_value():
    assert r.stage(m(graded=100, clv_n=90, avg_clv=0.2), RULES)[0] == 2
    assert r.stage(m(graded=100, clv_n=90, avg_clv=0.0), RULES)[0] == 1


def test_negative_closing_line_value_pauses():
    assert r.stage(m(graded=30, clv_n=25, avg_clv=-0.6), RULES)[0] == -1
    assert r.stage(m(graded=30, clv_n=24, avg_clv=-0.6), RULES)[0] == 0      # not enough closing lines yet to pause on


def test_report_is_generated_from_numbers_and_names_the_stage():
    text = r.report({"unit": 25}, __import__("duckdb").connect())
    assert "Stage 0" in text and "$12.5" in text and "Never bet at any stage" in text
