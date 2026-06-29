#!/opt/homebrew/bin/python3
"""
claude-sessions.py: persist & restore Claude Code sessions across tmux reboots.

Sits on top of tmux-resurrect / tmux-continuum (which already persist the
window/pane/layout/cwd tree). This layer adds the one thing resurrect can't:
re-attaching each restored pane to its exact Claude Code conversation.

Subcommands
  snapshot : detect every tmux pane running Claude Code, resolve its exact
             session id, and write a manifest. Wire to the resurrect
             @resurrect-hook-post-save-all hook so it runs in lockstep with
             every resurrect/continuum save (identical session/window/pane keys).
  restore  : read the latest manifest and, for each saved Claude pane that came
             back as a bare shell, inject `claude --resume <id>`. Wire to
             @resurrect-hook-post-restore-all so it runs automatically after
             continuum rebuilds the layout on boot. Staggered to avoid a
             thundering herd of simultaneous transcript loads at login.
  list     : print the current live detection (for testing / sanity).

Detection is exact, not heuristic. Every Claude process injects
CLAUDE_CODE_SESSION_ID into the environment of its children (MCP servers, Bash
tool shells). Those children often have no controlling tty, so we climb the
ppid chain from any env-bearing process to its `claude` ancestor, read that
ancestor's tty, and join to `tmux list-panes` by tty. This disambiguates
multiple Claude panes sharing one cwd, which a newest-jsonl-by-mtime heuristic
cannot (it collapses them all to the single most-recently-written session).
"""
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

TMUX = shutil.which("tmux") or "/opt/homebrew/bin/tmux"
HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".config", "tmux", "claude-sessions")
# Override the manifest path (e.g. for testing the restore path in isolation).
LATEST = os.environ.get("CLAUDE_SESSIONS_MANIFEST", os.path.join(STATE_DIR, "latest.json"))
PROJECTS = os.path.join(HOME, ".claude", "projects")
KEEP_HISTORY = 30  # timestamped manifests to retain
SETTLE_SECONDS = 1.0  # let resurrect-restored shells reach a prompt first
STAGGER_SECONDS = float(os.environ.get("CLAUDE_RESTORE_STAGGER", "0.4"))

UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+")  # tmux reports a Claude pane's command as its version
SHELLS = {"fish", "-fish", "bash", "-bash", "zsh", "-zsh", "sh", "-sh", "login"}


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def norm_tty(t: str) -> str:
    """Normalize a tty string to the bare device name used by `ps -o tty=` (e.g. ttys029)."""
    return t.replace("/dev/", "")


def munge(cwd: str) -> str:
    return cwd.replace("/", "-")


# --------------------------------------------------------------------------- #
# Live detection
# --------------------------------------------------------------------------- #
def all_procs() -> dict[str, tuple[str, str, str]]:
    """pid -> (ppid, tty, command-line)."""
    procs: dict[str, tuple[str, str, str]] = {}
    for line in run(["ps", "-A", "-o", "pid=", "-o", "ppid=", "-o", "tty=", "-o", "command="]).splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, tty, cmd = parts
        procs[pid] = (ppid, norm_tty(tty), cmd)
    return procs


def claude_masters(procs: dict[str, tuple[str, str, str]]) -> dict[str, dict]:
    """pid -> {tty, argv_id} for each top-level `claude` CLI process."""
    masters: dict[str, dict] = {}
    for pid, (_ppid, tty, cmd) in procs.items():
        c = cmd.strip()
        try:
            first = shlex.split(c)[0]
        except ValueError:
            first = c.split()[0] if c else ""
        if os.path.basename(first) != "claude":
            continue
        m = re.search(rf"--resume\s+({UUID_RE})", c)
        masters[pid] = {"tty": tty, "argv_id": m.group(1) if m else None}
    return masters


