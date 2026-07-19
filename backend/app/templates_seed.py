"""Built-in starter library: ~25-30 generic, distro-agnostic Linux admin
scripts. Ships with the app so a fresh install is useful immediately,
not an empty shell -- and deliberately contains nothing opi/victus
specific (no hardcoded IPs, no /mnt/storage/data paths), so the app
itself stays portable to any Linux host. Seeded idempotently on startup
(see seed_templates() in db.py) -- matched by name, never overwrites a
row a user has edited.
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
]
