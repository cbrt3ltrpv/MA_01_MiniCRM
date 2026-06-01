from __future__ import annotations

from typing import List, Optional

from supportdesk_ai.models import (
    CreateTicketInput,
    Ticket,
    TicketSnapshot,
    TicketStatus,
)
from supportdesk_ai.repository import SQLiteTicketRepository, TicketRepository
from supportdesk_ai.triage import TriageEngine


class SupportService:
    def __init__(
        self,
        repository: Optional[TicketRepository] = None,
        triage_engine: Optional[TriageEngine] = None,
    ) -> None:
        self.repository = repository or SQLiteTicketRepository()
        self.triage_engine = triage_engine or TriageEngine()

    def create_ticket(self, data: CreateTicketInput) -> Ticket:
        message = data.message.strip()
        if not message:
            raise ValueError("message cannot be empty")

        triage = self.triage_engine.analyze(message)
        subject = data.subject or self._build_subject(message, triage.category)
        ticket = self.repository.create_ticket(
            user_id=data.user_id,
            username=data.username or "unknown",
            subject=subject,
            message=message,
            status=TicketStatus.OPEN,
            priority=triage.priority,
            category=triage.category,
            sentiment=triage.sentiment,
            tags=triage.tags,
            suggested_reply=triage.suggested_reply,
        )
        self.repository.add_event(
            ticket.id,
            "system",
            _format_agent_trace(triage),
        )
        return ticket

    def list_open_tickets(self, limit: int = 20) -> List[Ticket]:
        return self.repository.list_tickets(
            statuses=[TicketStatus.OPEN, TicketStatus.WAITING],
            limit=limit,
        )

    def list_user_tickets(self, user_id: int, limit: int = 10) -> List[Ticket]:
        return self.repository.list_tickets(user_id=user_id, limit=limit)

    def get_ticket_snapshot(self, ticket_id: int) -> Optional[TicketSnapshot]:
        ticket = self.repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        return TicketSnapshot(ticket=ticket, events=self.repository.list_events(ticket_id))

    def assign_ticket(self, ticket_id: int, admin_id: int) -> Optional[Ticket]:
        ticket = self.repository.assign(ticket_id, admin_id)
        if ticket:
            self.repository.add_event(ticket_id, "system", f"Assigned to admin {admin_id}")
        return ticket

    def reply_to_ticket(self, ticket_id: int, admin_id: int, message: str) -> Optional[Ticket]:
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("reply cannot be empty")
        ticket = self.repository.get_ticket(ticket_id)
        if ticket is None:
            return None
        self.repository.add_event(ticket_id, f"admin:{admin_id}", clean_message)
        return self.repository.update_status(ticket_id, TicketStatus.WAITING)

    def resolve_ticket(self, ticket_id: int, admin_id: int) -> Optional[Ticket]:
        ticket = self.repository.update_status(ticket_id, TicketStatus.RESOLVED)
        if ticket:
            self.repository.add_event(ticket_id, f"admin:{admin_id}", "Resolved ticket")
        return ticket

    def close_ticket(self, ticket_id: int, user_id: int) -> Optional[Ticket]:
        ticket = self.repository.get_ticket(ticket_id)
        if ticket is None or ticket.user_id != user_id:
            return None
        self.repository.add_event(ticket_id, "user", "Closed ticket")
        return self.repository.update_status(ticket_id, TicketStatus.CLOSED)

    def _build_subject(self, message: str, category: str) -> str:
        first_line = message.splitlines()[0]
        trimmed = first_line[:58].strip()
        suffix = "..." if len(first_line) > 58 else ""
        return f"{category}: {trimmed}{suffix}"


def _format_agent_trace(triage) -> str:
    decisions = "; ".join(
        f"{item.agent_name} -> {item.decision}"
        for item in triage.agent_trace
    )
    return (
        f"Multi-agent triage: category={triage.category}, priority={triage.priority.value}, "
        f"sentiment={triage.sentiment}, confidence={triage.confidence:.2f}. "
        f"Trace: {decisions}"
    )
