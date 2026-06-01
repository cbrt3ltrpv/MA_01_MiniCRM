from __future__ import annotations

import asyncio

from supportdesk_ai.config import load_bot_config


def main() -> int:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv()

    asyncio.run(_check_bot())
    return 0


async def _check_bot() -> None:
    try:
        from aiogram import Bot
    except ImportError as exc:
        raise RuntimeError(
            'Telegram dependencies are missing. Install with: python3 -m pip install -e ".[telegram]"'
        ) from exc

    config = load_bot_config()
    bot = Bot(config.telegram_bot_token)
    try:
        me = await bot.get_me()
    finally:
        await bot.session.close()
    print(f"Connected to Telegram bot @{me.username} (id={me.id})")


if __name__ == "__main__":
    raise SystemExit(main())
