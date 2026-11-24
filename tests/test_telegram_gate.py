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


def test_config_sends_only_bets_system_and_recap():
    # decision 0027: Telegram carries staked picks, the recap and system lines; stale price alerts are held back
    assert telegram.allowed_kinds() == {"bet", "system", "recap"}
