from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Sequence

from supportdesk_ai.formatting import format_ticket_list, format_ticket_snapshot
from supportdesk_ai.models import CreateTicketInput
from supportdesk_ai.repository import SQLiteTicketRepository
from supportdesk_ai.service import SupportService


DEMO_MESSAGES = [
    "Urgent: payment failed but my card was charged twice. Order 883921.",
    "I cannot login after enabling 2FA, please help.",
    "Feature request: can you add Slack integration for ticket alerts?",
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    del argv
    db_path = Path(tempfile.gettempdir()) / "supportdesk_ai_demo.sqlite3"
    if db_path.exists():
        db_path.unlink()

    service = SupportService(SQLiteTicketRepository(str(db_path)))
    for index, message in enumerate(DEMO_MESSAGES, start=1):
        ticket = service.create_ticket(
            CreateTicketInput(
                user_id=1000 + index,
                username=f"demo_user_{index}",
                message=message,
            )
        )
        print(f"Created ticket #{ticket.id}: {ticket.priority.value} / {ticket.category}")

    print("\nOpen tickets")
    print(format_ticket_list(service.list_open_tickets()))

    snapshot = service.get_ticket_snapshot(1)
    if snapshot:
        print("\nTicket #1")
        print(format_ticket_snapshot(snapshot))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