def env_session_ids() -> dict[str, str]:
    """pid -> session_id, for every process whose env carries CLAUDE_CODE_SESSION_ID.

    Uses the default `ps eww` format on purpose: BSD `ps` suppresses the env
    dump when a custom `-o` format is supplied.
    """
    out: dict[str, str] = {}
    for line in run(["ps", "eww", "-A"]).splitlines():
        m = re.search(rf"CLAUDE_CODE_SESSION_ID=({UUID_RE})", line)
        if not m:
            continue
        tok = line.split(None, 1)
        if tok and tok[0].isdigit():
            out[tok[0]] = m.group(1)
    return out


def tty_session_map(procs, masters, env) -> dict[str, tuple[str, str]]:
    """tty -> (session_id, method). Env evidence (exact, live) wins; argv id is the fallback."""
    def climb(pid: str) -> str | None:
        hops = 0
        while pid in procs and hops < 50:
            if pid in masters:
                return pid
            pid = procs[pid][0]
            hops += 1
        return None

    tty_sid: dict[str, tuple[str, str]] = {}
    # argv ids first (lower precedence) ...
    for _pid, info in masters.items():
        if info["argv_id"]:
            tty_sid[info["tty"]] = (info["argv_id"], "argv")
    # ... then overwrite with live env evidence (ground truth for the active session).
    for epid, sid in env.items():
        cpid = climb(epid)
        if cpid:
            tty_sid[masters[cpid]["tty"]] = (sid, "env")
    return tty_sid


def tmux_panes() -> list[dict]:
    fmt = "\t".join(
        "#{%s}" % f
        for f in (
            "session_name", "window_index", "window_name", "pane_index",
            "pane_id", "pane_tty", "pane_current_path", "pane_current_command", "pane_title",
        )
    )
    panes = []
    for line in run([TMUX, "list-panes", "-a", "-F", fmt]).splitlines():
        f = (line.split("\t") + [""] * 9)[:9]
        panes.append(dict(zip(
            ("session", "window_index", "window_name", "pane_index",
             "pane_id", "tty", "cwd", "command", "title"), f)))
    return panes


def detect() -> list[dict]:
    """Return one record per Claude pane: location, cwd, title, session_id, method."""
    procs = all_procs()
    masters = claude_masters(procs)
    tty_sid = tty_session_map(procs, masters, env_session_ids())

    records = []
    for p in tmux_panes():
        is_claude = bool(VERSION_RE.match(p["command"])) or p["command"] == "claude"
        if not is_claude:
            continue
        sid, method = tty_sid.get(norm_tty(p["tty"]), (None, "unresolved"))
        records.append({
            "session": p["session"],
            "window_index": p["window_index"],
            "window_name": p["window_name"],
            "pane_index": p["pane_index"],
            "pane_id": p["pane_id"],
            "cwd": p["cwd"],
            "title": p["title"],
            "session_id": sid,
            "method": method,
        })
    return records


# --------------------------------------------------------------------------- #
# snapshot
# --------------------------------------------------------------------------- #
def snapshot() -> int:
    os.makedirs(STATE_DIR, exist_ok=True)
    records = detect()
    resolved = [r for r in records if r["session_id"]]
    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": os.uname().nodename,
        "claude_panes": len(records),
        "resolved": len(resolved),
        "panes": records,
    }
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = os.path.join(STATE_DIR, f"manifest-{stamp}.json")
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    tmp = LATEST + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(manifest, fh, indent=2)
    os.replace(tmp, LATEST)  # atomic

    history = sorted(glob.glob(os.path.join(STATE_DIR, "manifest-*.json")))
    for old in history[:-KEEP_HISTORY]:
        try:
            os.remove(old)
        except OSError:
            pass

    unresolved = len(records) - len(resolved)
    msg = f"[snapshot] {len(resolved)}/{len(records)} Claude panes resolved -> {LATEST}"
    if unresolved:
        msg += f" ({unresolved} unresolved)"
    print(msg)
    return 0


