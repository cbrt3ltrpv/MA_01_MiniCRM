from __future__ import annotations

from typing import Iterable, List, Optional

from supportdesk_ai.agents import (
    AgentContext,
    CategoryAgent,
    PriorityAgent,
    ReplyDraftAgent,
    SentimentAgent,
    SupervisorAgent,
    SupportAgent,
    TaggingAgent,
    normalize_message,
)
from supportdesk_ai.models import TriageResult


class TriageEngine:
    """Coordinates specialist agents and returns one support triage decision."""

    def __init__(self, agents: Optional[Iterable[SupportAgent]] = None) -> None:
        self.agents: List[SupportAgent] = list(agents) if agents is not None else [
            CategoryAgent(),
            PriorityAgent(),
            SentimentAgent(),
            TaggingAgent(),
            ReplyDraftAgent(),
            SupervisorAgent(),
        ]

    def analyze(self, message: str) -> TriageResult:
        context = AgentContext(message=message, normalized=normalize_message(message))
        for agent in self.agents:
            agent.run(context)

        return TriageResult(
            category=context.category,
            priority=context.priority,
            sentiment=context.sentiment,
            tags=context.tags,
            suggested_reply=context.suggested_reply,
            confidence=context.decisions[-1].confidence if context.decisions else 0.0,
            agent_trace=context.decisions,
        )
