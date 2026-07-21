"""Built-in starter library: ~25-30 generic, distro-agnostic Linux admin
scripts, plus a ~90-entry cross-platform admin/dev cheatsheet (Docker,
systemd, git, network diagnostics, Windows/PowerShell, Sysinternals,
macOS, text processing, tmux, archiving, API tooling, SSH, Python,
find/xargs, databases, ffmpeg). Ships with the app so a fresh install is
useful immediately, not an empty shell -- and deliberately contains
nothing opi/victus specific (no hardcoded IPs, no /mnt/storage/data
paths), so the app itself stays portable to any host. Seeded idempotently
on startup (see seed_templates() in db.py) -- matched by name, never
overwrites a row a user has edited.

The cheatsheet entries are reference material (a command + why/when to
use it), not automation scripts like the rest of this file -- kept in
the same flat SEED_TEMPLATES list (host="", same as everything else
here) and distinguished purely by tags (e.g. "docker", "git",
"windows"...) rather than a separate host value, so they browse
alongside the automation scripts instead of in their own silo.
"""

SEED_TEMPLATES = [
    {
        "name": "disk-usage-top.sh",
        "tags": "disk,storage",
        "run_mode": "manual",
        "short_description": "Top 20 largest directories under a given path",
        "long_description": "du -sh on each immediate subdirectory, sorted largest first. Defaults to current directory if no argument given.",
        "content": """#!/bin/bash
set -euo pipefail
DIR="${1:-.}"
du -sh "$DIR"/*/ 2>/dev/null | sort -rh | head -n 20
""",
    },
    {
        "name": "find-large-files.sh",
        "tags": "disk,storage",
        "run_mode": "manual",
        "short_description": "Find files larger than N megabytes under a path",
        "long_description": "Usage: find-large-files.sh /path 500  -- lists files over 500MB, largest first.",
        "content": """#!/bin/bash
set -euo pipefail
DIR="${1:-.}"
MB="${2:-100}"
find "$DIR" -type f -size +"${MB}"M -printf '%s\\t%p\\n' 2>/dev/null | sort -rn | \
  awk '{printf "%.1f MB\\t%s\\n", $1/1024/1024, $2}'
""",
    },
    {
        "name": "docker-cleanup.sh",
        "tags": "docker",
        "run_mode": "manual",
        "short_description": "Prune stopped containers, dangling images and unused volumes",
        "long_description": "Dry-run by default (just shows what `docker system df` reports). Pass --yes to actually prune. Never touches running containers.",
        "content": """#!/bin/bash
set -euo pipefail
echo "Current docker disk usage:"
docker system df
if [[ "${1:-}" != "--yes" ]]; then
  echo
  echo "Dry run only. Re-run with --yes to actually prune:"
  echo "  docker container prune -f && docker image prune -f && docker volume prune -f"
  exit 0
fi
docker container prune -f
docker image prune -f
docker volume prune -f
""",
    },
    {
        "name": "docker-logs-tail.sh",
        "tags": "docker",
        "run_mode": "manual",
        "short_description": "Tail the last N log lines of every running container",
        "long_description": "Usage: docker-logs-tail.sh 50  -- prints the last 50 lines from each running container, labeled by name.",
        "content": """#!/bin/bash
set -euo pipefail
N="${1:-30}"
for name in $(docker ps --format '{{.Names}}'); do
  echo "===== $name ====="
  docker logs --tail "$N" "$name" 2>&1
  echo
done
""",
    },
    {
        "name": "failed-systemd-units.sh",
        "tags": "systemd,monitoring",
        "run_mode": "manual",
        "short_description": "List all failed systemd units with a short journal excerpt",
        "long_description": "Combines `systemctl --failed` with the last few journal lines per failed unit, so you see the failure reason without a second command.",
        "content": """#!/bin/bash
set -euo pipefail
systemctl --failed --no-legend --no-pager | while read -r unit rest; do
  [[ -z "$unit" ]] && continue
  echo "===== $unit ====="
  journalctl -u "$unit" -n 5 --no-pager
  echo
done
""",
    },
    {
        "name": "disk-space-alert.sh",
        "tags": "disk,monitoring",
        "run_mode": "cron",
        "short_description": "Exit non-zero (and print a warning) if any mount exceeds a usage threshold",
        "long_description": "Usage: disk-space-alert.sh 90 -- warns about any real filesystem over 90% used. Meant to be wrapped by cron + your own notifier (mail, Telegram, etc).",
        "content": """#!/bin/bash
set -euo pipefail
THRESHOLD="${1:-90}"
STATUS=0
while read -r pct mount; do
  pct_num="${pct%\\%}"
  if [[ "$pct_num" -ge "$THRESHOLD" ]]; then
    echo "WARNING: $mount is ${pct} full"
    STATUS=1
  fi
done < <(df -hP -x tmpfs -x devtmpfs -x overlay | tail -n +2 | awk '{print $5, $6}')
exit "$STATUS"
""",
    },
    {
        "name": "list-listening-ports.sh",
        "tags": "network",
        "run_mode": "manual",
        "short_description": "Show listening TCP/UDP ports with the owning process",
        "long_description": "Wrapper around `ss -tulpn` with a cleaner column layout. Needs root/sudo to see process names for ports not owned by the current user.",
        "content": """#!/bin/bash
set -euo pipefail
ss -tulpn 2>/dev/null | awk 'NR==1 || /LISTEN|UNCONN/ {printf "%-8s %-24s %s\\n", $1, $5, $NF}'
""",
    },
    {
        "name": "kill-by-port.sh",
        "tags": "network,process",
        "run_mode": "manual",
        "short_description": "Find and kill whatever process is listening on a given port",
        "long_description": "Usage: kill-by-port.sh 8080  -- shows the matching process first and asks for confirmation before sending SIGTERM.",
        "content": """#!/bin/bash
set -euo pipefail
PORT="${1:?Usage: kill-by-port.sh <port>}"
PID=$(lsof -ti tcp:"$PORT" || true)
if [[ -z "$PID" ]]; then
  echo "Nothing listening on port $PORT"
  exit 0
fi
ps -p "$PID" -o pid,comm,args
read -rp "Kill PID $PID? [y/N] " confirm
[[ "$confirm" == "y" ]] && kill "$PID"
""",
    },
    {
        "name": "backup-tar-gz.sh",
        "tags": "backup",
        "run_mode": "manual",
        "short_description": "Tar+gzip a directory into a date-stamped archive",
        "long_description": "Usage: backup-tar-gz.sh /path/to/dir /path/to/backups  -- writes <dirname>_YYYY-MM-DD.tar.gz.",
        "content": """#!/bin/bash
set -euo pipefail
SRC="${1:?Usage: backup-tar-gz.sh <src_dir> <dest_dir>}"
DEST="${2:?Usage: backup-tar-gz.sh <src_dir> <dest_dir>}"
NAME="$(basename "$SRC")_$(date +%F).tar.gz"
mkdir -p "$DEST"
tar -czf "$DEST/$NAME" -C "$(dirname "$SRC")" "$(basename "$SRC")"
echo "Wrote $DEST/$NAME ($(du -h "$DEST/$NAME" | cut -f1))"
""",
    },
    {
        "name": "rsync-mirror.sh",
        "tags": "backup",
        "run_mode": "manual",
        "short_description": "One-way rsync mirror with sane defaults (archive, delete, progress)",
        "long_description": "Usage: rsync-mirror.sh /src/ /dst/  -- keeps dest an exact mirror of src (deletes files in dest that no longer exist in src). Trailing slashes on both paths matter for rsync semantics.",
        "content": """#!/bin/bash
set -euo pipefail
SRC="${1:?Usage: rsync-mirror.sh <src>/ <dst>/}"
DST="${2:?Usage: rsync-mirror.sh <src>/ <dst>/}"
rsync -avh --delete --info=progress2 "$SRC" "$DST"
""",
    },
    {
        "name": "find-duplicate-files.sh",
        "tags": "files",
        "run_mode": "manual",
        "short_description": "Find duplicate files under a path by content hash",
        "long_description": "Hashes every file with sha256sum and prints groups that share a hash. Fine for a few thousand files; for whole media libraries use a dedicated tool (fdupes/rdfind) instead.",
        "content": """#!/bin/bash
set -euo pipefail
DIR="${1:-.}"
find "$DIR" -type f -exec sha256sum {} + | sort | \
  awk '{ if ($1 == prev) { if (!printed) print prevline; print; printed=1 } else { printed=0 } prev=$1; prevline=$0 }'
""",
    },
    {
        "name": "batch-rename.sh",
        "tags": "files",
        "run_mode": "manual",
        "short_description": "Rename all files matching a glob by substring replace",
        "long_description": "Usage: batch-rename.sh '*.jpeg' jpeg jpg  -- previews renames, asks before applying.",
        "content": """#!/bin/bash
set -euo pipefail
PATTERN="${1:?Usage: batch-rename.sh <glob> <find> <replace>}"
FIND="${2:?}"
REPLACE="${3:?}"
shopt -s nullglob
for f in $PATTERN; do
  new="${f//$FIND/$REPLACE}"
  [[ "$f" == "$new" ]] && continue
  echo "$f -> $new"
done
read -rp "Apply renames? [y/N] " confirm
[[ "$confirm" != "y" ]] && exit 0
for f in $PATTERN; do
  new="${f//$FIND/$REPLACE}"
  [[ "$f" == "$new" ]] && continue
  mv -- "$f" "$new"
done
""",
    },
    {
        "name": "cron-list-all.sh",
        "tags": "scheduling",
        "run_mode": "manual",
        "short_description": "List every user's crontab plus system cron.d entries",
        "long_description": "Needs root to see other users' crontabs. Useful when auditing what actually runs on a box you didn't set up.",
        "content": """#!/bin/bash
set -euo pipefail
for user in $(cut -f1 -d: /etc/passwd); do
  crontab -l -u "$user" 2>/dev/null | grep -v '^#' | grep -q . && {
    echo "===== crontab: $user ====="
    crontab -l -u "$user" 2>/dev/null
    echo
  }
done
echo "===== /etc/cron.d ====="
for f in /etc/cron.d/*; do
  [[ -f "$f" ]] && { echo "-- $f --"; cat "$f"; }
done
""",
    },
    {
        "name": "ssh-keygen-quick.sh",
        "tags": "security,ssh",
        "run_mode": "manual",
        "short_description": "Generate a new ed25519 SSH keypair with a sane default path/comment",
        "long_description": "Usage: ssh-keygen-quick.sh mykey  -- writes ~/.ssh/mykey and ~/.ssh/mykey.pub, ed25519, no passphrase prompt skipped (you still get asked).",
        "content": """#!/bin/bash
set -euo pipefail
NAME="${1:?Usage: ssh-keygen-quick.sh <key_name>}"
ssh-keygen -t ed25519 -f "$HOME/.ssh/$NAME" -C "${NAME}@$(hostname)-$(date +%F)"
echo "Public key:"
cat "$HOME/.ssh/$NAME.pub"
""",
    },
    {
        "name": "update-check.sh",
        "tags": "packages,updates",
        "run_mode": "manual",
        "short_description": "Check for available package updates (apt or dnf, whichever exists)",
        "long_description": "Detects apt-get vs dnf and lists upgradable packages without installing anything.",
        "content": """#!/bin/bash
set -euo pipefail
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  apt list --upgradable 2>/dev/null | tail -n +2
elif command -v dnf >/dev/null; then
  dnf check-update || true
else
  echo "No supported package manager found (apt/dnf)." >&2
  exit 1
fi
""",
    },
    {
        "name": "zombie-process-check.sh",
        "tags": "process,monitoring",
        "run_mode": "manual",
        "short_description": "List zombie (defunct) processes and their parents",
        "long_description": "A zombie can't be killed directly -- if there are many, the fix is usually restarting the parent process shown here.",
        "content": """#!/bin/bash
set -euo pipefail
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/ {print}'
""",
    },
    {
        "name": "top-memory-processes.sh",
        "tags": "process,monitoring",
        "run_mode": "manual",
        "short_description": "Top N processes by resident memory usage",
        "long_description": "Usage: top-memory-processes.sh 15",
        "content": """#!/bin/bash
set -euo pipefail
N="${1:-10}"
ps -eo pid,comm,%mem,rss --sort=-%mem | head -n "$((N + 1))"
""",
    },
    {
        "name": "top-cpu-processes.sh",
        "tags": "process,monitoring",
        "run_mode": "manual",
        "short_description": "Top N processes by CPU usage",
        "long_description": "Usage: top-cpu-processes.sh 15",
        "content": """#!/bin/bash
set -euo pipefail
N="${1:-10}"
ps -eo pid,comm,%cpu --sort=-%cpu | head -n "$((N + 1))"
""",
    },
    {
        "name": "public-ip.sh",
        "tags": "network",
        "run_mode": "manual",
        "short_description": "Print this machine's public IPv4 address",
        "long_description": "Tries ifconfig.me, falls back to icanhazip.com if the first is unreachable.",
        "content": """#!/bin/bash
set -euo pipefail
curl -4 -s --max-time 3 ifconfig.me || curl -4 -s --max-time 3 icanhazip.com
""",
    },
    {
        "name": "uptime-summary.sh",
        "tags": "monitoring",
        "run_mode": "manual",
        "short_description": "One-screen summary: uptime, load, memory, logged-in users",
        "long_description": "A quick \"how's this box doing\" check without opening five different commands.",
        "content": """#!/bin/bash
set -euo pipefail
echo "Host: $(hostname)"
uptime
echo
free -h
echo
echo "Logged in:"
who
""",
    },
    {
        "name": "journal-errors-today.sh",
        "tags": "logs,systemd",
        "run_mode": "manual",
        "short_description": "Show today's journal entries at warning level or above",
        "long_description": "journalctl -p warning filtered to since midnight -- the fastest way to see \"what went wrong today\" on a systemd box.",
        "content": """#!/bin/bash
set -euo pipefail
journalctl -p warning --since today --no-pager
""",
    },
    {
        "name": "mysql-dump-all.sh",
        "tags": "backup,database",
        "run_mode": "manual",
        "short_description": "Dump every MySQL/MariaDB database to a timestamped directory",
        "long_description": "Template -- edit DB_USER/DB_HOST or export MYSQL_PWD before running. Excludes information_schema/performance_schema/mysql/sys system databases.",
        "content": """#!/bin/bash
set -euo pipefail
DB_USER="${DB_USER:-root}"
DB_HOST="${DB_HOST:-127.0.0.1}"
OUT="${1:-./mysql-backup-$(date +%F)}"
mkdir -p "$OUT"
for db in $(mysql -u"$DB_USER" -h"$DB_HOST" -N -e "SHOW DATABASES;" | \
    grep -Ev '^(information_schema|performance_schema|mysql|sys)$'); do
  echo "Dumping $db..."
  mysqldump -u"$DB_USER" -h"$DB_HOST" "$db" > "$OUT/$db.sql"
done
""",
    },
    {
        "name": "postgres-dump-all.sh",
        "tags": "backup,database",
        "run_mode": "manual",
        "short_description": "Dump every PostgreSQL database to a timestamped directory",
        "long_description": "Template -- assumes passwordless local auth (peer/trust) or a configured .pgpass. Excludes the template0/template1 system databases.",
        "content": """#!/bin/bash
set -euo pipefail
PG_USER="${PG_USER:-postgres}"
OUT="${1:-./postgres-backup-$(date +%F)}"
mkdir -p "$OUT"
for db in $(psql -U "$PG_USER" -tAc "SELECT datname FROM pg_database WHERE datistemplate = false;"); do
  echo "Dumping $db..."
  pg_dump -U "$PG_USER" "$db" > "$OUT/$db.sql"
done
""",
    },
    {
        "name": "firewall-status.sh",
        "tags": "security,network",
        "run_mode": "manual",
        "short_description": "Show active firewall rules (detects ufw vs iptables)",
        "long_description": "Prefers ufw status if ufw is installed and active, otherwise falls back to raw iptables -L.",
        "content": """#!/bin/bash
set -euo pipefail
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw status verbose
else
  sudo iptables -L -n -v
fi
""",
    },
    {
        "name": "passwordless-sudo-audit.sh",
        "tags": "security",
        "run_mode": "manual",
        "short_description": "List every NOPASSWD sudo rule across sudoers and sudoers.d",
        "long_description": "A quick security audit: NOPASSWD entries are exactly the commands an attacker with your user account could run without ever needing your password.",
        "content": """#!/bin/bash
set -euo pipefail
sudo grep -rn "NOPASSWD" /etc/sudoers /etc/sudoers.d/ 2>/dev/null | grep -v '^\\s*#'
""",
    },
    {
        "name": "log-tail-grep.sh",
        "tags": "logs",
        "run_mode": "manual",
        "short_description": "Tail a log file, filtered live by a grep pattern",
        "long_description": "Usage: log-tail-grep.sh /var/log/syslog ERROR",
        "content": """#!/bin/bash
set -euo pipefail
FILE="${1:?Usage: log-tail-grep.sh <file> <pattern>}"
PATTERN="${2:?Usage: log-tail-grep.sh <file> <pattern>}"
tail -F "$FILE" | grep --line-buffered -i "$PATTERN"
""",
    },
    {
        "name": "git-repo-cleanup.sh",
        "tags": "git",
        "run_mode": "manual",
        "short_description": "git gc + prune, dry-run of untracked files by default",
        "long_description": "Runs gc/prune (always safe) and shows what `git clean -fdx` WOULD remove. Pass --clean to actually remove untracked files.",
        "content": """#!/bin/bash
set -euo pipefail
git gc --prune=now
git remote prune origin 2>/dev/null || true
echo "Untracked files that would be removed by 'git clean -fdx':"
git clean -fdxn
if [[ "${1:-}" == "--clean" ]]; then
  git clean -fdx
fi
""",
    },
    {
        "name": "open-file-descriptors-top.sh",
        "tags": "process,monitoring",
        "run_mode": "manual",
        "short_description": "Processes with the most open file descriptors",
        "long_description": "Useful when you hit \"too many open files\" -- shows which process is the culprit before you raise ulimits blindly.",
        "content": """#!/bin/bash
set -euo pipefail
for pid in $(ls /proc | grep -E '^[0-9]+$'); do
  count=$(ls "/proc/$pid/fd" 2>/dev/null | wc -l)
  [[ "$count" -gt 0 ]] && echo "$count $pid $(ps -p "$pid" -o comm= 2>/dev/null)"
done | sort -rn | head -n 15
""",
    },
    {
        "name": "ssl-cert-expiry-check.sh",
        "tags": "security,network",
        "run_mode": "manual",
        "short_description": "Check a TLS certificate's expiry date for host:port",
        "long_description": "Usage: ssl-cert-expiry-check.sh example.com 443",
        "content": """#!/bin/bash
set -euo pipefail
HOST="${1:?Usage: ssl-cert-expiry-check.sh <host> [port]}"
PORT="${2:-443}"
echo | openssl s_client -connect "$HOST:$PORT" -servername "$HOST" 2>/dev/null | \
  openssl x509 -noout -enddate -subject
""",
    },

    # --- Cross-platform admin/dev cheatsheet (2026-07-21) ---
    {
        "name": 'Autoruns',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Shows EVERYTHING that launches at system startup',
        "long_description": "Services, scheduled tasks, registry Run keys, drivers, browser extensions - the most complete view of 'what ran at boot'. The classic first step in malware cleanup.",
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.Autoruns\n\nautorunsc64.exe -a * -c   # CLI version, CSV output, good for scripting/audits\n',
    },
    {
        "name": 'awk',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Quick processing of column/tabular data',
        "long_description": "Shorter and faster than writing a script for a simple column operation - used e.g. when parsing the output of 'ip neigh show' (awk '{print $5}' to pull out a MAC address).",
        "content": "# Install (if missing):\n# Part of coreutils/POSIX, always present\n\nawk '{print $1, $3}' file.txt     # pull out columns 1 and 3\nawk -F: '{print $1}' /etc/passwd    # custom delimiter (:)\n",
    },
    {
        "name": 'crontab - classic cron jobs',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Show scheduled cron jobs (user and system)',
        "long_description": 'Check this right after systemd timers, since older scripts often still run via classic cron rather than a systemd timer.',
        "content": "# Install (if missing):\n# sudo apt install cron   # sometimes missing on minimal/container images\n\ncrontab -l                       # current user's crontab\nsudo crontab -l -u <user>         # another user's crontab\ncat /etc/cron.d/*                 # system-wide cron entries\n",
    },
    {
        "name": 'curl + jq combo',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Directly filter an API response without saving an intermediate file',
        "long_description": 'Chaining curl → jq in one pipe is faster than downloading the response to a file and opening it in an editor - the exact pattern used today to verify Sindri API results.',
        "content": "# Install (if missing):\n# sudo apt install curl jq   # usually preinstalled already\n\ncurl -s https://api.example.com/users | jq '.[] | select(.active) | {id, name}'\n",
    },
    {
        "name": 'curl - authentication',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Different ways to authenticate API calls',
        "long_description": '-b/-c cookie jar is exactly what was used with Sindri (login returns a session cookie, sent on the next request).',
        "content": '# Install (if missing):\n# sudo apt install curl   # usually preinstalled already\n\ncurl -u user:pass https://api.example.com/                              # Basic auth\ncurl -H "Authorization: Bearer <token>" https://api.example.com/          # Bearer token\ncurl -b cookies.txt -c cookies.txt https://...                            # cookie persistence\n',
    },
    {
        "name": 'curl - POST/JSON requesty',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Send POST/JSON requests from the command line',
        "long_description": "The exact pattern used all through today's session for Sindri API calls (login, import/paste) - -d @file is cleaner than a long inline JSON string for more complex payloads.",
        "content": '# Install (if missing):\n# sudo apt install curl   # usually preinstalled already\n\ncurl -X POST https://api.example.com/endpoint -H "Content-Type: application/json" -d \'{"key":"value"}\'\ncurl -X POST ... -d @payload.json   # data from a file instead\n',
    },
    {
        "name": 'curl -v / -I',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'HTTP/TLS diagnostics straight from the command line',
        "long_description": '-v shows the entire exchange including the TLS handshake (useful for certificate issues), -I fetches only the response headers without the body (quick status/redirect check).',
        "content": '# Install (if missing):\n# sudo apt install curl   # usually preinstalled already\n\ncurl -v https://example.com   # full exchange including TLS handshake\ncurl -I https://example.com    # headers only\n',
    },
    {
        "name": 'df / du - disk space',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": "Find out what's using disk space",
        "long_description": 'df -h for an overview per mount, du -sh piped through sort -rh to find the specific large directories - the exact workflow for tracking down a full disk.',
        "content": '# Install (if missing):\n# Part of coreutils, always present\n\ndf -h                                # disk usage per mount\ndu -sh */ | sort -rh | head -20        # 20 largest directories in the current folder\n',
    },
    {
        "name": 'dig - DNS diagnostika',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Quick DNS record lookup, including against a specific server',
        "long_description": '+short strips out all the surrounding noise, @1.1.1.1 bypasses your local DNS cache (e.g. Pi-hole) when you need to see what the rest of the internet resolves, not just your own cached answer.',
        "content": '# Install (if missing):\n# sudo apt install dnsutils   # Debian/Ubuntu; RHEL/Fedora: bind-utils\n\ndig +short example.com          # quick answer without extra headers\ndig @1.1.1.1 example.com          # query against a specific DNS server\n',
    },
    {
        "name": 'diskutil',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Manage disks and partitions - the fdisk/lsblk equivalent',
        "long_description": 'list shows an overview of all attached disks including APFS containers, info gives detail on a specific volume (filesystem, size, encryption status).',
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\ndiskutil list          # list of disks and partitions\ndiskutil info disk0     # detail on a specific disk\n',
    },
    {
        "name": 'docker compose - basic workflow',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Rebuild, logs and service status in a compose stack',
        "long_description": 'Everyday workflow when working on your own apps - --build forces a rebuild on code changes, logs -f on one service is more precise than tailing the whole stack at once.',
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker compose up -d --build      # rebuild + restart in the background\ndocker compose logs -f <service>   # logs for one service in the compose stack\ndocker compose ps                  # status of all services in the stack\n',
    },
    {
        "name": 'docker exec',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Get a shell inside a running container / run a command inside it',
        "long_description": "Instead of restarting a container with a different entrypoint, go straight inside to check files, env vars, or network connectivity from the container's point of view.",
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker exec -it <container> /bin/sh   # interactive shell (or /bin/bash if available)\ndocker exec <container> env            # print env vars without opening a shell\n',
    },
    {
        "name": 'docker inspect',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Detailed JSON state of a container (networks, mounts, health, restart count)',
        "long_description": "When docker ps isn't enough - inspect shows the exact reason for restarts, IPs on each network, mount points, health-check history. Pipe through jq to pull out exactly what you need.",
        "content": "# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker inspect <container> | jq '.[0].State'            # state (running/health/restart count)\ndocker inspect <container> | jq '.[0].NetworkSettings'   # network settings (IP, ports)\n",
    },
    {
        "name": 'docker logs',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": "Follow and filter a container's logs",
        "long_description": 'The default first step when debugging a stack - -f for live tailing, --since to limit volume on long-running containers.',
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker logs -f --tail 100 <container>   # live-tail the last 100 lines\ndocker logs --since 1h <container>       # only the last hour\n',
    },
    {
        "name": 'docker network inspect',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Network diagnostics between containers',
        "long_description": "When two containers in the same compose stack can't talk to each other - confirm they're on the same Docker network and try pinging directly from one to the other by service name.",
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker network inspect <network>                 # list of containers on that network and their IPs\ndocker exec <container> ping <other_container>    # confirm connectivity from inside the network\n',
    },
    {
        "name": 'docker stats',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Live CPU/RAM/network usage per container',
        "long_description": 'A quick way to find the container eating resources without deploying a full monitoring stack - --no-stream for a one-shot snapshot, script-friendly.',
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker stats --no-stream   # one-shot CPU/RAM/network snapshot per container\n',
    },
    {
        "name": 'docker system prune / df',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Clean up unused images/containers/volumes',
        "long_description": "docker system df first shows how much space you'd actually reclaim. prune -a --volumes is irreversible (also removes named volumes with no attached container) - container prune is a safer subset.",
        "content": '# Install (if missing):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker system df                    # overview of space used by images/containers/volumes\ndocker container prune               # only stopped containers, safer\ndocker system prune -a --volumes     # WARNING: removes everything unused, including volumes\n',
    },
    {
        "name": 'dscl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Directory services - local and AD-bound users/groups',
        "long_description": 'Lower-level than sysadminctl, can read/change almost anything in the directory service database - powerful, but easy to break a system account with a careless write.',
        "content": "# Install (if missing):\n# Built into macOS, nothing to install\n\ndscl . -list /Users                        # list of local users\ndscl . -read /Users/$(whoami) UniqueID       # a specific user's UID\n",
    },
    {
        "name": 'Enter-PSSession / Invoke-Command',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Remote management of Windows machines (WinRM), the SSH equivalent',
        "long_description": 'PowerShell Remoting over WinRM is the Windows equivalent of SSH for remote administration - needs to be enabled (Enable-PSRemoting) on the target machine.',
        "content": '# Install (if missing):\n# Built in, but must be enabled on the target machine: Enable-PSRemoting -Force\n\nEnter-PSSession -ComputerName SERVER01                            # interactive remote shell\nInvoke-Command -ComputerName SERVER01 -ScriptBlock { Get-Service } # one-off remote command\n',
    },
    {
        "name": 'ffmpeg - format conversion',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Universal audio/video format conversion',
        "long_description": '-crf (Constant Rate Factor) controls the quality/size tradeoff - lower number = better quality/larger file, 23 is a reasonable default.',
        "content": '# Install (if missing):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i input.mov -c:v libx264 -crf 23 output.mp4\n',
    },
    {
        "name": 'ffmpeg - recording an RTSP stream',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Record an RTSP stream to a file without quality loss (copy mode)',
        "long_description": '-c copy copies the stream 1:1 without re-encoding (fast, no quality loss/CPU load) - useful for briefly capturing evidence from a camera without a full NVR setup.',
        "content": '# Install (if missing):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i rtsp://192.168.1.13:554/stream -c copy -t 60 recording.mp4\n',
    },
    {
        "name": 'ffmpeg - screenshot z RTSP',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Grab a single frame from an RTSP camera stream',
        "long_description": 'A quick way to confirm an RTSP stream actually works and see exactly what the camera sees, without needing to open VLC or a full app.',
        "content": '# Install (if missing):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i rtsp://192.168.1.13:554/stream -vframes 1 screenshot.jpg\n',
    },
    {
        "name": 'ffprobe',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Get the exact technical parameters of an audio/video file',
        "long_description": 'Part of the ffmpeg toolset - instead of guessing from the filename, gives you exact data (video codec, framerate, audio channels) in machine-readable JSON.',
        "content": '# Install (if missing):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffprobe -v quiet -print_format json -show_format -show_streams video.mp4\n',
    },
    {
        "name": 'find',
        "tags": 'cheatsheet,find-xargs',
        "run_mode": '',
        "short_description": 'Find files by name/age/size/type',
        "long_description": "Much more precise than manually browsing with ls - mtime/size filters are exactly what you need to find 'what's using my disk space' or 'old backups to delete'.",
        "content": '# Install (if missing):\n# Part of findutils, present almost everywhere\n\nfind . -name "*.log" -mtime +7   # files older than 7 days\nfind . -type f -size +100M           # files larger than 100MB\n',
    },
    {
        "name": 'find + xargs',
        "tags": 'cheatsheet,find-xargs',
        "run_mode": '',
        "short_description": "Apply a command to all of find's results at once",
        "long_description": 'The -print0/-0 combination is an important safety detail - without it, find+xargs mishandles filenames with spaces (splits them into two arguments). Without it, rm could end up deleting something other than what you intended.',
        "content": '# Install (if missing):\n# Part of findutils, present almost everywhere\n\nfind . -name "*.tmp" -print0 | xargs -0 rm   # safe deletion\nfind . -name "*.log" | xargs grep -l "ERROR"   # search inside content at once\n',
    },
    {
        "name": 'Get-ADUser / Get-ADComputer',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Query Active Directory (RSAT/AD module)',
        "long_description": 'The basis of enterprise Windows administration - finding inactive accounts/computers is a common security/hygiene check in an AD environment. Requires the AD PowerShell module (RSAT) installed.',
        "content": '# Install (if missing):\n# Install-WindowsFeature RSAT-AD-PowerShell   # server; on Windows 10/11 client: Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0\n\nGet-ADUser -Filter {Enabled -eq $false}                # list of disabled accounts\nGet-ADComputer -Filter * -Properties LastLogonDate       # last logon time of domain computers\n',
    },
    {
        "name": 'Get-ComputerInfo / systeminfo',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": "Quick overview of a machine's hardware/OS version",
        "long_description": 'Get-ComputerInfo is slower but structured (filterable), systeminfo is a fast plain-text dump - good to know both, depending on whether you need speed or precise parsing.',
        "content": '# Install (if missing):\n# Built into Windows/PowerShell, nothing to install\n\nGet-ComputerInfo | Select WindowsProductName, OsHardwareAbstractionLayer, CsProcessors\nsysteminfo   # older but faster cmd alternative with a full dump\n',
    },
    {
        "name": 'Get-Content -Tail -Wait',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Live-follow a growing log file (tail -f equivalent)',
        "long_description": "-Wait keeps the file open and prints new lines as they arrive, exactly like Linux's 'tail -f'.",
        "content": '# Install (if missing):\n# Built into PowerShell, nothing to install\n\nGet-Content C:\\logs\\app.log -Tail 20 -Wait\n',
    },
    {
        "name": 'Get-NetTCPConnection',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'List of listening ports and their owning processes',
        "long_description": "A more modern PowerShell replacement for netstat -ano - can be joined with Get-Process via OwningProcess to see exactly which process holds a given port. Windows equivalent of 'ss -tulnp'.",
        "content": '# Install (if missing):\n# Part of the NetTCPIP module, built in\n\nGet-NetTCPConnection -State Listen | Sort-Object LocalPort\n',
    },
    {
        "name": 'Get-Process / Stop-Process',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Process management via PowerShell - a more modern tasklist/taskkill',
        "long_description": 'Get-Process returns objects (not just text), so you can filter/sort/export it directly through the pipeline instead of parsing text like the classic cmd tools - the key difference between PowerShell and cmd.',
        "content": '# Install (if missing):\n# Built into PowerShell (built-in cmdlets), nothing to install\n\nGet-Process | Sort-Object CPU -Descending | Select -First 10   # top 10 processes by CPU\nStop-Process -Name notepad -Force                              # force-kill by name\n',
    },
    {
        "name": 'Get-Service / Restart-Service',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Manage Windows services (the systemctl equivalent)',
        "long_description": 'The direct Windows equivalent of systemctl status/restart. Where-Object filters objects the same way grep filters text, just over structured data.',
        "content": '# Install (if missing):\n# Built into PowerShell, nothing to install\n\nGet-Service | Where-Object {$_.Status -eq "Running"}   # list of running services\nRestart-Service -Name Spooler -Force                      # restart a specific service\n',
    },
    {
        "name": 'Get-WinEvent',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Windows Event Log - the journalctl equivalent',
        "long_description": 'FilterHashtable is more efficient than filtering after download (server-side filter), which matters on hosts with large logs. Level 1=Critical, 2=Error, 3=Warning.',
        "content": "# Install (if missing):\n# Built into PowerShell, nothing to install\n\nGet-WinEvent -LogName System -MaxEvents 50                                    # last 50 system events\nGet-WinEvent -FilterHashtable @{LogName='Application'; Level=2} -MaxEvents 20  # errors only (Level 2) from the Application log\n",
    },
    {
        "name": 'git bisect',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Binary-search for the commit that introduced a bug',
        "long_description": 'Instead of manually walking through history, git offers commits to test (binary search) until it narrows down to the exact one that broke things.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit bisect start && git bisect bad && git bisect good <hash>   # git then offers commits to test\n',
    },
    {
        "name": 'git cherry-pick',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Bring a single specific commit onto another branch',
        "long_description": 'When you need just one fix from another branch without merging the whole thing.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit cherry-pick <hash>   # applies the changes from another commit/branch onto the current one\n',
    },
    {
        "name": 'git filter-branch (msg-filter)',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Rewrite commit messages across the entire repo history',
        "long_description": 'Exactly the command used to strip AI co-author trailers from commit history before a public push. Requires a force push, and verify the tree is unchanged before/after via HEAD^{tree}.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit filter-branch --msg-filter \'sed "/Co-Authored-By: Claude/d"\' -- --all\n',
    },
    {
        "name": 'git log - useful formats',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": "More readable views of history and a file's changes",
        "long_description": '--graph --all gives a visual overview of branching instead of a flat list, -p on a file shows exactly when and how it changed across the whole history.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit log --oneline --graph --all   # visual overview of branching\ngit log -p -- <file>                # full history of changes to a specific file\n',
    },
    {
        "name": 'git rebase -i',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Interactively rewrite history before pushing',
        "long_description": "Squash/reword/reorder the last N commits into a clean history before pushing - most useful on a feature branch with lots of 'wip' commits.",
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit rebase -i HEAD~5   # last 5 commits - squash/reword/reorder\n',
    },
    {
        "name": 'git reflog',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": "Recover 'lost' commits after a bad reset/rebase",
        "long_description": 'reflog remembers every single HEAD move, even the ones regular git log can no longer see (after a hard reset, force push, aborted rebase). Almost always recoverable until garbage collection runs.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit reflog                            # history of every HEAD move\ngit reset --hard <reflog-hash>          # go back to the state before the bad rebase/reset\n',
    },
    {
        "name": 'git stash',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Temporarily shelve work in progress',
        "long_description": '-u also includes untracked files (the default skips them, a common trap). Useful to switch branches quickly without committing unfinished work.',
        "content": '# Install (if missing):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit stash push -u -m "description"   # -u = include untracked files too\ngit stash pop                          # restore the last stash and remove it from the list\n',
    },
    {
        "name": 'gpupdate / gpresult',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Force Group Policy and diagnose it',
        "long_description": "gpresult /R is the key diagnostic tool when 'this policy should apply but doesn't' - shows exactly which GPOs actually applied and which were filtered/blocked.",
        "content": '# Install (if missing):\n# Built into Windows (built-in cmd tools), nothing to install\n\ngpupdate /force   # force group policy immediately on the local machine\ngpresult /R        # which policies actually applied, and from where\n',
    },
    {
        "name": 'grep -P / ripgrep (rg)',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Search for patterns in text/code, ripgrep as a faster alternative',
        "long_description": "ripgrep is faster than grep by default (parallelization, smart defaults) and automatically skips .gitignore'd files (node_modules, .git) - a common choice in modern dev tools.",
        "content": '# Install (if missing):\n# grep is always present; ripgrep: sudo apt install ripgrep   # brew install ripgrep\n\ngrep -rn -P \'\\d{3}-\\d{4}\' .   # Perl-compatible regex\nrg "TODO" --type py             # respects .gitignore automatically\n',
    },
    {
        "name": 'gzip / zcat',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Compress individual files, zcat to search without decompressing',
        "long_description": 'Common with rotated logs (access.log.1.gz) - zcat/zgrep let you search directly inside a compressed file without manually decompressing it first.',
        "content": '# Install (if missing):\n# Part of coreutils/gzip, present almost everywhere\n\ngzip big_log.txt              # creates .gz, removes the original\ngunzip big_log.txt.gz           # decompress back\nzcat big_log.txt.gz | grep "error"   # search without decompressing\n',
    },
    {
        "name": 'Handle',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Find out which process is holding a specific file open',
        "long_description": "A direct answer to the 'file is in use by another process' message from Windows Explorer - instead of guessing, shows the exact PID and process name.",
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.Handle\n\nhandle64.exe file.txt   # finds the process holding this file open\n',
    },
    {
        "name": 'Homebrew (brew)',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'The de-facto standard package manager for macOS',
        "long_description": "macOS doesn't ship a built-in package manager like apt/pacman - brew is the community standard that fills the gap. --versions shows exact installed versions, useful when debugging compatibility.",
        "content": '# Install (if missing):\n# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n\nbrew list --versions\nbrew update && brew upgrade\n',
    },
    {
        "name": 'httpie',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'More readable/faster alternative to curl for API testing',
        "long_description": 'Automatically formats JSON (colored, indented), no need for -H Content-Type or quotes around JSON - faster for interactive testing, curl is more universal/scriptable.',
        "content": '# Install (if missing):\n# sudo apt install httpie   # or: pip install httpie\n\nhttp POST api.example.com/endpoint key=value\nhttp GET api.example.com/users Authorization:"Bearer token"\n',
    },
    {
        "name": 'ip route / ip addr',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Routing and IP diagnostics on the local machine',
        "long_description": 'ip route get shows exactly which interface/route a packet would take to a given destination without actually sending it - useful on hosts with multiple networks (e.g. Docker bridge networks).',
        "content": '# Install (if missing):\n# Part of iproute2, preinstalled on most Linux distros\n\nip route get 8.8.8.8   # which interface/route a packet would take to reach this destination\nip addr show             # current IP addresses on all interfaces\n',
    },
    {
        "name": 'journalctl - service logs',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Filtering system/service logs via journald',
        "long_description": '-u narrows to one unit, -p err -b shows only errors since the last boot - the exact kind of filtering that matters once a host has been running a while.',
        "content": '# Install (if missing):\n# Part of systemd, nothing to install\n\njournalctl -u <service> -f                  # live-follow a unit\'s log\njournalctl -u <service> --since "1 hour ago"  # logs from the last hour\njournalctl -p err -b                          # errors only, since last boot\n',
    },
    {
        "name": 'journalctl --vacuum',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Managing journald log size',
        "long_description": 'When the journal itself is surprisingly taking up a lot of space (common on hosts with lots of containers/services) - vacuum-time trims old entries without changing the retention policy config.',
        "content": '# Install (if missing):\n# Part of systemd, nothing to install\n\njournalctl --disk-usage              # how much space the journal is using\nsudo journalctl --vacuum-time=7d       # remove entries older than 7 days\n',
    },
    {
        "name": 'jq',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Parse/filter JSON from the command line',
        "long_description": 'Without jq, JSON output from an API/log would have to be parsed via grep/sed with a high chance of error - jq understands the structure and chains like a normal Unix pipe tool. Used constantly today for the Sindri API calls.',
        "content": "# Install (if missing):\n# sudo apt install jq   # brew install jq (macOS)\n\ncurl -s https://api.example.com/data | jq '.items[] | select(.active==true) | .name'\njq -r '.[0].id' file.json   # raw output without quotes\n",
    },
    {
        "name": 'launchctl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Manage launchd services - the macOS equivalent of systemctl',
        "long_description": "launchd is macOS's init/service manager. load/unload starts/stops LaunchAgents (per-user) and LaunchDaemons (system-wide) defined in .plist files.",
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\nlaunchctl list | grep <name>                          # list of running launchd jobs\nlaunchctl load/unload ~/Library/LaunchAgents/x.plist   # load/unload a specific agent\n',
    },
    {
        "name": 'log show',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Unified logging system - the macOS equivalent of journalctl',
        "long_description": "The predicate syntax allows precise filtering without grepping through text output - a similar concept to journalctl's FilterHashtable on Windows.",
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\nlog show --predicate \'eventMessage contains "error"\' --last 1h\n',
    },
    {
        "name": 'mtr - continuous traceroute',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Path to a destination with per-hop loss, live',
        "long_description": 'Better than plain traceroute - runs continuously and shows the % of packets lost at every hop, so you can pinpoint exactly where along the path a problem is occurring.',
        "content": '# Install (if missing):\n# sudo apt install mtr\n\nmtr example.com   # live/continuous traceroute with per-hop packet loss\n',
    },
    {
        "name": 'nc -zv - test portu',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Quick check that a port is open/reachable',
        "long_description": 'The simplest possible connectivity test without needing a full nmap scan - good when you already know exactly which one port you want to check.',
        "content": '# Install (if missing):\n# sudo apt install netcat-openbsd\n\nnc -zv 192.168.1.10 443   # confirm a port is open/reachable\n',
    },
    {
        "name": 'openssl s_client',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Check a TLS certificate and its chain straight from the CLI',
        "long_description": 'Check expiry, certificate chain and SNI behavior without opening a browser - useful when debugging Caddy/Cloudflare certificate issues.',
        "content": '# Install (if missing):\n# sudo apt install openssl   # usually preinstalled already\n\nopenssl s_client -connect example.com:443 -servername example.com\n',
    },
    {
        "name": 'pg_dump / pg_restore',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Back up and restore a Postgres database',
        "long_description": 'A regular pg_dump before any risky schema change is a cheap insurance policy against an irreversible mistake.',
        "content": '# Install (if missing):\n# sudo apt install postgresql-client\n\npg_dump -U user dbname > backup.sql   # dump to a SQL file\npsql -U user dbname < backup.sql        # restore from the dump\n',
    },
    {
        "name": 'pip freeze / requirements.txt',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Reproducible dependencies - the exact same versions on another machine',
        "long_description": "Without requirements.txt, 'works on my machine' becomes a common problem - freeze captures exact versions including transitive dependencies.",
        "content": '# Install (if missing):\n# pip is usually bundled with Python; if missing: sudo apt install python3-pip\n\npip freeze > requirements.txt       # export exact versions\npip install -r requirements.txt      # install from that export\n',
    },
    {
        "name": 'pipx',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Install Python CLI tools without polluting the global Python install',
        "long_description": "Unlike 'pip install --user', pipx gives each tool its own isolated environment, so they don't fight each other over dependencies, while the command is still available globally on PATH.",
        "content": '# Install (if missing):\n# sudo apt install pipx   # or: python3 -m pip install --user pipx\n\npipx install httpie   # isolated venv, available globally\n',
    },
    {
        "name": 'pmset',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Manage power and sleep settings',
        "long_description": '-g shows current power settings (sleep timers, displaysleep etc), also commonly used to prevent sleep during a long-running process.',
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\npmset -g                # current power settings\nsudo pmset sleepnow      # sleep immediately\n',
    },
    {
        "name": 'Process Explorer',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": "'Task Manager on steroids' - shows handles, DLLs, color-codes processes",
        "long_description": "Not a 'hacking tool' - safe for a DBA/dev to run without concern. Portable exe, no install needed. Shows exactly which handles/DLLs a process has open, which Task Manager can't.",
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.ProcessExplorer   # or ZIP from learn.microsoft.com/sysinternals\n\nprocexp64.exe   # launches the GUI, portable exe, no install needed\n',
    },
    {
        "name": 'Process Monitor (procmon)',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Live log of every file/registry/process/network event',
        "long_description": "The key tool for 'why does this app crash / can't read a file' - you see exactly which file/registry key the app tried to open and whether it failed (Access Denied, Not Found...).",
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.ProcessMonitor\n\nprocmon.exe /AcceptEula /Quiet /Minimized   # quiet start, filters are set in the GUI\n',
    },
    {
        "name": 'psql',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Interactive work with a Postgres database',
        "long_description": 'The backslash commands (\\dt, \\d, \\l) are psql-specific shortcuts - faster than writing a full SELECT * FROM information_schema query.',
        "content": '# Install (if missing):\n# sudo apt install postgresql-client\n\npsql -U user -d dbname -h localhost   # connect\n\\dt                                     # list tables\n\\d table_name                            # table structure\n',
    },
    {
        "name": 'python venv',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Isolate Python dependencies per project, avoids version conflicts',
        "long_description": 'Without venv, all pip-installed packages would go into the global environment, which quickly leads to version conflicts once you have multiple projects. Every project should have its own .venv.',
        "content": "# Install (if missing):\n# sudo apt install python3-venv   # the venv module isn't always bundled with the base python3 package on Debian/Ubuntu\n\npython3 -m venv .venv          # create a virtual environment\nsource .venv/bin/activate        # activate (Linux/macOS)\ndeactivate                        # deactivate\n",
    },
    {
        "name": 'robocopy',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Robust file copy/sync, replaces xcopy',
        "long_description": '/MIR mirrors (deletes anything in the destination that no longer exists in the source - be careful the first time you use it), built-in retry on network hiccups - a common tool for backups/migrations on Windows servers.',
        "content": '# Install (if missing):\n# Built into Windows since Vista/Server 2008\n\nrobocopy C:\\source D:\\dest /MIR /LOG:copy.log\n',
    },
    {
        "name": 'rsync',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Efficient file synchronization - transfers only changes',
        "long_description": 'Unlike cp/scp it transfers only the differences (delta), so repeated syncing of a large directory is dramatically faster. The basis of almost every backup script.',
        "content": '# Install (if missing):\n# sudo apt install rsync   # brew install rsync (macOS ships an older version by default)\n\nrsync -avz --progress source/ dest/            # -a=archive, -z=compression\nrsync -avz -e ssh source/ user@host:/dest/       # over SSH to a remote machine\n',
    },
    {
        "name": 'scp / rsync cez SSH',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Transfer files over SSH - scp for simple cases, rsync for efficiency',
        "long_description": 'scp is simpler to remember for a single file, but rsync is always the better choice for repeated transfers/large directories thanks to delta transfer.',
        "content": '# Install (if missing):\n# sudo apt install openssh-client rsync\n\nscp file.txt user@host:/path/\nrsync -avz -e ssh folder/ user@host:/path/\n',
    },
    {
        "name": 'screen',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Older alternative to tmux, still common on older/minimal systems',
        "long_description": "Same purpose as tmux (session persistence), but older and less flexible with split panes. Good to know since it's the only thing preinstalled on some systems.",
        "content": '# Install (if missing):\n# sudo apt install screen   # brew install screen (macOS)\n\nscreen -S name   # new session\nscreen -r name    # attach\nCtrl+a d            # detach\n',
    },
    {
        "name": 'sed',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Bulk find-and-replace in text/files',
        "long_description": "The exact tool used to strip 'Co-Authored-By: Claude' trailers from git history (via msg-filter). -i without a backup is irreversible, be careful.",
        "content": "# Install (if missing):\n# Part of coreutils/POSIX, always present\n\nsed 's/old/new/g' file.txt      # output to stdout\nsed -i 's/old/new/g' file.txt     # -i rewrites the file in place\n",
    },
    {
        "name": 'Sophia Script',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Community PowerShell collection for Windows 10/11 privacy/debloat/tweaks',
        "long_description": 'A modular script (not a single command) that disables telemetry, removes preinstalled apps, and tweaks UI/performance settings - popular among power users and admins managing their own machines. Read what it actually does before running it, some changes are quite invasive.',
        "content": '# Install (if missing):\n# git clone https://github.com/farag2/Sophia-Script-for-Windows   # run as a .ps1 module, needs Set-ExecutionPolicy RemoteSigned\n\n# GitHub: farag2/Sophia-Script-for-Windows\nImport-Module .\\Sophia.psm1\nDisableTelemetry\n',
    },
    {
        "name": 'sort / uniq / wc',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Counting occurrences, deduplication, basic log analytics',
        "long_description": 'sort|uniq -c|sort -rn is one of the most useful Unix pipeline patterns there is - works on anything (IPs in a log, error messages, HTTP status codes) and gives an exact frequency table without writing a script.',
        "content": '# Install (if missing):\n# Part of coreutils, always present\n\nsort file.txt | uniq -c | sort -rn | head -10   # top 10 most frequent lines\nwc -l file.txt                                   # line count\n',
    },
    {
        "name": 'spctl / codesign',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Gatekeeper and code-signing verification for apps - security relevant',
        "long_description": 'Checks whether an app would pass Gatekeeper (spctl) and the detail of its code-signing certificate (codesign) - important when judging the trustworthiness of unsigned/third-party software.',
        "content": '# Install (if missing):\n# Built into macOS (codesign needs Xcode Command Line Tools): xcode-select --install\n\nspctl --assess --verbose /Applications/App.app     # check whether an app would pass Gatekeeper\ncodesign -dv --verbose=4 /Applications/App.app       # detail of its code-signing certificate\n',
    },
    {
        "name": 'sqlite3 .backup',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": "Safely back up a SQLite database while it's actively in use",
        "long_description": "A plain 'cp database.db backup.db' can produce a corrupted copy if something is writing to it at the same time (a half-finished write) - the .backup command handles this correctly via SQLite's own backup API.",
        "content": '# Install (if missing):\n# sudo apt install sqlite3\n\nsqlite3 database.db ".backup backup.db"\n',
    },
    {
        "name": 'sqlite3 CLI',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Direct work with SQLite database files',
        "long_description": 'SQLite has no server/process - the database is a single file, so it can be queried/backed up directly by copying the file (as long as nothing is writing to it at the time).',
        "content": '# Install (if missing):\n# sudo apt install sqlite3\n\nsqlite3 database.db "SELECT * FROM users LIMIT 5;"   # one-liner query\nsqlite3 database.db ".tables"                          # list tables\n',
    },
    {
        "name": 'ss - listening ports',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Modern alternative to netstat for listing open ports',
        "long_description": "-tulnp = TCP+UDP, listening, numeric, with PID/process name (needs root to show the PID). Exactly what you'd use to see what's actually running on a given port.",
        "content": '# Install (if missing):\n# Part of iproute2, preinstalled on most Linux distros\n\nss -tulnp   # all listening TCP/UDP ports + owning process\n',
    },
    {
        "name": 'SSH ControlMaster (multiplexing)',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Share a single TCP connection across multiple SSH commands to the same host',
        "long_description": "The second and later SSH connections to the same host are almost instant (no new TCP handshake/auth) - significantly speeds up scripts that make many SSH calls in a row (like today's Sindri registration via several SSH commands).",
        "content": '# Install (if missing):\n# sudo apt install openssh-client   # usually preinstalled already\n\n# in ~/.ssh/config:\nHost *\n    ControlMaster auto\n    ControlPath ~/.ssh/sockets/%r@%h-%p\n    ControlPersist 10m\n',
    },
    {
        "name": 'SSH port forwarding',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Tunnel ports over SSH without needing a VPN',
        "long_description": '-L is useful when you want your local browser to reach a service that only listens on localhost on a remote server (e.g. an internal admin UI). -R does the opposite, exposing your local service to the remote machine.',
        "content": '# Install (if missing):\n# sudo apt install openssh-client   # usually preinstalled already\n\nssh -L 8080:localhost:80 user@host    # local 8080 -> remote 80\nssh -R 9000:localhost:3000 user@host   # the opposite direction\n',
    },
    {
        "name": 'ssh-agent / ssh-add',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Enter your passphrase once instead of on every SSH connection',
        "long_description": 'Without an agent, a passphrase-protected key prompts for the password on every single SSH connection - the agent holds it in memory for the whole session.',
        "content": '# Install (if missing):\n# sudo apt install openssh-client   # usually preinstalled already; Windows: Settings > Optional Features > OpenSSH Client\n\neval $(ssh-agent)              # start the agent\nssh-add ~/.ssh/id_ed25519       # add a key\n',
    },
    {
        "name": 'sysadminctl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Newer, safer management of user accounts',
        "long_description": 'Recommended since macOS 10.13 instead of directly manipulating dscl for common operations (creating an account, changing a password, SecureToken status).',
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\nsysadminctl -deleteUser username\n',
    },
    {
        "name": 'Sysmon',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Advanced system logging - the basis of DIY threat hunting on Windows',
        "long_description": 'Logs far more detail than the default Windows Event Log (process creation with the full command line, network connections, file creates) straight into the Event Log, from where it can be collected by a SIEM. Usually the first thing security teams deploy on Windows endpoints - a good starting point is the public SwiftOnSecurity config.',
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.Sysmon   # + a community config, e.g. github.com/SwiftOnSecurity/sysmon-config\n\nsysmon64.exe -i sysmonconfig.xml   # install as a service with a config\n',
    },
    {
        "name": 'systemctl daemon-reload',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Required after every edit to a .service file',
        "long_description": "Without daemon-reload, systemd keeps using the old version of the unit file from memory even though it's changed on disk - the classic 'why didn't my change take effect' trap.",
        "content": '# Install (if missing):\n# Part of systemd, nothing to install\n\nsudo systemctl daemon-reload && sudo systemctl restart <service>\n',
    },
    {
        "name": 'systemctl list-timers',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Overview of scheduled systemd timers (next/last run)',
        "long_description": 'The modern alternative to cron - list-timers --all shows inactive ones too, with the exact time of the next/last run.',
        "content": '# Install (if missing):\n# Part of systemd, nothing to install\n\nsystemctl list-timers --all   # including inactive ones, with next/last run times\n',
    },
    {
        "name": 'systemctl status / is-active',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'systemd unit status including recent logs',
        "long_description": "The first command to run for 'service isn't responding' - status shows PID, uptime and the last few log lines at once. is-active returns just yes/no, handy in scripts.",
        "content": '# Install (if missing):\n# Part of systemd, preinstalled on most modern Linux distros\n\nsystemctl status <service>     # status, recent logs, PID\nsystemctl is-active <service>   # yes/no only, script-friendly\n',
    },
    {
        "name": 'tar',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Create/extract compressed archives (.tar.gz)',
        "long_description": "c=create, x=extract, t=list, z=gzip, v=verbose, f=file. -t is useful to check what's actually in a large archive before extracting it.",
        "content": '# Install (if missing):\n# Present on almost every system, nothing to install\n\ntar -czvf archive.tar.gz folder/   # create\ntar -xzvf archive.tar.gz            # extract\ntar -tzvf archive.tar.gz             # list contents without extracting\n',
    },
    {
        "name": 'TCPView',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Live GUI view of network connections with process names',
        "long_description": 'GUI equivalent of netstat/Get-NetTCPConnection, but with live color-highlighting of new/closed connections - faster to watch visually than re-running a command.',
        "content": '# Install (if missing):\n# winget install Microsoft.Sysinternals.TCPView\n\ntcpview.exe\n',
    },
    {
        "name": 'Test-NetConnection',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Test host/port reachability, replaces ping+telnet+tracert at once',
        "long_description": "One command instead of combining ping/telnet/tracert - returns both RTT and TCP handshake success, not just ICMP echo. Windows equivalent of Linux's 'nc -zv'.",
        "content": '# Install (if missing):\n# Part of the NetTCPIP module (Windows 8/Server 2012+), built in\n\nTest-NetConnection -ComputerName 192.168.1.10 -Port 443   # port reachability test (nc -zv / telnet equivalent)\nTest-NetConnection google.com -TraceRoute                  # with traceroute too\n',
    },
    {
        "name": 'tmutil',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Control Time Machine from the command line',
        "long_description": "Useful for automating backups or diagnosing why a Time Machine backup isn't running/is failing without opening the GUI.",
        "content": '# Install (if missing):\n# Built into macOS, nothing to install\n\ntmutil listbackups\ntmutil startbackup --auto\n',
    },
    {
        "name": 'tmux - session control',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Terminal multiplexer - a session survives disconnecting/closing the terminal',
        "long_description": "A long-running process (backup, build, watching logs) survives an SSH disconnect as long as it's running inside tmux. Ctrl+b d = detach, the terminal closes but the process keeps running.",
        "content": '# Install (if missing):\n# sudo apt install tmux   # brew install tmux (macOS)\n\ntmux new -s name      # new named session\ntmux attach -t name    # attach to an existing session\ntmux ls                 # list running sessions\n',
    },
    {
        "name": 'tmux copy mode',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Scroll terminal history and copy text inside tmux',
        "long_description": "Without this, tmux doesn't let you scroll up through history normally with the mouse/keyboard - copy mode enables it (including keyboard-only navigation via vim-style keys).",
        "content": '# Install (if missing):\n# sudo apt install tmux   # brew install tmux (macOS)\n\nCtrl+b [   # enter copy/scroll mode\nq          # exit copy mode\n',
    },
    {
        "name": 'tmux split panes',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Split a terminal window into multiple panes at once',
        "long_description": 'Watch logs in one pane and work in another without switching windows/tabs - especially useful over SSH on a headless server.',
        "content": '# Install (if missing):\n# sudo apt install tmux   # brew install tmux (macOS)\n\nCtrl+b %   # vertical split\nCtrl+b "   # horizontal split\nCtrl+b <arrow>   # switch between panes\n',
    },
    {
        "name": 'wmic (legacy)',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Older WMI CLI interface - still common in older scripts/environments',
        "long_description": 'Microsoft is gradually deprecating wmic in favor of Get-CimInstance, but it still shows up in a lot of older admin scripts and environments without PowerShell 7 - worth knowing how to read even though new scripts should prefer CIM cmdlets.',
        "content": '# Install (if missing):\n# Part of older Windows; removed from Windows 11 24H2 onward - install via Optional Features\n\nwmic process list brief                     # quick process list\nwmic logicaldisk get size,freespace,caption   # disk space via WMI\n',
    },
    {
        "name": 'zip / unzip',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Cross-platform archiving (works natively on Windows too)',
        "long_description": 'Unlike tar.gz, zip opens natively on Windows without extra software - the choice when the archive is going to someone without Linux/macOS.',
        "content": '# Install (if missing):\n# sudo apt install zip unzip\n\nzip -r archive.zip folder/\nunzip archive.zip -d dest/\n',
    },
]
