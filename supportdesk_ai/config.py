from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class BotConfig:
    telegram_bot_token: str
    admin_ids: Set[int]
    db_path: str


def load_bot_config() -> BotConfig:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    return BotConfig(
        telegram_bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("SUPPORT_ADMIN_IDS", "")),
        db_path=os.getenv("SUPPORT_DB_PATH", "supportdesk.db"),
    )


def _parse_admin_ids(raw_value: str) -> Set[int]:
    admin_ids: Set[int] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if item:
            admin_ids.add(int(item))
    return admin_ids
