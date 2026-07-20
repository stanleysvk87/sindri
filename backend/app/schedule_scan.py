"""Best-effort cross-check between what the catalog SAYS a script's run
mode is (free-text field, entered by hand, never verified) and what's
actually scheduled on the machine it's tagged with -- crontab entries
and systemd timers' ExecStart lines.

Deliberately simple: one SSH round trip per machine, one combined text
dump, and purely textual matching (does the script's filename show up
anywhere in that dump) -- same "heuristic, not a scanner" spirit as
secret_scan.py. A hit doesn't prove the script is wired up correctly, a
miss doesn't prove it's broken -- it's a nudge to go look, exactly the
kind of drift that caused the real BudgetPilot duplicate-systemd-unit
finding this catalog audit turned up."""

from app.remote_exec import RemoteExecError, run_remote

_SCAN_SCRIPT = """
echo "===CRON==="
crontab -l 2>/dev/null
echo "===SYSTEM_TIMERS==="
for u in $(systemctl list-timers --all --no-legend 2>/dev/null | awk '{print $(NF-1)}'); do
  echo "--- $u ---"
  systemctl cat "$u" 2>/dev/null | grep -i '^ExecStart'
done
echo "===USER_TIMERS==="
for u in $(systemctl --user list-timers --all --no-legend 2>/dev/null | awk '{print $(NF-1)}'); do
  echo "--- $u (user) ---"
  systemctl --user cat "$u" 2>/dev/null | grep -i '^ExecStart'
done
true
"""


def scan_schedule(machine: dict) -> str:
    result = run_remote(machine, _SCAN_SCRIPT, None)
    if result["timed_out"]:
        raise RemoteExecError("Kontrola plánovania vypršala (timeout).")
    if result["exit_code"] not in (0, None):
        raise RemoteExecError(result["stderr"][:500] or "Kontrola plánovania zlyhala.")
    return result["stdout"]


def find_mismatches(scripts: list[dict], dump: str) -> list[dict]:
    mismatches = []
    for s in scripts:
        run_mode = (s["run_mode"] or "").lower()
        claims_scheduled = "cron" in run_mode or "systemd" in run_mode
        found_in_dump = s["name"] in dump
        if claims_scheduled and not found_in_dump:
            mismatches.append({"id": s["id"], "name": s["name"], "issue": "claimed_not_found"})
        elif not claims_scheduled and found_in_dump:
            mismatches.append({"id": s["id"], "name": s["name"], "issue": "found_not_claimed"})
    return mismatches
