from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Protocol, Tuple

from supportdesk_ai.models import AgentDecision, Priority


@dataclass
class AgentContext:
    message: str
    normalized: str
    category: str = "general"
    category_hits: List[str] = field(default_factory=list)
    priority: Priority = Priority.LOW
    sentiment: str = "neutral"
    tags: List[str] = field(default_factory=list)
    suggested_reply: str = ""
    decisions: List[AgentDecision] = field(default_factory=list)

    def record(self, agent_name: str, decision: str, reason: str, confidence: float) -> None:
        self.decisions.append(
            AgentDecision(
                agent_name=agent_name,
                decision=decision,
                reason=reason,
                confidence=confidence,
            )
        )


class SupportAgent(Protocol):
    name: str

    def run(self, context: AgentContext) -> None:
        ...


class CategoryAgent:
    name = "category-agent"

    CATEGORY_RULES: Dict[str, Tuple[str, ...]] = {
        "billing": ("refund", "payment", "invoice", "charge", "paid", "card", "billing"),
        "login": ("login", "password", "2fa", "sign in", "account", "access"),
        "bug": ("bug", "error", "crash", "broken", "does not work", "fail", "failed"),
        "delivery": ("delivery", "shipping", "order", "tracking", "courier"),
        "feature_request": ("feature", "request", "can you add", "integration"),
    }

    def run(self, context: AgentContext) -> None:
        best_category = "general"
        best_hits: List[str] = []
        for category, keywords in self.CATEGORY_RULES.items():
            hits = [keyword for keyword in keywords if keyword in context.normalized]
            if len(hits) > len(best_hits):
                best_category = category
                best_hits = hits

        context.category = best_category
        context.category_hits = best_hits
        reason = (
            f"matched keywords: {', '.join(best_hits)}"
            if best_hits
            else "no specific category keywords matched"
        )
        confidence = min(0.9, 0.45 + len(best_hits) * 0.12)
        context.record(self.name, best_category, reason, round(confidence, 2))


class PriorityAgent:
    name = "priority-agent"

    URGENT_TERMS = ("urgent", "asap", "critical", "production", "blocked", "can't work")
    HIGH_TERMS = ("angry", "refund", "chargeback", "lost", "broken", "failed", "down")

    def run(self, context: AgentContext) -> None:
        if any(term in context.normalized for term in self.URGENT_TERMS):
            priority = Priority.URGENT
            reason = "urgent language detected"
        elif any(term in context.normalized for term in self.HIGH_TERMS):
            priority = Priority.HIGH
            reason = "high-risk support keyword detected"
        elif context.category in {"billing", "login", "bug"}:
            priority = Priority.MEDIUM
            reason = f"{context.category} issues require support review"
        else:
            priority = Priority.LOW
            reason = "no urgent or high-risk signal detected"

        context.priority = priority
        confidence = 0.82 if priority in {Priority.URGENT, Priority.HIGH} else 0.68
        context.record(self.name, priority.value, reason, confidence)


class SentimentAgent:
    name = "sentiment-agent"

    NEGATIVE_TERMS = ("angry", "bad", "terrible", "broken", "failed", "can't", "cannot")
    POSITIVE_TERMS = ("thanks", "great", "please", "appreciate")

    def run(self, context: AgentContext) -> None:
        negative = sum(1 for term in self.NEGATIVE_TERMS if term in context.normalized)
        positive = sum(1 for term in self.POSITIVE_TERMS if term in context.normalized)
        if negative > positive:
            sentiment = "negative"
            reason = f"negative terms={negative}, positive terms={positive}"
        elif positive > negative:
            sentiment = "positive"
            reason = f"positive terms={positive}, negative terms={negative}"
        else:
            sentiment = "neutral"
            reason = "positive and negative signals are balanced"

        context.sentiment = sentiment
        context.record(self.name, sentiment, reason, 0.64 if sentiment == "neutral" else 0.74)


class TaggingAgent:
    name = "tagging-agent"

    def run(self, context: AgentContext) -> None:
        tags = {context.category, context.priority.value}
        tags.update(keyword.replace(" ", "_") for keyword in context.category_hits[:3])
        if re.search(r"\b\d{4,}\b", context.normalized):
            tags.add("contains_id")

        context.tags = sorted(tags)
        context.record(
            self.name,
            ", ".join(context.tags),
            "combined category, priority, matched keywords, and id detection",
            0.76,
        )


class ReplyDraftAgent:
    name = "reply-draft-agent"

    def run(self, context: AgentContext) -> None:
        if context.priority is Priority.URGENT:
            reply = (
                "Thanks for reporting this. I marked it urgent and our support team "
                "will review it as a priority."
            )
            reason = "urgent tickets need acknowledgement and priority expectation"
        else:
            reply = self._reply_for_category(context.category)
            reason = f"selected reply template for {context.category}"

        context.suggested_reply = reply
        context.record(self.name, "drafted_reply", reason, 0.7)

    def _reply_for_category(self, category: str) -> str:
        replies = {
            "billing": "Thanks. We will check the payment details and get back with the next step.",
            "login": "Thanks. Please keep access to your account email available while we investigate.",
            "bug": "Thanks for the report. We will reproduce the issue and follow up with a fix or workaround.",
            "delivery": "Thanks. We will check the order and delivery status.",
            "feature_request": "Thanks for the suggestion. We will review it with the product backlog.",
            "general": "Thanks. Our support team will review your request and reply soon.",
        }
        return replies.get(category, replies["general"])


class SupervisorAgent:
    name = "supervisor-agent"

    def run(self, context: AgentContext) -> None:
        confidence = self.score(context.decisions)
        reason = f"reviewed {len(context.decisions)} agent decisions"
        context.record(self.name, f"overall_confidence={confidence:.2f}", reason, confidence)

    def score(self, decisions: Iterable[AgentDecision]) -> float:
        scores = [decision.confidence for decision in decisions]
        if not scores:
            return 0.0
        return round(min(0.95, sum(scores) / len(scores) + min(0.08, len(scores) * 0.01)), 2)


def normalize_message(message: str) -> str:
    return " ".join(message.lower().strip().split())
