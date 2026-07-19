FROM python:3.12-slim

WORKDIR /app

# openssh-client: needed for real remote execution (app/remote_exec.py)
# over SSH to registered managed machines.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV SINDRI_DB_PATH=/data/scripts.db
VOLUME ["/data"]

# Non-root, UID 1000: matches the typical single-user homelab host account
# (so bind-mounted ~/.claude/~/.codex need no chown gymnastics) and some
# CLI auth flows behave differently/refuse outright when run as root. Same
# reasoning as Muninn's ai_engine container -- see docs/AI_FEATURES.md.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin sindri \
    && mkdir -p /data && chown -R sindri:sindri /data /app
USER sindri
ENV HOME=/home/sindri

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
