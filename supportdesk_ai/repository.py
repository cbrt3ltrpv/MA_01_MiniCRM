from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Protocol

from supportdesk_ai.models import Priority, Ticket, TicketEvent, TicketStatus


class TicketRepository(Protocol):
    def create_ticket(
        self,
        *,
        user_id: int,
        username: str,
        subject: str,
        message: str,
        status: TicketStatus,
        priority: Priority,
        category: str,
        sentiment: str,
        tags: List[str],
        suggested_reply: str,
    ) -> Ticket:
        ...

    def add_event(self, ticket_id: int, actor: str, body: str) -> TicketEvent:
        ...

    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        ...

    def list_tickets(
        self,
        *,
        statuses: Optional[Iterable[TicketStatus]] = None,
        user_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Ticket]:
        ...

    def list_events(self, ticket_id: int) -> List[TicketEvent]:
        ...

    def update_status(self, ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
        ...

    def assign(self, ticket_id: int, admin_id: int) -> Optional[Ticket]:
        ...


class SQLiteTicketRepository:
    def __init__(self, db_path: str = "supportdesk.db") -> None:
        self.db_path = db_path
        self._ensure_schema()

    def create_ticket(
        self,
        *,
        user_id: int,
        username: str,
        subject: str,
        message: str,
        status: TicketStatus,
        priority: Priority,
        category: str,
        sentiment: str,
        tags: List[str],
        suggested_reply: str,
    ) -> Ticket:
        now = _utcnow()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tickets (
                    user_id, username, subject, message, status, priority, category,
                    sentiment, tags, suggested_reply, assigned_admin_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    user_id,
                    username,
                    subject,
                    message,
                    status.value,
                    priority.value,
                    category,
                    sentiment,
                    json.dumps(tags),
                    suggested_reply,
                    _dump_datetime(now),
                    _dump_datetime(now),
                ),
            )
            ticket_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO ticket_events (ticket_id, actor, body, created_at) VALUES (?, ?, ?, ?)",
                (ticket_id, "user", message, _dump_datetime(now)),
            )
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise RuntimeError("created ticket could not be loaded")
        return ticket

    def add_event(self, ticket_id: int, actor: str, body: str) -> TicketEvent:
        now = _utcnow()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO ticket_events (ticket_id, actor, body, created_at) VALUES (?, ?, ?, ?)",
                (ticket_id, actor, body, _dump_datetime(now)),
            )
            event_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE tickets SET updated_at = ? WHERE id = ?",
                (_dump_datetime(now), ticket_id),
            )
        events = [event for event in self.list_events(ticket_id) if event.id == event_id]
        if not events:
            raise RuntimeError("created event could not be loaded")
        return events[0]

    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE id = ?",
                (ticket_id,),
            ).fetchone()
        return _row_to_ticket(row) if row else None

    def list_tickets(
        self,
        *,
        statuses: Optional[Iterable[TicketStatus]] = None,
        user_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Ticket]:
        clauses = []
        params: List[object] = []
        if statuses is not None:
            status_values = [status.value for status in statuses]
            placeholders = ", ".join("?" for _ in status_values)
            clauses.append(f"status IN ({placeholders})")
            params.extend(status_values)
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)

        query = "SELECT * FROM tickets"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_ticket(row) for row in rows]

    def list_events(self, ticket_id: int) -> List[TicketEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
                (ticket_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def update_status(self, ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
        now = _utcnow()
        with self._connect() as connection:
            connection.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, _dump_datetime(now), ticket_id),
            )
        return self.get_ticket(ticket_id)

    def assign(self, ticket_id: int, admin_id: int) -> Optional[Ticket]:
        now = _utcnow()
        with self._connect() as connection:
            connection.execute(
                "UPDATE tickets SET assigned_admin_id = ?, updated_at = ? WHERE id = ?",
                (admin_id, _dump_datetime(now), ticket_id),
            )
        return self.get_ticket(ticket_id)

    def _connect(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    suggested_reply TEXT NOT NULL,
                    assigned_admin_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    actor TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id)
                )
                """
            )


def _row_to_ticket(row: sqlite3.Row) -> Ticket:
    return Ticket(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        username=str(row["username"]),
        subject=str(row["subject"]),
        message=str(row["message"]),
        status=TicketStatus(str(row["status"])),
        priority=Priority(str(row["priority"])),
        category=str(row["category"]),
        sentiment=str(row["sentiment"]),
        tags=list(json.loads(str(row["tags"]))),
        suggested_reply=str(row["suggested_reply"]),
        assigned_admin_id=(
            int(row["assigned_admin_id"]) if row["assigned_admin_id"] is not None else None
        ),
        created_at=_load_datetime(str(row["created_at"])),
        updated_at=_load_datetime(str(row["updated_at"])),
    )


def _row_to_event(row: sqlite3.Row) -> TicketEvent:
    return TicketEvent(
        id=int(row["id"]),
        ticket_id=int(row["ticket_id"]),
        actor=str(row["actor"]),
        body=str(row["body"]),
        created_at=_load_datetime(str(row["created_at"])),
    )


def _utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def _dump_datetime(value: datetime) -> str:
    return value.isoformat()


def _load_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
