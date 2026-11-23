from engine.alerts import telegram


def test_only_bets_and_system_get_through(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram, "_call", lambda token, method, params=None: calls.append(params) or {"ok": True})
    monkeypatch.setattr(telegram, "allowed_kinds", lambda: {"bet", "system"})
    env = {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"}
    assert telegram.send(env, "NFL · NO BETS", kind="info") is False
    assert telegram.send(env, "NBA NEWS") is False          # default kind is info
    assert calls == []
    assert telegram.send(env, "NFL · BET NOW\nx", kind="bet") is True
    assert telegram.send(env, "FAILED", kind="system") is True
    assert len(calls) == 2


def test_config_default_is_bets_system_and_stale_number():
    assert telegram.allowed_kinds() == {"bet", "system", "stale"}