# --------------------------------------------------------------------------- #
# restore
# --------------------------------------------------------------------------- #
def pane_state(target: str) -> tuple[str, str] | None:
    """Return (current_command, current_path) for a live pane, or None if absent."""
    r = subprocess.run(
        [TMUX, "display-message", "-p", "-t", target, "#{pane_current_command}\t#{pane_current_path}"],
        capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    cmd, _, path = r.stdout.strip().partition("\t")
    return cmd, path


def find_target(rec: dict) -> str | None:
    """Locate the restored pane for a manifest record. Prefer index, fall back to window name."""
    primary = f"{rec['session']}:{rec['window_index']}.{rec['pane_index']}"
    if pane_state(primary) is not None:
        return primary
    # window indexes can shift; match by window name + pane index instead.
    fmt = "#{session_name}\t#{window_name}\t#{pane_index}\t#{session_name}:#{window_index}.#{pane_index}"
    for line in run([TMUX, "list-panes", "-a", "-F", fmt]).splitlines():
        sess, wname, pidx, addr = (line.split("\t") + [""] * 4)[:4]
        if sess == rec["session"] and wname == rec["window_name"] and pidx == rec["pane_index"]:
            return addr
    return None


def restore(dry: bool = False) -> int:
    if not os.path.exists(LATEST):
        print(f"[restore] no manifest at {LATEST}; nothing to do")
        return 0
    with open(LATEST) as fh:
        manifest = json.load(fh)
    panes = manifest.get("panes", [])  # every entry is a Claude pane by construction
    if not panes:
        print("[restore] manifest has no Claude panes")
        return 0

    if not dry:
        time.sleep(SETTLE_SECONDS)  # let resurrect-restored shells reach a prompt

    resumed = fresh = skipped = 0
    for rec in panes:
        target = find_target(rec)
        if target is None:
            print(f"[restore] skip (pane not found): {rec['session']}:{rec['window_index']}.{rec['pane_index']} {rec['title'][:40]}")
            skipped += 1
            continue

        state = pane_state(target)
        if state is None:
            skipped += 1
            continue
        cur_cmd, cur_path = state
        if not (cur_cmd in SHELLS or os.path.basename(cur_cmd) in SHELLS):
            # already running something (claude already up, nvim, etc.) -> don't clobber
            skipped += 1
            continue

        # Resume when a transcript exists for the recorded id; otherwise the
        # session was empty/fresh, so relaunch bare claude (loses nothing).
        sid = rec.get("session_id")
        cwd = rec["cwd"]
        has_transcript = bool(sid) and os.path.exists(os.path.join(PROJECTS, munge(cwd), f"{sid}.jsonl"))
        cmd = f"claude --resume {sid}" if has_transcript else "claude"
        if cur_path != cwd:
            cmd = f"cd {shlex.quote(cwd)} && {cmd}"

        if has_transcript:
            resumed += 1
        else:
            fresh += 1

        if dry:
            tag = f"resume {sid[:8]}" if has_transcript else "fresh claude   "
            print(f"[dry-run] {target:<16} {tag}  {rec['title'][:42]}")
            continue

        subprocess.run([TMUX, "send-keys", "-t", target, "--", cmd, "Enter"])
        time.sleep(STAGGER_SECONDS)

    verb = "would launch" if dry else "launched"
    print(f"[restore] {verb} {resumed + fresh} ({resumed} resumed, {fresh} fresh), skipped {skipped} (already running)")
    return 0


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #
def list_live() -> int:
    records = detect()
    for r in records:
        sid = r["session_id"] or "?" * 8
        loc = f"{r['session']}:{r['window_index']}.{r['pane_index']}"
        print(f"  {r['method']:<10} {sid[:8]}  {loc:<10} {r['window_name'][:14]:<14} {r['title'][:40]}")
    resolved = sum(1 for r in records if r["session_id"])
    print(f"  -> {resolved}/{len(records)} resolved")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "snapshot":
        return snapshot()
    if cmd == "restore":
        return restore(dry="--dry-run" in sys.argv)
    if cmd == "list":
        return list_live()
    print(__doc__)
    print(f"usage: {os.path.basename(sys.argv[0])} {{snapshot|restore [--dry-run]|list}}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
