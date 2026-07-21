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
        "short_description": 'Zobrazí VŠETKO čo sa spúšťa pri štarte systému',
        "long_description": "Services, scheduled tasks, registry Run keys, drivers, browser extensions - najkompletnejší pohľad na 'čo bežalo pri boote'. Klasický prvý krok pri malware cleanup.",
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.Autoruns\n\nautorunsc64.exe -a * -c   # CLI verzia, CSV výstup, vhodné do skriptu/auditu\n',
    },
    {
        "name": 'awk',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Rýchle spracovanie stĺpcových/tabuľkových dát',
        "long_description": "Kratšie a rýchlejšie než písať skript na jednoduché stĺpcové operácie - použité dnes napr. pri parsovaní 'ip neigh show' výstupu (awk '{print $5}' na MAC adresu).",
        "content": "# Install (ak chýba):\n# Súčasť coreutils/POSIX, vždy prítomné\n\nawk '{print $1, $3}' file.txt     # vytiahne 1. a 3. stĺpec\nawk -F: '{print $1}' /etc/passwd    # vlastný oddeľovač (:)\n",
    },
    {
        "name": 'crontab - klasické cron joby',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Zobrazenie naplánovaných cron úloh (užívateľské aj systémové)',
        "long_description": 'Skontroluje sa hneď po systemd timeroch, keďže staršie skripty (napr. ytupdate na opi) bežia cez klasický cron, nie systemd timer.',
        "content": '# Install (ak chýba):\n# sudo apt install cron   # na minimálnych/kontajnerových image niekedy chýba\n\ncrontab -l                       # vlastný crontab aktuálneho užívateľa\nsudo crontab -l -u <user>         # cudzí užívateľ\ncat /etc/cron.d/*                 # systémové cron entries\n',
    },
    {
        "name": 'curl + jq kombinácia',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Priame filtrovanie API odpovede bez ukladania medzivýsledku',
        "long_description": 'Reťazenie curl → jq v jednom pipe je rýchlejšie než sťahovať odpoveď do súboru a otvárať v editore - presný vzor použitý dnes pri overovaní Sindri API výsledkov.',
        "content": "# Install (ak chýba):\n# sudo apt install curl jq   # zvyčajne už predinštalované\n\ncurl -s https://api.example.com/users | jq '.[] | select(.active) | {id, name}'\n",
    },
    {
        "name": 'curl - autentifikácia',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Rôzne spôsoby autentifikácie pri API volaniach',
        "long_description": '-b/-c cookie jar presne to, čo sa použilo pri Sindri (login vráti session cookie, tá sa poslala pri ďalšom requeste).',
        "content": '# Install (ak chýba):\n# sudo apt install curl   # zvyčajne už predinštalované\n\ncurl -u user:pass https://api.example.com/                              # Basic auth\ncurl -H "Authorization: Bearer <token>" https://api.example.com/          # Bearer token\ncurl -b cookies.txt -c cookies.txt https://...                            # cookie persistence\n',
    },
    {
        "name": 'curl - POST/JSON requesty',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Odosielanie POST/JSON requestov z príkazového riadku',
        "long_description": 'Presne ten vzor, čo sa dnes celú session používal pri Sindri API volaniach (login, import/paste) - -d @súbor je čistejšie než dlhý inline JSON string.',
        "content": '# Install (ak chýba):\n# sudo apt install curl   # zvyčajne už predinštalované\n\ncurl -X POST https://api.example.com/endpoint -H "Content-Type: application/json" -d \'{"key":"value"}\'\ncurl -X POST ... -d @payload.json   # dáta zo súboru\n',
    },
    {
        "name": 'curl -v / -I',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'HTTP/TLS diagnostika priamo z príkazového riadku',
        "long_description": '-v ukáže celú komunikáciu vrátane TLS handshake (dobré pri cert problémoch), -I stiahne len response headers bez tela (rýchla kontrola stavu/redirectu).',
        "content": '# Install (ak chýba):\n# sudo apt install curl   # zvyčajne už predinštalované\n\ncurl -v https://example.com   # plná komunikácia vrátane TLS handshake\ncurl -I https://example.com    # len response headers\n',
    },
    {
        "name": 'df / du - diskový priestor',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Zistenie čo zaberá miesto na disku',
        "long_description": 'df -h pre celkový prehľad per mount, du -sh so sort -rh pre nájdenie konkrétnych veľkých adresárov - presne workflow z riešenia SSD-plné incidentov na opi.',
        "content": '# Install (ak chýba):\n# Súčasť coreutils, vždy prítomné\n\ndf -h                                # využitie diskov per mount\ndu -sh */ | sort -rh | head -20        # 20 najväčších adresárov v aktuálnom priečinku\n',
    },
    {
        "name": 'dig - DNS diagnostika',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Rýchle overenie DNS záznamov, aj proti konkrétnemu serveru',
        "long_description": '+short vynechá všetku réžiu okolo, @1.1.1.1 obíde lokálnu DNS cache (napr. Pi-hole) keď treba overiť čo vidí zvyšok internetu, nie čo má vyriešené doma.',
        "content": '# Install (ak chýba):\n# sudo apt install dnsutils   # Debian/Ubuntu; RHEL/Fedora: bind-utils\n\ndig +short example.com          # rýchla odpoveď bez extra hlavičiek\ndig @1.1.1.1 example.com          # test proti konkrétnemu DNS serveru\n',
    },
    {
        "name": 'diskutil',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Správa diskov a partícií - ekvivalent fdisk/lsblk',
        "long_description": 'list ukáže prehľad všetkých pripojených diskov vrátane APFS containers, info dá detail o konkrétnom zväzku (filesystem, veľkosť, encryption status).',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\ndiskutil list          # zoznam diskov a partícií\ndiskutil info disk0     # detail konkrétneho disku\n',
    },
    {
        "name": 'docker compose - základné workflow',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Rebuild, logy a stav služieb v compose stacku',
        "long_description": 'Denný chlieb pri práci na vlastných appkách (Foodcost, MidgardCMS, Heimdall...) - --build vynúti rebuild image pri zmene kódu, logs -f konkrétnej služby je presnejšie než sledovať celý stack naraz.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker compose up -d --build      # rebuild + reštart na pozadí\ndocker compose logs -f <service>   # logy konkrétnej služby v compose stacku\ndocker compose ps                  # stav všetkých služieb v stacku\n',
    },
    {
        "name": 'docker exec',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Vstup do bežiaceho kontajnera / spustenie príkazu vnútri',
        "long_description": 'Namiesto reštartu kontajnera s iným entrypointom vojdeš priamo dnu overiť súbory, env premenné, sieťovú konektivitu z pohľadu kontajnera.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker exec -it <container> /bin/sh   # interaktívny shell (alebo /bin/bash ak je k dispozícii)\ndocker exec <container> env            # výpis env premenných bez vstupu do shellu\n',
    },
    {
        "name": 'docker inspect',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Detailný JSON stav kontajnera (siete, mounty, health, restart count)',
        "long_description": 'Keď docker ps nestačí - inspect ukáže presný dôvod reštartov, IP v jednotlivých sieťach, mount body, health-check históriu. S jq sa dá vypítať presne to, čo treba.',
        "content": "# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker inspect <container> | jq '.[0].State'            # stav (running/health/restart count)\ndocker inspect <container> | jq '.[0].NetworkSettings'   # sieťové nastavenia (IP, porty)\n",
    },
    {
        "name": 'docker logs',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Sledovanie a filtrovanie logov kontajnera',
        "long_description": 'Základ debugovania - najčastejší prvý krok keď niečo v stacku nefunguje. -f pre live sledovanie, --since na obmedzenie objemu pri dlho bežiacich kontajneroch.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker logs -f --tail 100 <container>   # live sledovanie posledných 100 riadkov\ndocker logs --since 1h <container>       # len logy za poslednú hodinu\n',
    },
    {
        "name": 'docker network inspect',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Sieťová diagnostika medzi kontajnermi',
        "long_description": 'Keď dva kontajnery v tom istom compose stacku spolu nekomunikujú - over že sú na tej istej Docker sieti a skús ping priamo z jedného do druhého po service name.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker network inspect <network>                 # zoznam pripojených kontajnerov a ich IP v danej sieti\ndocker exec <container> ping <other_container>    # over konektivitu priamo z vnútra siete\n',
    },
    {
        "name": 'docker stats',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Live využitie CPU/RAM/siete per kontajner',
        "long_description": 'Rýchly spôsob nájsť kontajner čo žerie zdroje bez nutnosti nasadzovať plný monitoring (Beszel a pod.) - --no-stream pre jednorazový snapshot vhodný aj do skriptu.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker stats --no-stream   # jednorazový snapshot CPU/RAM/network per kontajner\n',
    },
    {
        "name": 'docker system prune / df',
        "tags": 'cheatsheet,docker',
        "run_mode": '',
        "short_description": 'Upratovanie nepoužívaných images/kontajnerov/volumes',
        "long_description": 'docker system df najprv ukáže koľko miesta sa reálne dá získať. prune -a --volumes je nezvratné (zmaže aj pomenované volumes bez bežiaceho kontajnera) - container prune je bezpečnejší podmnožinový krok.',
        "content": '# Install (ak chýba):\n# curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER   # macOS/Windows: Docker Desktop\n\ndocker system df                    # prehľad koľko miesta zaberajú images/containers/volumes\ndocker container prune               # len zastavené kontajnery, bezpečnejšie\ndocker system prune -a --volumes     # POZOR: zmaže všetko nepoužívané vrátane volumes\n',
    },
    {
        "name": 'dscl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Directory services - lokálni aj AD-pripojení používatelia/skupiny',
        "long_description": 'Nižšia úroveň než sysadminctl, dá sa čítať/meniť takmer čokoľvek v directory service databáze - mocný, ale ľahko sa dá pokaziť systémový účet neopatrným zápisom.',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\ndscl . -list /Users                        # zoznam lokálnych používateľov\ndscl . -read /Users/$(whoami) UniqueID       # UID konkrétneho užívateľa\n',
    },
    {
        "name": 'Enter-PSSession / Invoke-Command',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Vzdialená správa Windows strojov (WinRM), ekvivalent SSH',
        "long_description": 'PowerShell Remoting cez WinRM je Windows ekvivalent SSH pre vzdialenú administráciu - treba mať povolené (Enable-PSRemoting) na cieľovom stroji.',
        "content": '# Install (ak chýba):\n# Vstavané, ale treba povoliť na cieľovom stroji: Enable-PSRemoting -Force\n\nEnter-PSSession -ComputerName SERVER01                            # interaktívna vzdialená shell\nInvoke-Command -ComputerName SERVER01 -ScriptBlock { Get-Service } # jednorazový vzdialený príkaz\n',
    },
    {
        "name": 'ffmpeg - konverzia formátov',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Univerzálna konverzia audio/video formátov',
        "long_description": '-crf (Constant Rate Factor) kontroluje kvalitu/veľkosť pomeru - nižšie číslo = lepšia kvalita/väčší súbor, 23 je rozumný default. Relevantné pre Jellyfin media stack aj camera-ai-telegram spracovanie.',
        "content": '# Install (ak chýba):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i vstup.mov -c:v libx264 -crf 23 vystup.mp4\n',
    },
    {
        "name": 'ffmpeg - nahrávanie RTSP streamu',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Nahrávanie RTSP streamu do súboru bez straty kvality (copy mód)',
        "long_description": '-c copy skopíruje stream 1:1 bez re-encodingu (rýchle, žiadna strata kvality/CPU záťaž) - vhodné pri krátkodobom zaznamenaní dôkazu z kamery bez plného NVR setupu.',
        "content": '# Install (ak chýba):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i rtsp://192.168.1.13:554/stream -c copy -t 60 nahravka.mp4\n',
    },
    {
        "name": 'ffmpeg - screenshot z RTSP',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Extrakcia jedného snímku z RTSP kamera streamu',
        "long_description": 'Priamo relevantné pre IP kamery/go2rtc/ALPR prácu - rýchly spôsob overiť, že RTSP stream vôbec funguje a čo presne kamera vidí, bez nutnosti otvárať VLC/appku.',
        "content": '# Install (ak chýba):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffmpeg -i rtsp://192.168.1.13:554/stream -vframes 1 screenshot.jpg\n',
    },
    {
        "name": 'ffprobe',
        "tags": 'cheatsheet,ffmpeg',
        "run_mode": '',
        "short_description": 'Zistenie presných technických parametrov audio/video súboru',
        "long_description": 'Súčasť ffmpeg balíka - namiesto hádania z názvu súboru dá presné dáta (video kodek, framerate, audio kanály) v strojovo spracovateľnom JSON formáte.',
        "content": '# Install (ak chýba):\n# sudo apt install ffmpeg   # brew install ffmpeg (macOS)\n\nffprobe -v quiet -print_format json -show_format -show_streams video.mp4\n',
    },
    {
        "name": 'find',
        "tags": 'cheatsheet,find-xargs',
        "run_mode": '',
        "short_description": 'Vyhľadávanie súborov podľa mena/veku/veľkosti/typu',
        "long_description": "Oveľa presnejšie než ručné prehľadávanie ls - mtime/size filtre sú presne to, čo sa hodí pri hľadaní 'čo mi zaberá miesto' alebo 'staré zálohy na zmazanie'.",
        "content": '# Install (ak chýba):\n# Súčasť findutils, takmer vždy prítomné\n\nfind . -name "*.log" -mtime +7   # súbory staršie ako 7 dní\nfind . -type f -size +100M           # súbory väčšie ako 100MB\n',
    },
    {
        "name": 'find + xargs',
        "tags": 'cheatsheet,find-xargs',
        "run_mode": '',
        "short_description": 'Aplikovanie príkazu na všetky výsledky find naraz',
        "long_description": '-print0/-0 kombinácia je dôležitá bezpečnostná záležitosť - bez nej find+xargs zle spracuje súbory s medzerou v mene (rozdelí ich na dva argumenty). Bez toho hrozí, že rm zmaže niečo iné, než si čakal.',
        "content": '# Install (ak chýba):\n# Súčasť findutils, takmer vždy prítomné\n\nfind . -name "*.tmp" -print0 | xargs -0 rm   # bezpečné zmazanie\nfind . -name "*.log" | xargs grep -l "ERROR"   # hľadanie v obsahu naraz\n',
    },
    {
        "name": 'Get-ADUser / Get-ADComputer',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Dotazovanie Active Directory (RSAT/AD modul)',
        "long_description": 'Základ enterprise Windows administrácie - nájdenie neaktívnych účtov/počítačov je bežná bezpečnostná/hygienická kontrola v AD prostredí. Vyžaduje nainštalovaný AD PowerShell modul (RSAT).',
        "content": '# Install (ak chýba):\n# Install-WindowsFeature RSAT-AD-PowerShell   # server; na klient Windows 10/11: Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0\n\nGet-ADUser -Filter {Enabled -eq $false}                # zoznam deaktivovaných účtov\nGet-ADComputer -Filter * -Properties LastLogonDate       # posledné prihlásenie počítačov v doméne\n',
    },
    {
        "name": 'Get-ComputerInfo / systeminfo',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Rýchly prehľad hardvéru/OS verzie stroja',
        "long_description": 'Get-ComputerInfo je pomalší ale štruktúrovaný (dá sa filtrovať), systeminfo je rýchly bleskový textový výpis - dobré vedieť oba, podľa toho či potrebuješ rýchlosť alebo presné parsovanie.',
        "content": '# Install (ak chýba):\n# Súčasť Windows/PowerShellu, netreba inštalovať\n\nGet-ComputerInfo | Select WindowsProductName, OsHardwareAbstractionLayer, CsProcessors\nsysteminfo   # staršia, ale rýchlejšia cmd alternatíva s kompletným výpisom\n',
    },
    {
        "name": 'Get-Content -Tail -Wait',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Live sledovanie rastúceho log súboru (tail -f ekvivalent)',
        "long_description": "-Wait drží súbor otvorený a vypisuje nové riadky ako pribúdajú, presne ako Linuxový 'tail -f'.",
        "content": '# Install (ak chýba):\n# Súčasť PowerShellu, netreba inštalovať\n\nGet-Content C:\\logs\\app.log -Tail 20 -Wait\n',
    },
    {
        "name": 'Get-NetTCPConnection',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Zoznam počúvajúcich portov a asociovaných procesov',
        "long_description": "Modernejšia PowerShell náhrada netstat -ano - dá sa priamo prepojiť s Get-Process cez OwningProcess na zistenie, ktorý proces drží daný port. Windows ekvivalent 'ss -tulnp'.",
        "content": '# Install (ak chýba):\n# Súčasť modulu NetTCPIP, vstavané\n\nGet-NetTCPConnection -State Listen | Sort-Object LocalPort\n',
    },
    {
        "name": 'Get-Process / Stop-Process',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Správa procesov cez PowerShell - modernejšia náhrada tasklist/taskkill',
        "long_description": 'Get-Process vracia objekty (nie len text), takže sa dá priamo filtrovať/triediť/exportovať cez pipeline namiesto parsovania textu ako pri klasických cmd nástrojoch - kľúčový rozdiel PowerShell vs cmd.',
        "content": '# Install (ak chýba):\n# Súčasť PowerShellu (vstavané cmdlety), netreba inštalovať\n\nGet-Process | Sort-Object CPU -Descending | Select -First 10   # top 10 procesov podľa CPU\nStop-Process -Name notepad -Force                              # násilné ukončenie podľa mena\n',
    },
    {
        "name": 'Get-Service / Restart-Service',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Správa Windows služieb (ekvivalent systemctl)',
        "long_description": 'Priamy Windows ekvivalent systemctl status/restart. Where-Object filtruje objekty rovnako ako grep filtruje text, len nad štruktúrovanými dátami.',
        "content": '# Install (ak chýba):\n# Súčasť PowerShellu, netreba inštalovať\n\nGet-Service | Where-Object {$_.Status -eq "Running"}   # zoznam bežiacich služieb\nRestart-Service -Name Spooler -Force                      # reštart konkrétnej služby\n',
    },
    {
        "name": 'Get-WinEvent',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Windows Event Log - ekvivalent journalctl',
        "long_description": 'FilterHashtable je efektívnejší než filtrovanie po stiahnutí (server-side filter), dôležité na strojoch s veľkými logmi. Level 1=Critical, 2=Error, 3=Warning.',
        "content": "# Install (ak chýba):\n# Súčasť PowerShellu, netreba inštalovať\n\nGet-WinEvent -LogName System -MaxEvents 50                                    # posledných 50 systémových eventov\nGet-WinEvent -FilterHashtable @{LogName='Application'; Level=2} -MaxEvents 20  # len chyby (Level 2) z Application logu\n",
    },
    {
        "name": 'git bisect',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Binárne hľadanie commitu, ktorý zaviedol bug',
        "long_description": 'Namiesto ručného prechádzania histórie git sám ponúka commity na test (binárne delenie), kým sa nenájde presne ten jeden, čo bug zaviedol.',
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit bisect start && git bisect bad && git bisect good <hash>   # git potom sám ponúka commity na test\n',
    },
    {
        "name": 'git cherry-pick',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Prenesenie jedného konkrétneho commitu na iný branch',
        "long_description": 'Keď potrebuješ len jednu opravu z iného branchu bez toho, aby si merge-oval celú vetvu.',
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit cherry-pick <hash>   # aplikuje zmeny z iného commitu/branch na aktuálny branch\n',
    },
    {
        "name": 'git filter-branch (msg-filter)',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Prepis histórie commit messagí naprieč celým repom',
        "long_description": "Presne ten príkaz, čo sa použil pri čistení 'Co-Authored-By: Claude' trailerov zo Sindri a camera-ai-telegram repa pred verejným pushom. Vyžaduje force-push a overenie stromu pred/po cez HEAD^{tree}.",
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit filter-branch --msg-filter \'sed "/Co-Authored-By: Claude/d"\' -- --all\n',
    },
    {
        "name": 'git log - užitočné formáty',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Prehľadnejšie zobrazenie histórie a zmien konkrétneho súboru',
        "long_description": '--graph --all dá vizuálny prehľad vetvenia namiesto lineárneho zoznamu, -p na súbor ukáže presne kedy a ako sa daný súbor menil naprieč celou históriou.',
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit log --oneline --graph --all   # vizuálny prehľad vetvenia\ngit log -p -- <file>                # plná história zmien konkrétneho súboru\n',
    },
    {
        "name": 'git rebase -i',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Interaktívne prepisovanie histórie pred pushom',
        "long_description": "Squash/reword/reorder posledných N commitov do čistej histórie predtým, než sa pushne - najužitočnejšie pri feature branchi s veľa 'wip' commitmi.",
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit rebase -i HEAD~5   # posledných 5 commitov - squash/reword/reorder\n',
    },
    {
        "name": 'git reflog',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": "Záchrana 'stratených' commitov po zlom resete/rebase",
        "long_description": 'reflog pamätá KAŽDÝ pohyb HEAD, aj tie čo bežný git log už nevidí (po hard reset, force push, zrušenom rebase). Skoro vždy sa dá vrátiť späť, kým nezasiahne garbage collection.',
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit reflog                            # história VŠETKÝCH HEAD pohybov\ngit reset --hard <reflog-hash>          # návrat na stav pred nechceným rebase/reset\n',
    },
    {
        "name": 'git stash',
        "tags": 'cheatsheet,git',
        "run_mode": '',
        "short_description": 'Dočasné odloženie rozrobených zmien',
        "long_description": '-u zahrnie aj untracked súbory (default ich stash preskočí, čo je bežná pasca). Dobré keď treba rýchlo prepnúť branch bez commitnutia nedokončenej práce.',
        "content": '# Install (ak chýba):\n# sudo apt install git   # brew install git (macOS); winget install Git.Git (Windows)\n\ngit stash push -u -m "popis"   # -u = zahrň aj untracked súbory\ngit stash pop                   # vráti posledný stash a zmaže ho zo zoznamu\n',
    },
    {
        "name": 'gpupdate / gpresult',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Group Policy vynútenie a diagnostika',
        "long_description": "gpresult /R je kľúčový diagnostický nástroj keď 'policy by mala platiť, ale nefunguje' - ukáže presne ktoré GPO sa aplikovali a ktoré boli filtrované/blokované.",
        "content": '# Install (ak chýba):\n# Súčasť Windows (built-in cmd nástroje), netreba inštalovať\n\ngpupdate /force   # okamžité vynútenie group policy na lokálnom stroji\ngpresult /R        # aké policy sa reálne aplikovali a odkiaľ\n',
    },
    {
        "name": 'grep -P / ripgrep (rg)',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Vyhľadávanie vzorov v texte/kóde, ripgrep ako rýchlejšia alternatíva',
        "long_description": 'ripgrep je defaultne rýchlejší než grep (paralelizácia, smart defaults) a automaticky preskakuje .gitignore súbory (node_modules, .git) - bežná voľba v moderných dev nástrojoch.',
        "content": '# Install (ak chýba):\n# grep je vždy prítomný; ripgrep: sudo apt install ripgrep   # brew install ripgrep\n\ngrep -rn -P \'\\d{3}-\\d{4}\' .   # Perl-compatible regex\nrg "TODO" --type py             # rešpektuje .gitignore automaticky\n',
    },
    {
        "name": 'gzip / zcat',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Kompresia jednotlivých súborov, zcat na prehľadávanie bez rozbalenia',
        "long_description": 'Bežné pri rotovaných logoch (access.log.1.gz) - zcat/zgrep umožňujú hľadať priamo v komprimovanom súbore bez manuálneho rozbaľovania.',
        "content": '# Install (ak chýba):\n# Súčasť coreutils/gzip balíka, takmer vždy prítomné\n\ngzip velky_log.txt              # vytvorí .gz, zmaže originál\ngunzip velky_log.txt.gz           # rozbalí naspäť\nzcat velky_log.txt.gz | grep "error"   # hľadanie bez rozbaľovania\n',
    },
    {
        "name": 'Handle',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Zistí, ktorý proces drží otvorený konkrétny súbor',
        "long_description": "Priama odpoveď na 'súbor je používaný iným procesom' hlášku Windows Exploreru - namiesto hádania presne ukáže PID a názov procesu.",
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.Handle\n\nhandle64.exe file.txt   # nájde proces, ktorý drží daný súbor otvorený\n',
    },
    {
        "name": 'Homebrew (brew)',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'De-facto štandardný balíčkovací systém pre macOS',
        "long_description": 'macOS nemá vstavaný package manager ako apt/pacman - brew je komunitný štandard, ktorý to rieši. --versions ukáže presné nainštalované verzie, užitočné pri debugovaní kompatibility.',
        "content": '# Install (ak chýba):\n# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n\nbrew list --versions\nbrew update && brew upgrade\n',
    },
    {
        "name": 'httpie',
        "tags": 'cheatsheet,api-tools',
        "run_mode": '',
        "short_description": 'Čitateľnejšia/rýchlejšia alternatíva ku curl pre API testovanie',
        "long_description": 'Automaticky formátuje JSON (farebne, odsadené), netreba -H Content-Type ani úvodzovky okolo JSON - rýchlejšie na interaktívne testovanie, curl je univerzálnejší/skriptovateľnejší.',
        "content": '# Install (ak chýba):\n# sudo apt install httpie   # alebo: pip install httpie\n\nhttp POST api.example.com/endpoint key=value\nhttp GET api.example.com/users Authorization:"Bearer token"\n',
    },
    {
        "name": 'ip route / ip addr',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Routing a IP diagnostika na lokálnom stroji',
        "long_description": 'ip route get ukáže presne akým rozhraním/cestou by paket odišiel k danému cieľu bez toho, aby sa reálne poslal - užitočné pri strojoch s viacerými sieťami (napr. Docker bridge siete na opi/victus).',
        "content": '# Install (ak chýba):\n# Súčasť iproute2, predinštalované na väčšine Linux distro\n\nip route get 8.8.8.8   # akou cestou/rozhraním by paket odišiel k danému cieľu\nip addr show             # aktuálne IP adresy na všetkých rozhraniach\n',
    },
    {
        "name": 'journalctl - logy služby',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Filtrovanie systémových/service logov cez journald',
        "long_description": '-u obmedzí na konkrétnu jednotku, -p err -b len chyby od posledného bootu - užitočné presne pri tom type debugovania, aké sa dnes riešilo pri MidgardOps observability medzere.',
        "content": '# Install (ak chýba):\n# Súčasť systemd, netreba inštalovať\n\njournalctl -u <service> -f                  # live sledovanie logu konkrétnej služby\njournalctl -u <service> --since "1 hour ago"  # logy za poslednú hodinu\njournalctl -p err -b                          # len chyby od posledného bootu\n',
    },
    {
        "name": 'journalctl --vacuum',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Správa veľkosti journald logov',
        "long_description": 'Keď journal sám osebe zaberie prekvapivo veľa miesta (bežné na strojoch s veľa kontajnermi/službami) - vacuum-time zmaže staré záznamy bez zásahu do konfigurácie retention policy.',
        "content": '# Install (ak chýba):\n# Súčasť systemd, netreba inštalovať\n\njournalctl --disk-usage              # koľko miesta zaberá journal\nsudo journalctl --vacuum-time=7d       # zmaže logy staršie ako 7 dní\n',
    },
    {
        "name": 'jq',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Parsovanie/filtrovanie JSON z príkazového riadku',
        "long_description": 'Bez jq by sa JSON výstup z API/logov musel parsovať cez grep/sed s vysokým rizikom chyby - jq rozumie štruktúre a dá sa reťaziť ako bežný Unix pipe nástroj. Presne to sa dnes používalo pri Sindri API volaniach.',
        "content": "# Install (ak chýba):\n# sudo apt install jq   # brew install jq (macOS)\n\ncurl -s https://api.example.com/data | jq '.items[] | select(.active==true) | .name'\njq -r '.[0].id' file.json   # raw výstup bez úvodzoviek\n",
    },
    {
        "name": 'launchctl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Správa launchd služieb - macOS ekvivalent systemctl',
        "long_description": 'launchd je macOS init/service manager. load/unload štartuje/zastavuje LaunchAgents (per-user) a LaunchDaemons (system-wide) definované v .plist súboroch.',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\nlaunchctl list | grep <name>                          # zoznam bežiacich launchd jobov\nlaunchctl load/unload ~/Library/LaunchAgents/x.plist   # načítanie/vypnutie konkrétneho agenta\n',
    },
    {
        "name": 'log show',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Unified logging systém - macOS ekvivalent journalctl',
        "long_description": 'Predicate syntax umožňuje presné filtrovanie bez nutnosti grepovať textový výstup - podobný koncept ako journalctl FilterHashtable na Windows.',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\nlog show --predicate \'eventMessage contains "error"\' --last 1h\n',
    },
    {
        "name": 'mtr - kontinuálny traceroute',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Cesta paketov k cieľu so stratovosťou per hop, live',
        "long_description": 'Lepšie než klasický traceroute - beží kontinuálne a ukazuje % stratených paketov na každom hope, takže sa dá presne identifikovať kde v ceste vzniká problém.',
        "content": '# Install (ak chýba):\n# sudo apt install mtr\n\nmtr example.com   # live/kontinuálny traceroute s stratovosťou per hop\n',
    },
    {
        "name": 'nc -zv - test portu',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Rýchle overenie že port je otvorený/dosiahnuteľný',
        "long_description": 'Najjednoduchší možný test konektivity bez potreby plného nmap scanu - dobré keď vieš presne aký jeden port chceš overiť.',
        "content": '# Install (ak chýba):\n# sudo apt install netcat-openbsd\n\nnc -zv 192.168.1.10 443   # over že port je otvorený/dosiahnuteľný\n',
    },
    {
        "name": 'openssl s_client',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Overenie TLS certifikátu a jeho reťaze priamo z CLI',
        "long_description": 'Bez otvárania prehliadača over expiráciu, certificate chain a SNI správanie servera - užitočné pri Caddy/Cloudflare cert debugovaní.',
        "content": '# Install (ak chýba):\n# sudo apt install openssl   # zvyčajne už predinštalované\n\nopenssl s_client -connect example.com:443 -servername example.com\n',
    },
    {
        "name": 'pg_dump / pg_restore',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Záloha a obnova Postgres databázy',
        "long_description": 'Priamo relevantné pre MidgardCMS (Postgres backend) - pravidelný pg_dump pred rizikovými zmenami schémy je lacná poistka proti nezvratnej chybe.',
        "content": '# Install (ak chýba):\n# sudo apt install postgresql-client\n\npg_dump -U user dbname > zaloha.sql   # záloha do SQL súboru\npsql -U user dbname < zaloha.sql        # obnova zo zálohy\n',
    },
    {
        "name": 'pip freeze / requirements.txt',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Reprodukovateľné závislosti - presne rovnaké verzie na inom stroji',
        "long_description": "Bez requirements.txt sa 'funguje mi to lokálne' problém stane bežným - freeze zachytí presné verzie vrátane tranzitívnych závislostí.",
        "content": '# Install (ak chýba):\n# pip je zvyčajne súčasťou Python inštalácie; ak chýba: sudo apt install python3-pip\n\npip freeze > requirements.txt       # export presných verzií\npip install -r requirements.txt      # inštalácia z exportu\n',
    },
    {
        "name": 'pipx',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Inštalácia Python CLI nástrojov bez znečistenia globálneho Python',
        "long_description": "Na rozdiel od 'pip install --user' pipx dá každému nástroju vlastné izolované prostredie, takže sa navzájom nepobijú závislosťami, no príkaz je aj tak dostupný globálne v PATH.",
        "content": '# Install (ak chýba):\n# sudo apt install pipx   # alebo: python3 -m pip install --user pipx\n\npipx install httpie   # izolovaný venv, dostupné globálne\n',
    },
    {
        "name": 'pmset',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Správa napájania a spánku',
        "long_description": '-g ukáže aktuálne power nastavenia (sleep timery, displaysleep atď), časté použitie je aj zabránenie spánku počas dlho bežiaceho procesu.',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\npmset -g                # aktuálne power nastavenia\nsudo pmset sleepnow      # okamžité uspatie\n',
    },
    {
        "name": 'Process Explorer',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": "'Task Manager na steroidoch' - vidí handles, DLL, farebne označuje procesy",
        "long_description": "Nie je to 'hacking tool' - bezpečne ho môže spúšťať aj DBA/dev bez obáv. Portable exe, netreba inštaláciu. Ukáže presne aké handles/DLL má proces otvorené, čo je pri Task Manageri neviditeľné.",
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.ProcessExplorer   # alebo ZIP z learn.microsoft.com/sysinternals\n\nprocexp64.exe   # spustí GUI, portable exe, netreba inštaláciu\n',
    },
    {
        "name": 'Process Monitor (procmon)',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Live log všetkých file/registry/process/network eventov',
        "long_description": "Kľúčový nástroj pri 'prečo appka padá / nevie čítať súbor' - vidíš presne ktorý súbor/registry kľúč appka skúsila otvoriť a či to zlyhalo (Access Denied, Not Found...).",
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.ProcessMonitor\n\nprocmon.exe /AcceptEula /Quiet /Minimized   # tichý štart, filtre sa nastavujú v GUI\n',
    },
    {
        "name": 'psql',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Interaktívna práca s Postgres databázou (napr. MidgardCMS)',
        "long_description": 'Backslash príkazy (\\dt, \\d, \\l) sú psql-špecifické skratky - rýchlejšie než písať plný SQL SELECT * FROM information_schema.',
        "content": '# Install (ak chýba):\n# sudo apt install postgresql-client\n\npsql -U user -d dbname -h localhost   # pripojenie\n\\dt                                     # zoznam tabuliek\n\\d nazov_tabulky                          # detail štruktúry\n',
    },
    {
        "name": 'python venv',
        "tags": 'cheatsheet,python',
        "run_mode": '',
        "short_description": 'Izolácia Python závislostí per projekt, zabráni konfliktom verzií',
        "long_description": 'Bez venv by sa všetky pip install balíčky inštalovali globálne, čo pri viacerých projektoch rýchlo vedie ku konfliktom verzií. Každý projekt by mal mať vlastné .venv.',
        "content": '# Install (ak chýba):\n# sudo apt install python3-venv   # modul venv nie je vždy súčasťou base python3 balíka na Debian/Ubuntu\n\npython3 -m venv .venv          # vytvorenie virtuálneho prostredia\nsource .venv/bin/activate        # aktivácia (Linux/macOS)\ndeactivate                        # deaktivácia\n',
    },
    {
        "name": 'robocopy',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Robustné kopírovanie/synchronizácia súborov, nahrádza xcopy',
        "long_description": '/MIR zrkadlí (zmaže v cieli čo chýba v zdroji, pozor pri prvom použití), vstavané retry pri sieťových výpadkoch - bežný nástroj pre zálohy/migrácie na Windows serveroch.',
        "content": '# Install (ak chýba):\n# Súčasť Windows od Vista/Server 2008, vstavané\n\nrobocopy C:\\zdroj D:\\ciel /MIR /LOG:copy.log\n',
    },
    {
        "name": 'rsync',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Efektívna synchronizácia súborov - prenáša len zmeny',
        "long_description": 'Na rozdiel od cp/scp prenáša len rozdiely (delta), takže opakovaná synchronizácia veľkého priečinka je rádovo rýchlejšia. Základ takmer každého backup skriptu.',
        "content": '# Install (ak chýba):\n# sudo apt install rsync   # brew install rsync (macOS má staršiu verziu predinštalovanú)\n\nrsync -avz --progress zdroj/ ciel/            # -a=archive, -z=kompresia\nrsync -avz -e ssh zdroj/ user@host:/ciel/       # cez SSH na vzdialený stroj\n',
    },
    {
        "name": 'scp / rsync cez SSH',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Prenos súborov cez SSH - scp pre jednoduché prípady, rsync pre efektívnejší',
        "long_description": 'scp je jednoduchšie na zapamätanie pre jeden súbor, ale rsync je vždy lepšia voľba pri opakovanom prenose/veľkých priečinkoch vďaka delta prenosu.',
        "content": '# Install (ak chýba):\n# sudo apt install openssh-client rsync\n\nscp subor.txt user@host:/cesta/\nrsync -avz -e ssh priecinok/ user@host:/cesta/\n',
    },
    {
        "name": 'screen',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Staršia alternatíva k tmuxu, stále bežná na starších/minimálnych systémoch',
        "long_description": 'Rovnaký účel ako tmux (session persistence), ale staršie a menej flexibilné pri split panes. Dobré vedieť, lebo na niektorých strojoch je jediné čo je predinštalované.',
        "content": '# Install (ak chýba):\n# sudo apt install screen   # brew install screen (macOS)\n\nscreen -S nazov   # nová session\nscreen -r nazov    # pripojenie\nCtrl+a d            # detach\n',
    },
    {
        "name": 'sed',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Hromadné vyhľadaj-a-nahraď v texte/súboroch',
        "long_description": "Presne ten nástroj, čo sa použil pri čistení 'Co-Authored-By: Claude' trailerov z git histórie (cez msg-filter). -i bez zálohy je nezvratné, opatrne.",
        "content": "# Install (ak chýba):\n# Súčasť coreutils/POSIX, vždy prítomné\n\nsed 's/starý/nový/g' file.txt      # výstup na stdout\nsed -i 's/starý/nový/g' file.txt     # -i priamo prepíše súbor\n",
    },
    {
        "name": 'Sophia Script',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Komunitná PowerShell zbierka na privacy/debloat/tweaks Windows 10/11',
        "long_description": 'Modulárny skript (nie jeden príkaz) na vypnutie telemetrie, odstránenie preinštalovaných appiek, tweaky UI a výkonu - populárny medzi power-users aj adminmi spravujúcimi vlastné stroje. Treba si prečítať čo presne robí pred spustením, niektoré zmeny sú dosť invazívne.',
        "content": '# Install (ak chýba):\n# git clone https://github.com/farag2/Sophia-Script-for-Windows   # spúšťať ako .ps1 modul, treba Set-ExecutionPolicy RemoteSigned\n\n# GitHub: farag2/Sophia-Script-for-Windows\nImport-Module .\\Sophia.psm1\nDisableTelemetry\n',
    },
    {
        "name": 'sort / uniq / wc',
        "tags": 'cheatsheet,text-processing',
        "run_mode": '',
        "short_description": 'Počítanie výskytov, deduplikácia, základná log analytika',
        "long_description": "sort|uniq -c|sort -rn je jeden z najužitočnejších Unix 'pipeline' vzorov vôbec - funguje na hocičom (IP adresy v logu, chybové hlášky, HTTP status kódy) a dá presnú frekvenčnú tabuľku bez písania skriptu.",
        "content": '# Install (ak chýba):\n# Súčasť coreutils, vždy prítomné\n\nsort file.txt | uniq -c | sort -rn | head -10   # 10 najčastejších riadkov\nwc -l file.txt                                   # počet riadkov\n',
    },
    {
        "name": 'spctl / codesign',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Gatekeeper a overenie code-signing appiek - bezpečnostne relevantné',
        "long_description": 'Overí, či appka prejde Gatekeeperom (spctl) a detail jej code-signing certifikátu (codesign) - dôležité pri posudzovaní dôveryhodnosti nepodpísaného/tretej-strany softvéru.',
        "content": '# Install (ak chýba):\n# Súčasť macOS (codesign potrebuje Xcode Command Line Tools): xcode-select --install\n\nspctl --assess --verbose /Applications/App.app     # over či appka prejde Gatekeeperom\ncodesign -dv --verbose=4 /Applications/App.app       # detail code signing certifikátu\n',
    },
    {
        "name": 'sqlite3 .backup',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Bezpečná záloha SQLite databázy počas aktívneho používania appky',
        "long_description": "Obyčajné 'cp database.db zaloha.db' môže pri súbežnom zápise vytvoriť poškodenú kópiu (polovičný write) - .backup príkaz to rieši korektne cez SQLite vlastný backup API.",
        "content": '# Install (ak chýba):\n# sudo apt install sqlite3\n\nsqlite3 database.db ".backup zaloha.db"\n',
    },
    {
        "name": 'sqlite3 CLI',
        "tags": 'cheatsheet,database',
        "run_mode": '',
        "short_description": 'Priama práca s SQLite databázovými súbormi (Foodcost, BudgetPilot)',
        "long_description": 'SQLite nemá server/proces - databáza je jeden súbor, takže sa dá priamo dotazovať/zálohovať kopírovaním súboru (za predpokladu, že nič naň práve nepíše).',
        "content": '# Install (ak chýba):\n# sudo apt install sqlite3\n\nsqlite3 database.db "SELECT * FROM users LIMIT 5;"   # jednoriadkový dotaz\nsqlite3 database.db ".tables"                          # zoznam tabuliek\n',
    },
    {
        "name": 'ss - počúvajúce porty',
        "tags": 'cheatsheet,network-diag',
        "run_mode": '',
        "short_description": 'Moderná alternatíva k netstat na zobrazenie otvorených portov',
        "long_description": '-tulnp = TCP+UDP, listening, numeric, s PID/process menom (root potrebný na zobrazenie PID). Presne toto by ukázalo čo beží na portoch nájdených pri dnešnom IoT scane, keby to boli vlastné stroje.',
        "content": '# Install (ak chýba):\n# Súčasť iproute2, predinštalované na väčšine Linux distro\n\nss -tulnp   # všetky počúvajúce TCP/UDP porty + proces\n',
    },
    {
        "name": 'SSH ControlMaster (multiplexing)',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Zdieľanie jedného TCP spojenia naprieč viacerými SSH príkazmi k tomu istému hostu',
        "long_description": 'Druhé a ďalšie SSH pripojenie k tomu istému hostu je takmer okamžité (žiadny nový TCP handshake/auth) - výrazne to zrýchli skripty, čo robia veľa SSH volaní za sebou (presne ako dnešná Sindri registrácia cez viacero SSH príkazov).',
        "content": '# Install (ak chýba):\n# sudo apt install openssh-client   # zvyčajne už predinštalované\n\n# v ~/.ssh/config:\nHost *\n    ControlMaster auto\n    ControlPath ~/.ssh/sockets/%r@%h-%p\n    ControlPersist 10m\n',
    },
    {
        "name": 'SSH port forwarding',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Tunelovanie portov cez SSH bez potreby VPN',
        "long_description": '-L je užitočné keď chceš z lokálneho prehliadača pristúpiť na službu čo počúva len na localhost vzdialeného servera (napr. interné admin UI). -R naopak sprístupní tvoju lokálnu službu vzdialenému stroju.',
        "content": '# Install (ak chýba):\n# sudo apt install openssh-client   # zvyčajne už predinštalované\n\nssh -L 8080:localhost:80 user@host    # lokálny 8080 -> vzdialený 80\nssh -R 9000:localhost:3000 user@host   # opačný smer\n',
    },
    {
        "name": 'ssh-agent / ssh-add',
        "tags": 'cheatsheet,ssh',
        "run_mode": '',
        "short_description": 'Jednorazové zadanie passphrase namiesto pri každom SSH spojení',
        "long_description": 'Bez agenta sa pri kľúči chránenom passphrase pýta heslo pri každom jednom SSH pripojení - agent si ho podrží v pamäti pre celú session.',
        "content": '# Install (ak chýba):\n# sudo apt install openssh-client   # zvyčajne už predinštalované; Windows: Settings > Optional Features > OpenSSH Client\n\neval $(ssh-agent)              # spustenie agenta\nssh-add ~/.ssh/id_ed25519       # pridanie kľúča\n',
    },
    {
        "name": 'sysadminctl',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Modernejšia, bezpečnejšia správa používateľských účtov',
        "long_description": 'Od macOS 10.13 odporúčaný nástroj namiesto priamej manipulácie cez dscl pre bežné operácie (vytvorenie účtu, zmena hesla, SecureToken status).',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\nsysadminctl -deleteUser username\n',
    },
    {
        "name": 'Sysmon',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Pokročilé systémové logovanie - základ DIY threat huntingu na Windows',
        "long_description": 'Loguje oveľa detailnejšie než default Windows Event Log (process creation s celým command line, network connections, file creates) priamo do Event Logu, odkiaľ sa dá zbierať cez SIEM. Bežne prvá vec, ktorú security tímy nasadzujú na Windows endpointy - dobrý štart je verejný SwiftOnSecurity config.',
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.Sysmon   # + community config, napr. github.com/SwiftOnSecurity/sysmon-config\n\nsysmon64.exe -i sysmonconfig.xml   # inštalácia ako služba s konfiguráciou\n',
    },
    {
        "name": 'systemctl daemon-reload',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Nutný krok po každej úprave .service súboru',
        "long_description": "Bez daemon-reload systemd naďalej používa starú verziu unit súboru v pamäti aj keď je na disku už zmenený - klasická 'prečo sa moja zmena neprejavila' pasca.",
        "content": '# Install (ak chýba):\n# Súčasť systemd, netreba inštalovať\n\nsudo systemctl daemon-reload && sudo systemctl restart <service>\n',
    },
    {
        "name": 'systemctl list-timers',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Prehľad naplánovaných systemd timerov (next/last run)',
        "long_description": 'Modernejšia alternatíva k cronu - list-timers --all ukáže aj neaktívne, s presným časom ďalšieho/posledného behu. Priamo nadväzuje na dnešnú MidgardOps cron/scheduler visibility prácu.',
        "content": '# Install (ak chýba):\n# Súčasť systemd, netreba inštalovať\n\nsystemctl list-timers --all   # vrátane neaktívnych, s next/last run časmi\n',
    },
    {
        "name": 'systemctl status / is-active',
        "tags": 'cheatsheet,systemd',
        "run_mode": '',
        "short_description": 'Stav systemd služby vrátane posledných logov',
        "long_description": "Prvý príkaz pri 'služba nereaguje' - status ukáže PID, uptime a poslednýchpár riadkov logu naraz. is-active vracia len áno/nie, hodí sa do skriptov/health-checkov.",
        "content": '# Install (ak chýba):\n# Súčasť systemd, predinštalované na väčšine moderných Linux distro\n\nsystemctl status <service>     # stav, posledné logy, PID\nsystemctl is-active <service>   # len áno/nie, vhodné do skriptov\n',
    },
    {
        "name": 'tar',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Vytvorenie/rozbalenie komprimovaných archívov (.tar.gz)',
        "long_description": 'c=create, x=extract, t=list, z=gzip, v=verbose, f=súbor. -t je užitočné pred rozbalením veľkého archívu overiť čo v ňom vôbec je.',
        "content": '# Install (ak chýba):\n# Súčasť takmer každého systému, netreba inštalovať\n\ntar -czvf archiv.tar.gz priecinok/   # vytvorenie\ntar -xzvf archiv.tar.gz                # rozbalenie\ntar -tzvf archiv.tar.gz                 # výpis obsahu bez rozbalenia\n',
    },
    {
        "name": 'TCPView',
        "tags": 'cheatsheet,sysinternals,windows',
        "run_mode": '',
        "short_description": 'Live GUI zobrazenie sieťových spojení s menami procesov',
        "long_description": 'GUI ekvivalent netstat/Get-NetTCPConnection, ale s live farebným zvýrazňovaním nových/zatvorených spojení - rýchlejšie na vizuálne sledovanie než opakované spúšťanie príkazu.',
        "content": '# Install (ak chýba):\n# winget install Microsoft.Sysinternals.TCPView\n\ntcpview.exe\n',
    },
    {
        "name": 'Test-NetConnection',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Test dostupnosti hosta/portu, nahrádza ping+telnet+tracert naraz',
        "long_description": "Jeden príkaz namiesto kombinácie ping/telnet/tracert - vráti aj RTT aj úspešnosť TCP handshake, nie len ICMP echo. Windows ekvivalent 'nc -zv' z Linux cheatsheetu.",
        "content": '# Install (ak chýba):\n# Súčasť modulu NetTCPIP (Windows 8/Server 2012+), vstavané\n\nTest-NetConnection -ComputerName 192.168.1.10 -Port 443   # ekvivalent nc -zv / telnet test portu\nTest-NetConnection google.com -TraceRoute                  # aj s traceroute\n',
    },
    {
        "name": 'tmutil',
        "tags": 'cheatsheet,macos',
        "run_mode": '',
        "short_description": 'Time Machine ovládanie z príkazového riadku',
        "long_description": 'Užitočné pri automatizácii záloh alebo diagnostike prečo Time Machine backup nebeží/zlyháva bez nutnosti otvárať GUI.',
        "content": '# Install (ak chýba):\n# Súčasť macOS, netreba inštalovať\n\ntmutil listbackups\ntmutil startbackup --auto\n',
    },
    {
        "name": 'tmux - session ovládanie',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Terminálový multiplexer - session prežije odpojenie/zatvorenie terminálu',
        "long_description": 'Dlho bežiaci proces (backup, build, sledovanie logov) prežije zatvorenie SSH spojenia, kým beží v tmuxe. Ctrl+b d = detach, terminál sa zavrie ale proces beží ďalej.',
        "content": '# Install (ak chýba):\n# sudo apt install tmux   # brew install tmux (macOS)\n\ntmux new -s nazov      # nová pomenovaná session\ntmux attach -t nazov    # pripojenie k existujúcej session\ntmux ls                  # zoznam bežiacich session\n',
    },
    {
        "name": 'tmux copy mode',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Scrollovanie histórie terminálu a kopírovanie textu v tmuxe',
        "long_description": 'Bez toho sa v tmuxe nedá myšou/klávesnicou normálne scrollovať hore v histórii - copy mode to sprístupní (aj keyboard-only navigácia cez vim-style klávesy).',
        "content": '# Install (ak chýba):\n# sudo apt install tmux   # brew install tmux (macOS)\n\nCtrl+b [   # vstup do copy/scroll módu\nq          # výstup z copy módu\n',
    },
    {
        "name": 'tmux split panes',
        "tags": 'cheatsheet,tmux',
        "run_mode": '',
        "short_description": 'Rozdelenie terminálového okna na viac panelov naraz',
        "long_description": 'Sledovanie logov v jednom paneli a práca v druhom bez prepínania okien/tabov - obzvlášť užitočné cez SSH na headless server.',
        "content": '# Install (ak chýba):\n# sudo apt install tmux   # brew install tmux (macOS)\n\nCtrl+b %   # vertikálny split\nCtrl+b "   # horizontálny split\nCtrl+b <šípka>   # prepínanie medzi panelmi\n',
    },
    {
        "name": 'wmic (legacy)',
        "tags": 'cheatsheet,windows',
        "run_mode": '',
        "short_description": 'Staršie WMI CLI rozhranie - stále bežné v starších skriptoch/prostrediach',
        "long_description": 'Microsoft wmic postupne deprecuje v prospech Get-CimInstance, ale stále sa vyskytuje v mnohých starších admin skriptoch a prostrediach bez PowerShell 7 - užitočné vedieť prečítať aj keď nové skripty už radšej používajú CIM cmdlets.',
        "content": '# Install (ak chýba):\n# Súčasť staršieho Windows; od Windows 11 24H2 je WMIC odstránené - doinštalovať cez Optional Features\n\nwmic process list brief                     # rýchly zoznam procesov\nwmic logicaldisk get size,freespace,caption   # diskový priestor cez WMI\n',
    },
    {
        "name": 'zip / unzip',
        "tags": 'cheatsheet,archiving',
        "run_mode": '',
        "short_description": 'Cross-platform archivácia (funguje aj natívne na Windows)',
        "long_description": 'Na rozdiel od tar.gz vie zip natívne otvoriť aj Windows bez extra softvéru - voľba keď archív pôjde niekomu bez Linux/macOS.',
        "content": '# Install (ak chýba):\n# sudo apt install zip unzip\n\nzip -r archiv.zip priecinok/\nunzip archiv.zip -d ciel/\n',
    },
]
