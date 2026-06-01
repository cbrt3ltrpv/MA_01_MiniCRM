# MA_01_MiniCRM

Multi-agent Telegram support desk bot with AI triage, SQLite storage, admin commands, Docker, and tests.

## What It Does

MA_01_MiniCRM turns a Telegram bot into a small support desk. A user sends a normal message, the system creates a ticket, runs multi-agent triage, suggests a first reply, and lets an admin manage the ticket from Telegram commands.

## Multi-Agent Flow

The project uses a deterministic multi-agent pipeline, so it works without paid AI APIs and is easy to test.

- `CategoryAgent` detects the support area: billing, login, bug, delivery, feature request, or general.
- `PriorityAgent` decides ticket urgency: low, medium, high, or urgent.
- `SentimentAgent` estimates customer tone: positive, neutral, or negative.
- `TaggingAgent` creates searchable tags from the message.
- `ReplyDraftAgent` drafts the first support response.
- `SupervisorAgent` reviews the previous decisions and produces overall confidence.

The final ticket timeline stores the agent trace, so `/ticket <id>` shows how the system reached its decision.

## Features

- Telegram support intake for customer messages
- Admin commands for listing, viewing, assigning, replying, and resolving tickets
- Multi-agent triage with decision trace
- SQLite persistence
- CLI demo without Telegram credentials
- Docker and Docker Compose setup
- GitHub Actions CI
- Unit tests for triage and ticket lifecycle

## Architecture

```text
Telegram User/Admin
        |
        v
supportdesk_ai.telegram_bot
        |
        v
SupportService
        |
        +--> TriageEngine
        |       +--> CategoryAgent
        |       +--> PriorityAgent
        |       +--> SentimentAgent
        |       +--> TaggingAgent
        |       +--> ReplyDraftAgent
        |       +--> SupervisorAgent
        |
        +--> SQLiteTicketRepository
                |
                v
             SQLite DB
```

## Quick Start Without Telegram

```bash
python3 -m supportdesk_ai.demo
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Run Telegram Bot Locally

Create a local `.env` file. Do not commit it.

```env
TELEGRAM_BOT_TOKEN=your_bot_token
SUPPORT_ADMIN_IDS=123456789
SUPPORT_DB_PATH=supportdesk.db
```

Install dependencies:

```bash
python3 -m pip install -e ".[telegram]"
```

Check the token:

```bash
python3 -m supportdesk_ai.check_bot
```

Run the bot:

```bash
python3 -m supportdesk_ai.telegram_bot
```

## Docker

```bash
docker compose up --build
```

## Telegram Commands

User commands:

```text
/start
/mytickets
/whoami
```

Admin commands:

```text
/tickets
/ticket 1
/assign 1
/reply 1 We are checking your issue.
/resolve 1
```

## Example Ticket Trace

```text
Multi-agent triage: category=login, priority=medium, sentiment=negative, confidence=0.72.
Trace: category-agent -> login; priority-agent -> medium; sentiment-agent -> negative; tagging-agent -> login, medium, password; reply-draft-agent -> drafted_reply; supervisor-agent -> overall_confidence=0.72
```

## Tech Stack

- Python 3.9+
- aiogram 3
- SQLite
- Docker
- GitHub Actions
- unittest

## Security Notes

Do not commit `.env`, Telegram tokens, local databases, or real user data. Use `.env.example` for configuration examples.
