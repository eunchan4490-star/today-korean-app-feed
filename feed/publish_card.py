"""Update the curated feed from a GitHub-authorized manual dispatch."""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

FEED = Path("published.json")
FIELDS = {"id": 64, "title": 100, "description": 1000, "url": 500}


def validate(card):
    if not isinstance(card, dict) or set(card) != set(FIELDS):
        raise ValueError("Expected only id, title, description and url")
    for field, limit in FIELDS.items():
        value = card[field]
        if not isinstance(value, str) or not value.strip() or len(value.encode("utf-16-le")) // 2 > limit:
            raise ValueError(f"Invalid {field}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", card["id"]):
        raise ValueError("Invalid card ID")
    url = urlsplit(card["url"])
    if (url.scheme != "https" or not url.hostname or "." not in url.hostname
            or url.username is not None or url.password is not None or url.port not in (None, 443)
            or any(c.isspace() or c in r'\<>"' for c in card["url"])):
        raise ValueError("Use an HTTPS source URL")


def update(feed, action, data):
    if feed.get("version") != 1 or not isinstance(feed.get("cards"), list):
        raise ValueError("Unsupported feed")
    cards = {card["id"]: card for card in feed["cards"]}
    if action == "publish":
        card = json.loads(data)
        validate(card)
        cards[card["id"]] = card
    elif action == "remove":
        if data not in cards:
            raise ValueError("Card ID was not found")
        del cards[data]
    else:
        raise ValueError("Unsupported operation")
    if len(cards) > 200:
        raise ValueError("Public feed has reached 200 cards")
    # Validate the complete result before writing it.
    for card in cards.values():
        validate(card)
    return {"version": 1, "cards": list(cards.values())}


if __name__ == "__main__":
    result = update(json.loads(FEED.read_text(encoding="utf-8")),
                    os.environ["CARD_ACTION"], os.environ["CARD_DATA"].strip())
    FEED.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
