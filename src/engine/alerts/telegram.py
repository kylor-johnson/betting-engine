"""Send alerts to Telegram. The bot token is never printed or logged."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from engine.odds.espn import SourceError

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict | None = None) -> dict:
    data = urllib.parse.urlencode(params).encode() if params else None
    try:
        with urllib.request.urlopen(API.format(token=token, method=method), data=data, timeout=20) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        raise SourceError(f"Telegram {method} returned HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise SourceError(f"Telegram {method} failed: {type(e).__name__}") from None
    if not out.get("ok"):
        raise SourceError(f"Telegram {method} was refused: {out.get('description', 'no reason given')}")
    return out


def find_chat_id(token: str) -> str | None:
    """The chat that most recently messaged the bot, if any."""
    updates = _call(token, "getUpdates").get("result", [])
    chats = [u["message"]["chat"]["id"] for u in updates if "message" in u]
    return str(chats[-1]) if chats else None


def allowed_kinds() -> set[str]:
    """Which kinds of message may reach Telegram (config `telegram.send_kinds`). Default: bets and broken-engine alerts only."""
    try:
        from engine import config
        kinds = (config.load_config().get("telegram") or {}).get("send_kinds")
    except Exception:
        kinds = None
    return set(kinds) if kinds is not None else {"bet", "system"}


def send(env: dict, text: str, lane: str | None = None, kind: str = "info") -> bool:
    """Returns True if sent, False if held back because its `kind` is not in `telegram.send_kinds`.
    Kinds: "bet" (a Bet, Conditional, or the cancellation of one), "system" (the engine is broken or you asked for it by command),
    anything else is "info" and is held back by default: it stays in the cards, the board page and the alerts_sent table.
    `lane` is a key from config `lanes:`. If .env has TELEGRAM_THREAD_<LANE> (a forum topic id) the message goes to that topic;
    otherwise it goes to the main chat, and its first line already names the lane."""
    if kind not in allowed_kinds():
        return False
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token:
        raise SourceError("Telegram bot token is missing from .env")
    if not chat:
        raise SourceError("Telegram chat id is missing: message the bot once, then run `engine telegram-setup`")
    import html as _html
    head, _, rest = text[:3900].partition("\n")
    body = f"<b>{_html.escape(head)}</b>" + ("\n" + _html.escape(rest) if rest else "")
    params = {"chat_id": chat, "text": body, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    thread = env.get(f"TELEGRAM_THREAD_{lane.upper()}") if lane else None
    if thread:
        params["message_thread_id"] = thread
    _call(token, "sendMessage", params)
    return True
