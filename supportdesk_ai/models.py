from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TicketStatus(str, Enum):
    OPEN = "open"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class AgentDecision:
    agent_name: str
    decision: str
    reason: str
    confidence: float


@dataclass(frozen=True)
class TriageResult:
    category: str
    priority: Priority
    sentiment: str
    tags: List[str]
    suggested_reply: str
    confidence: float
    agent_trace: List[AgentDecision] = field(default_factory=list)


@dataclass(frozen=True)
class Ticket:
    id: int
    user_id: int
    username: str
    subject: str
    message: str
    status: TicketStatus
    priority: Priority
    category: str
    sentiment: str
    tags: List[str]
    suggested_reply: str
    assigned_admin_id: Optional[int]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TicketEvent:
    id: int
    ticket_id: int
    actor: str
    body: str
    created_at: datetime


@dataclass(frozen=True)
class CreateTicketInput:
    user_id: int
    username: str
    message: str
    subject: Optional[str] = None


@dataclass
class TicketSnapshot:
    ticket: Ticket
    events: List[TicketEvent] = field(default_factory=list)
