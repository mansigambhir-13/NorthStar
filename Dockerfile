FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY northstar/ northstar/

RUN pip install --no-cache-dir .

ENTRYPOINT ["northstar"]
