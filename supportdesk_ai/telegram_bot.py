from __future__ import annotations

import asyncio
from typing import Optional

from supportdesk_ai.config import load_bot_config
from supportdesk_ai.formatting import format_ticket_list, format_ticket_snapshot
from supportdesk_ai.models import CreateTicketInput
from supportdesk_ai.repository import SQLiteTicketRepository
from supportdesk_ai.service import SupportService


def main() -> int:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv()

    asyncio.run(_run_bot())
    return 0


async def _run_bot() -> None:
    try:
        from aiogram import Bot, Dispatcher, F
        from aiogram.filters import Command, CommandObject
        from aiogram.types import Message
    except ImportError as exc:
        raise RuntimeError(
            'Telegram dependencies are missing. Install with: python3 -m pip install -e ".[telegram]"'
        ) from exc

    config = load_bot_config()
    service = SupportService(SQLiteTicketRepository(config.db_path))
    bot = Bot(config.telegram_bot_token)
    dispatcher = Dispatcher()

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in config.admin_ids)

    @dispatcher.message(Command("start"))
    async def start(message: Message) -> None:
        await message.answer(
            "Send a support request as a normal message. "
            "Admins can use /tickets, /ticket, /assign, /reply and /resolve."
        )

    @dispatcher.message(Command("mytickets"))
    async def my_tickets(message: Message) -> None:
        if not message.from_user:
            return
        tickets = service.list_user_tickets(message.from_user.id)
        await message.answer(format_ticket_list(tickets))

    @dispatcher.message(Command("whoami"))
    async def whoami(message: Message) -> None:
        if not message.from_user:
            return
        await message.answer(
            f"Your Telegram user id: {message.from_user.id}\n"
            f"Username: @{message.from_user.username or 'none'}"
        )

    @dispatcher.message(Command("tickets"))
    async def tickets(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Admin command.")
            return
        await message.answer(format_ticket_list(service.list_open_tickets()))

    @dispatcher.message(Command("ticket"))
    async def ticket_details(message: Message, command: CommandObject) -> None:
        if not is_admin(message):
            await message.answer("Admin command.")
            return
        ticket_id = _parse_ticket_id(command.args)
        if ticket_id is None:
            await message.answer("Usage: /ticket <id>")
            return
        snapshot = service.get_ticket_snapshot(ticket_id)
        if snapshot is None:
            await message.answer("Ticket not found.")
            return
        await message.answer(format_ticket_snapshot(snapshot))

    @dispatcher.message(Command("assign"))
    async def assign(message: Message, command: CommandObject) -> None:
        if not is_admin(message) or not message.from_user:
            await message.answer("Admin command.")
            return
        ticket_id = _parse_ticket_id(command.args)
        if ticket_id is None:
            await message.answer("Usage: /assign <id>")
            return
        ticket = service.assign_ticket(ticket_id, message.from_user.id)
        await message.answer("Ticket assigned." if ticket else "Ticket not found.")

    @dispatcher.message(Command("reply"))
    async def reply(message: Message, command: CommandObject) -> None:
        if not is_admin(message) or not message.from_user:
            await message.answer("Admin command.")
            return
        args = (command.args or "").strip()
        ticket_id_text, _, body = args.partition(" ")
        ticket_id = _parse_ticket_id(ticket_id_text)
        if ticket_id is None or not body.strip():
            await message.answer("Usage: /reply <id> <message>")
            return

        snapshot = service.get_ticket_snapshot(ticket_id)
        ticket = service.reply_to_ticket(ticket_id, message.from_user.id, body)
        if ticket is None or snapshot is None:
            await message.answer("Ticket not found.")
            return
        await bot.send_message(snapshot.ticket.user_id, f"Support reply for ticket #{ticket_id}:\n{body}")
        await message.answer("Reply sent.")

    @dispatcher.message(Command("resolve"))
    async def resolve(message: Message, command: CommandObject) -> None:
        if not is_admin(message) or not message.from_user:
            await message.answer("Admin command.")
            return
        ticket_id = _parse_ticket_id(command.args)
        if ticket_id is None:
            await message.answer("Usage: /resolve <id>")
            return
        snapshot = service.get_ticket_snapshot(ticket_id)
        ticket = service.resolve_ticket(ticket_id, message.from_user.id)
        if ticket is None or snapshot is None:
            await message.answer("Ticket not found.")
            return
        await bot.send_message(snapshot.ticket.user_id, f"Ticket #{ticket_id} has been resolved.")
        await message.answer("Ticket resolved.")

    @dispatcher.message(F.text)
    async def intake(message: Message) -> None:
        if not message.from_user or not message.text:
            return
        ticket = service.create_ticket(
            CreateTicketInput(
                user_id=message.from_user.id,
                username=message.from_user.username or str(message.from_user.id),
                message=message.text,
            )
        )
        await message.answer(
            f"Ticket #{ticket.id} created.\n"
            f"Priority: {ticket.priority.value}\n"
            f"Category: {ticket.category}\n\n"
            f"{ticket.suggested_reply}"
        )
        for admin_id in config.admin_ids:
            await bot.send_message(admin_id, f"New ticket:\n{format_ticket_list([ticket])}")

    await dispatcher.start_polling(bot)


def _parse_ticket_id(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    if not value.isdigit():
        return None
    return int(value)


if __name__ == "__main__":
    raise SystemExit(main())
