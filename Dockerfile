FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY supportdesk_ai ./supportdesk_ai

RUN pip install --no-cache-dir -e ".[telegram]"

CMD ["python", "-m", "supportdesk_ai.telegram_bot"]
