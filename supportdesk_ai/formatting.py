from __future__ import annotations

from typing import Iterable, List

from supportdesk_ai.models import Ticket, TicketSnapshot


def format_ticket_summary(ticket: Ticket) -> str:
    assignee = ticket.assigned_admin_id if ticket.assigned_admin_id is not None else "unassigned"
    return (
        f"#{ticket.id} [{ticket.status.value}] {ticket.priority.value.upper()} "
        f"{ticket.category} - {ticket.subject} (user: @{ticket.username}, assignee: {assignee})"
    )


def format_ticket_list(tickets: Iterable[Ticket]) -> str:
    items = list(tickets)
    if not items:
        return "No tickets found."
    return "\n".join(format_ticket_summary(ticket) for ticket in items)


def format_ticket_snapshot(snapshot: TicketSnapshot) -> str:
    ticket = snapshot.ticket
    lines: List[str] = [
        format_ticket_summary(ticket),
        "",
        f"Message: {ticket.message}",
        f"Tags: {', '.join(ticket.tags)}",
        f"Suggested reply: {ticket.suggested_reply}",
        "",
        "Timeline:",
    ]
    for event in snapshot.events:
        lines.append(f"- {event.created_at.isoformat()} {event.actor}: {event.body}")
    return "\n".join(lines)
