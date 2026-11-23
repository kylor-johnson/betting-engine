import duckdb

from engine import version


def test_settings_hash_changes_only_with_settings_that_decide_picks():
    a = {"picks": {"min_value": 0.02}, "models": {}, "telegram": {"send_kinds": ["bet"]}}
    b = {"picks": {"min_value": 0.02}, "models": {}, "telegram": {"send_kinds": ["bet", "info"]}}
    c = {"picks": {"min_value": 0.03}, "models": {}}
    assert version.settings_hash(a) == version.settings_hash(b)      # messaging is not a rule
    assert version.settings_hash(a) != version.settings_hash(c)


def test_a_new_version_is_recorded_once(monkeypatch):
    monkeypatch.setattr(version, "commit_id", lambda: "abc1234")
    con = duckdb.connect()
    cfg = {"picks": {"min_value": 0.02}}
    s1 = version.stamp(cfg, con)
    assert version.stamp(cfg, con) == s1 and con.execute("select count(*) from rule_versions").fetchone()[0] == 1
    version.stamp({"picks": {"min_value": 0.05}}, con)
    assert con.execute("select count(*) from rule_versions").fetchone()[0] == 2
    assert "Rule versions seen: 2" in version.versions_text(con)


def test_uncommitted_code_is_not_recorded_as_a_clean_version(monkeypatch):
    monkeypatch.setattr(version, "commit_id", lambda: "abc1234+edited")
    con = duckdb.connect()
    assert version.stamp({"picks": {}}, con).startswith("abc1234+edited/")
    assert con.execute("select count(*) from rule_versions").fetchone()[0] == 0
