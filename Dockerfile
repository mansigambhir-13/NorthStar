FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY northstar/ northstar/

RUN pip install --no-cache-dir ".[web]"

EXPOSE 8765

ENTRYPOINT ["northstar"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8765"]
