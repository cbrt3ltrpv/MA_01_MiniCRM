import tempfile
import unittest
from pathlib import Path

from supportdesk_ai.models import CreateTicketInput, Priority, TicketStatus
from supportdesk_ai.repository import SQLiteTicketRepository
from supportdesk_ai.service import SupportService
from supportdesk_ai.triage import TriageEngine


class TriageEngineTest(unittest.TestCase):
    def test_classifies_urgent_billing_request(self):
        result = TriageEngine().analyze(
            "Urgent refund needed, my card was charged twice for order 12345."
        )

        self.assertEqual(result.category, "billing")
        self.assertEqual(result.priority, Priority.URGENT)
        self.assertIn("contains_id", result.tags)
        self.assertGreaterEqual(result.confidence, 0.7)
        self.assertEqual(
            [decision.agent_name for decision in result.agent_trace],
            [
                "category-agent",
                "priority-agent",
                "sentiment-agent",
                "tagging-agent",
                "reply-draft-agent",
                "supervisor-agent",
            ],
        )


class SupportServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "tickets.sqlite3"
        self.service = SupportService(SQLiteTicketRepository(str(self.db_path)))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_creates_ticket_with_triage_and_events(self):
        ticket = self.service.create_ticket(
            CreateTicketInput(
                user_id=42,
                username="alice",
                message="I cannot login after password reset.",
            )
        )

        snapshot = self.service.get_ticket_snapshot(ticket.id)

        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertEqual(ticket.category, "login")
        self.assertEqual(ticket.priority, Priority.MEDIUM)
        self.assertIsNotNone(snapshot)
        self.assertEqual(len(snapshot.events), 2)
        self.assertIn("Multi-agent triage", snapshot.events[1].body)
        self.assertIn("category-agent -> login", snapshot.events[1].body)

    def test_admin_reply_marks_ticket_waiting(self):
        ticket = self.service.create_ticket(
            CreateTicketInput(user_id=42, username="alice", message="Payment failed.")
        )

        updated = self.service.reply_to_ticket(ticket.id, admin_id=7, message="We are checking it.")

        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, TicketStatus.WAITING)
        snapshot = self.service.get_ticket_snapshot(ticket.id)
        self.assertTrue(any(event.actor == "admin:7" for event in snapshot.events))

    def test_cannot_reply_to_resolved_ticket(self):
        ticket = self.service.create_ticket(
            CreateTicketInput(user_id=42, username="alice", message="Payment failed.")
        )
        self.service.resolve_ticket(ticket.id, admin_id=7)

        with self.assertRaises(ValueError):
            self.service.reply_to_ticket(ticket.id, admin_id=7, message="Late reply")

    def test_user_cannot_close_another_users_ticket(self):
        ticket = self.service.create_ticket(
            CreateTicketInput(user_id=42, username="alice", message="Bug report")
        )

        closed = self.service.close_ticket(ticket.id, user_id=99)

        self.assertIsNone(closed)
        snapshot = self.service.get_ticket_snapshot(ticket.id)
        self.assertEqual(snapshot.ticket.status, TicketStatus.OPEN)


if __name__ == "__main__":
    unittest.main()
