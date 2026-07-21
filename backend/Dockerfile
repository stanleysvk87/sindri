FROM python:3.12-slim

WORKDIR /app

# openssh-client: needed for real remote execution (app/remote_exec.py)
# over SSH to registered managed machines. sshpass: only for machines
# registered with auth_type=password (no mounted key) -- password is
# always passed via the SSHPASS env var, never argv.
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client sshpass \
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

# No curl/wget in this slim image -- python is already here, so use it
# instead of adding a package just for the healthcheck. 127.0.0.1, not
# localhost: uvicorn only binds IPv4 (--host 0.0.0.0), and the frontend's
# equivalent wget-based check proved "localhost" resolving to ::1 first is
# enough to break clients that don't retry the next address -- pinning to
# 127.0.0.1 here avoids relying on urllib's happier retry behavior.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
