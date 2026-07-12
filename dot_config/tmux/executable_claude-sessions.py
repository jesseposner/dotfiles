#!/opt/homebrew/bin/python3
"""
claude-sessions.py: persist & restore Claude Code and Codex CLI sessions.

Sits on top of tmux-resurrect / tmux-continuum (which already persist the
window/pane/layout/cwd tree). This layer adds the one thing resurrect cannot:
re-attaching each restored pane to its exact agent conversation.

Subcommands
  snapshot   : detect every tmux pane running Claude Code or Codex, resolve its
               exact session id, and write a manifest. Wire to resurrect's
               @resurrect-hook-post-save-all hook so it runs in lockstep with
               every resurrect/continuum save.
  restore    : read the latest manifest and, for each saved agent pane that came
               back as a bare shell, inject the appropriate resume command.
               Wire to @resurrect-hook-post-restore-all so it runs after
               continuum rebuilds the layout. Launches are staggered to avoid a
               thundering herd of transcript loads.
  list       : print the current live detection (for testing / sanity).
  codex-hook : consume a Codex SessionStart hook payload from stdin and record
               its exact session_id against the inherited TMUX_PANE.

Claude detection is exact, not heuristic. Claude injects
CLAUDE_CODE_SESSION_ID into child environments; we climb from those children
to their Claude ancestor and join its tty to tmux.

Codex exposes session_id through its stable SessionStart hook API. The hook
registry is the primary mapping. For sessions that predate the hook, snapshot
can recover the exact top-level rollout held open by the live Codex process;
an explicit `codex resume <uuid>` argv is the final fallback.
"""
from __future__ import annotations

import fcntl
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
LSOF = shutil.which("lsof") or "/usr/sbin/lsof"
HOME = os.path.expanduser("~")
STATE_DIR = os.environ.get(
    "AGENT_SESSIONS_STATE_DIR",
    os.path.join(HOME, ".config", "tmux", "claude-sessions"),
)
# Preserve the original override while offering a provider-neutral name.
LATEST = os.environ.get(
    "AGENT_SESSIONS_MANIFEST",
    os.environ.get("CLAUDE_SESSIONS_MANIFEST", os.path.join(STATE_DIR, "latest.json")),
)
CLAUDE_PROJECTS = os.path.join(HOME, ".claude", "projects")
CODEX_SESSIONS = os.path.join(HOME, ".codex", "sessions")
CODEX_REGISTRY = os.path.join(STATE_DIR, "codex-registry.json")
SNAPSHOT_LOCK = os.path.join(STATE_DIR, "snapshot.lock")
KEEP_HISTORY = 30  # timestamped manifests to retain
KEEP_CODEX_REGISTRY = 200  # stale tmux pane ids are harmless, but bound the file
SETTLE_SECONDS = 1.0  # let resurrect-restored shells reach a prompt first
STAGGER_SECONDS = float(
    os.environ.get(
        "AGENT_RESTORE_STAGGER",
        os.environ.get("CLAUDE_RESTORE_STAGGER", "0.4"),
    )
)

UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
UUID_PATTERN = re.compile(rf"^{UUID_RE}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+")  # tmux reports Claude's version as its command
SHELLS = {"fish", "-fish", "bash", "-bash", "zsh", "-zsh", "sh", "-sh", "login"}


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def norm_tty(tty: str) -> str:
    """Normalize to the bare device name used by `ps -o tty=` (for example ttys029)."""
    return tty.replace("/dev/", "")


def munge(cwd: str) -> str:
    return cwd.replace("/", "-")


def command_parts(command: str) -> list[str]:
    try:
        return shlex.split(command.strip())
    except ValueError:
        return command.strip().split()


def atomic_json_write(path: str, value: object) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as fh:
        json.dump(value, fh, indent=2)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Live process and tmux inspection
# --------------------------------------------------------------------------- #
def all_procs() -> dict[str, tuple[str, str, str]]:
    """pid -> (ppid, tty, command-line)."""
    procs: dict[str, tuple[str, str, str]] = {}
    for line in run(
        ["ps", "-A", "-o", "pid=", "-o", "ppid=", "-o", "tty=", "-o", "command="]
    ).splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, tty, command = parts
        procs[pid] = (ppid, norm_tty(tty), command)
    return procs


def cli_masters(
    procs: dict[str, tuple[str, str, str]], program: str
) -> dict[str, dict]:
    """pid -> {pid, tty, argv_id} for top-level interactive agent processes."""
    masters: dict[str, dict] = {}
    for pid, (_ppid, tty, command) in procs.items():
        parts = command_parts(command)
        if not parts or os.path.basename(parts[0]) != program:
            continue
        match = re.search(rf"(?:^|\s)--resume\s+({UUID_RE})(?:\s|$)", command)
        if program == "codex":
            match = re.search(rf"(?:^|\s)resume\s+({UUID_RE})(?:\s|$)", command)
        masters[pid] = {
            "pid": pid,
            "tty": tty,
            "argv_id": match.group(1) if match else None,
        }
    return masters


def find_ancestor_master(
    pid: str,
    procs: dict[str, tuple[str, str, str]],
    masters: dict[str, dict],
) -> str | None:
    hops = 0
    while pid in procs and hops < 50:
        if pid in masters:
            return pid
        pid = procs[pid][0]
        hops += 1
    return None


def env_session_ids(variable: str) -> dict[str, str]:
    """pid -> UUID for processes whose environment carries `variable`."""
    pattern = re.compile(rf"{re.escape(variable)}=({UUID_RE})")
    out: dict[str, str] = {}
    # BSD ps suppresses the environment when a custom -o format is supplied.
    for line in run(["ps", "eww", "-A"]).splitlines():
        match = pattern.search(line)
        if not match:
            continue
        first = line.split(None, 1)
        if first and first[0].isdigit():
            out[first[0]] = match.group(1)
    return out


def tmux_panes() -> list[dict]:
    fmt = "\t".join(
        "#{%s}" % field
        for field in (
            "session_name",
            "window_index",
            "window_name",
            "pane_index",
            "pane_id",
            "pane_tty",
            "pane_current_path",
            "pane_current_command",
            "pane_title",
        )
    )
    panes = []
    for line in run([TMUX, "list-panes", "-a", "-F", fmt]).splitlines():
        fields = (line.split("\t") + [""] * 9)[:9]
        panes.append(
            dict(
                zip(
                    (
                        "session",
                        "window_index",
                        "window_name",
                        "pane_index",
                        "pane_id",
                        "tty",
                        "cwd",
                        "command",
                        "title",
                    ),
                    fields,
                )
            )
        )
    return panes


def pane_record(
    pane: dict,
    agent: str,
    session_id: str | None,
    method: str,
    transcript_path: str | None = None,
) -> dict:
    record = {
        "agent": agent,
        "session": pane["session"],
        "window_index": pane["window_index"],
        "window_name": pane["window_name"],
        "pane_index": pane["pane_index"],
        "pane_id": pane["pane_id"],
        "cwd": pane["cwd"],
        "title": pane["title"],
        "session_id": session_id,
        "method": method,
    }
    if transcript_path:
        record["transcript_path"] = transcript_path
    return record


# --------------------------------------------------------------------------- #
# Claude detection
# --------------------------------------------------------------------------- #
def claude_tty_session_map(
    procs: dict[str, tuple[str, str, str]],
    masters: dict[str, dict],
    env: dict[str, str],
) -> dict[str, tuple[str, str]]:
    """tty -> (session_id, method). Live env evidence wins over resume argv."""
    tty_sid: dict[str, tuple[str, str]] = {}
    for info in masters.values():
        if info["argv_id"]:
            tty_sid[info["tty"]] = (info["argv_id"], "argv")
    for env_pid, session_id in env.items():
        master_pid = find_ancestor_master(env_pid, procs, masters)
        if master_pid:
            tty_sid[masters[master_pid]["tty"]] = (session_id, "env")
    return tty_sid


def detect_claude(
    panes: list[dict], procs: dict[str, tuple[str, str, str]]
) -> list[dict]:
    masters = cli_masters(procs, "claude")
    tty_sid = claude_tty_session_map(
        procs,
        masters,
        env_session_ids("CLAUDE_CODE_SESSION_ID"),
    )
    records = []
    for pane in panes:
        is_claude = bool(VERSION_RE.match(pane["command"])) or pane["command"] == "claude"
        if not is_claude:
            continue
        session_id, method = tty_sid.get(norm_tty(pane["tty"]), (None, "unresolved"))
        records.append(pane_record(pane, "claude", session_id, method))
    return records


# --------------------------------------------------------------------------- #
# Codex detection and SessionStart registry
# --------------------------------------------------------------------------- #
def load_codex_registry() -> dict[str, dict]:
    try:
        with open(CODEX_REGISTRY) as fh:
            value = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    panes = value.get("panes", {}) if isinstance(value, dict) else {}
    return panes if isinstance(panes, dict) else {}


def codex_transcript_path(session_id: str | None, hint: str | None = None) -> str | None:
    if not session_id or not UUID_PATTERN.match(session_id):
        return None
    if hint and os.path.exists(hint):
        return hint
    matches = glob.glob(
        os.path.join(CODEX_SESSIONS, "**", f"*{session_id}.jsonl"),
        recursive=True,
    )
    return matches[0] if matches else None


def read_codex_session_meta(path: str) -> dict | None:
    try:
        with open(path, errors="replace") as fh:
            first = json.loads(fh.readline())
    except (OSError, json.JSONDecodeError):
        return None
    if first.get("type") != "session_meta" or not isinstance(first.get("payload"), dict):
        return None
    payload = first["payload"]
    session_id = payload.get("id")
    if not isinstance(session_id, str) or not UUID_PATTERN.match(session_id):
        return None
    return payload


def codex_lsof_candidates(master_pid: str) -> list[dict]:
    """Return top-level Codex rollouts currently held open by a master process."""
    if not os.path.exists(LSOF):
        return []
    candidates: dict[str, dict] = {}
    for line in run([LSOF, "-a", "-p", master_pid, "-Fn"]).splitlines():
        if not line.startswith("n"):
            continue
        path = line[1:]
        if not (
            path.startswith(CODEX_SESSIONS + os.sep)
            and os.path.basename(path).startswith("rollout-")
            and path.endswith(".jsonl")
        ):
            continue
        payload = read_codex_session_meta(path)
        if not payload:
            continue
        source = payload.get("source")
        if isinstance(source, dict) and "subagent" in source:
            continue
        session_id = payload["id"]
        candidates[session_id] = {
            "session_id": session_id,
            "cwd": payload.get("cwd"),
            "transcript_path": path,
        }
    return list(candidates.values())


def codex_lsof_session(master_pid: str, cwd: str) -> dict | None:
    candidates = codex_lsof_candidates(master_pid)
    cwd_matches = [candidate for candidate in candidates if candidate.get("cwd") == cwd]
    if len(cwd_matches) == 1:
        return cwd_matches[0]
    if len(candidates) == 1:
        return candidates[0]
    # Multiple top-level rollouts are ambiguous; unresolved is safer than wrong.
    return None


def codex_registry_session(
    pane: dict, master: dict, registry: dict[str, dict]
) -> dict | None:
    entry = registry.get(pane["pane_id"])
    if not isinstance(entry, dict):
        return None
    session_id = entry.get("session_id")
    if not isinstance(session_id, str) or not UUID_PATTERN.match(session_id):
        return None
    recorded_pid = entry.get("master_pid")
    if recorded_pid is not None and str(recorded_pid) != master["pid"]:
        return None
    if recorded_pid is None and entry.get("cwd") not in (None, pane["cwd"]):
        return None
    transcript = codex_transcript_path(session_id, entry.get("transcript_path"))
    if not transcript:
        return None
    return {"session_id": session_id, "transcript_path": transcript}


def detect_codex(
    panes: list[dict], procs: dict[str, tuple[str, str, str]]
) -> list[dict]:
    masters = cli_masters(procs, "codex")
    by_tty = {info["tty"]: info for info in masters.values()}
    registry = load_codex_registry()
    records = []
    for pane in panes:
        master = by_tty.get(norm_tty(pane["tty"]))
        if not master or not pane["command"].startswith("codex"):
            continue

        session_id = None
        transcript = None
        method = "unresolved"

        registered = codex_registry_session(pane, master, registry)
        if registered:
            session_id = registered["session_id"]
            transcript = registered["transcript_path"]
            method = "hook"
        else:
            opened = codex_lsof_session(master["pid"], pane["cwd"])
            if opened:
                session_id = opened["session_id"]
                transcript = opened["transcript_path"]
                method = "lsof"
            elif master["argv_id"]:
                session_id = master["argv_id"]
                transcript = codex_transcript_path(session_id)
                method = "argv"

        records.append(
            pane_record(pane, "codex", session_id, method, transcript)
        )
    return records


def detect() -> list[dict]:
    """Return one record per Claude or Codex tmux pane."""
    procs = all_procs()
    panes = tmux_panes()
    records = detect_claude(panes, procs) + detect_codex(panes, procs)
    return sorted(
        records,
        key=lambda record: (
            record["session"],
            int(record["window_index"]),
            int(record["pane_index"]),
        ),
    )


def codex_hook() -> int:
    """Record Codex's stable SessionStart payload against its inherited tmux pane."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0  # a persistence helper must never prevent Codex startup

    session_id = payload.get("session_id")
    pane_id = os.environ.get("TMUX_PANE")
    if not (
        pane_id
        and isinstance(session_id, str)
        and UUID_PATTERN.match(session_id)
    ):
        return 0  # Codex outside tmux needs no registry entry

    procs = all_procs()
    masters = cli_masters(procs, "codex")
    master_pid = find_ancestor_master(str(os.getppid()), procs, masters)
    if master_pid is None:
        pane_tty = run([TMUX, "display-message", "-p", "-t", pane_id, "#{pane_tty}"]).strip()
        normalized = norm_tty(pane_tty)
        master_pid = next(
            (pid for pid, info in masters.items() if info["tty"] == normalized),
            None,
        )

    os.makedirs(STATE_DIR, exist_ok=True)
    lock_path = CODEX_REGISTRY + ".lock"
    with open(lock_path, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(CODEX_REGISTRY) as fh:
                registry = json.load(fh)
        except (OSError, json.JSONDecodeError):
            registry = {"version": 1, "panes": {}}
        if not isinstance(registry.get("panes"), dict):
            registry["panes"] = {}

        registry["version"] = 1
        registry["panes"][pane_id] = {
            "session_id": session_id,
            "transcript_path": payload.get("transcript_path"),
            "cwd": payload.get("cwd"),
            "source": payload.get("source"),
            "master_pid": int(master_pid) if master_pid else None,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if len(registry["panes"]) > KEEP_CODEX_REGISTRY:
            newest = sorted(
                registry["panes"].items(),
                key=lambda item: item[1].get("updated", ""),
                reverse=True,
            )[:KEEP_CODEX_REGISTRY]
            registry["panes"] = dict(newest)
        atomic_json_write(CODEX_REGISTRY, registry)
        fcntl.flock(lock, fcntl.LOCK_UN)
    return 0


# --------------------------------------------------------------------------- #
# Snapshot
# --------------------------------------------------------------------------- #
def snapshot() -> int:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SNAPSHOT_LOCK, "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("[snapshot] skipped: another snapshot is already running")
            return 0
        return snapshot_locked()


def snapshot_locked() -> int:
    records = detect()
    resolved = [record for record in records if record["session_id"]]
    agent_counts = {
        agent: sum(1 for record in records if record["agent"] == agent)
        for agent in ("claude", "codex")
    }
    resolved_counts = {
        agent: sum(
            1
            for record in resolved
            if record["agent"] == agent
        )
        for agent in ("claude", "codex")
    }
    manifest = {
        "version": 2,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": os.uname().nodename,
        "agent_panes": len(records),
        "claude_panes": agent_counts["claude"],
        "codex_panes": agent_counts["codex"],
        "resolved": len(resolved),
        "panes": records,
    }
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    history_path = os.path.join(STATE_DIR, f"manifest-{stamp}.json")
    atomic_json_write(history_path, manifest)
    atomic_json_write(LATEST, manifest)

    history = sorted(glob.glob(os.path.join(STATE_DIR, "manifest-*.json")))
    for old in history[:-KEEP_HISTORY]:
        try:
            os.remove(old)
        except OSError:
            pass

    unresolved = len(records) - len(resolved)
    message = (
        f"[snapshot] {len(resolved)}/{len(records)} agent panes resolved "
        f"({resolved_counts['claude']}/{agent_counts['claude']} Claude, "
        f"{resolved_counts['codex']}/{agent_counts['codex']} Codex) -> {LATEST}"
    )
    if unresolved:
        message += f" ({unresolved} unresolved)"
    print(message)
    return 0


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #
def pane_state(target: str) -> tuple[str, str] | None:
    """Return (current_command, current_path) for a live pane, or None if absent."""
    result = subprocess.run(
        [
            TMUX,
            "display-message",
            "-p",
            "-t",
            target,
            "#{pane_current_command}\t#{pane_current_path}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    command, _, path = result.stdout.strip().partition("\t")
    return command, path


def find_target(record: dict) -> str | None:
    """Locate the restored pane. Prefer indexes, then window name + pane index."""
    primary = f"{record['session']}:{record['window_index']}.{record['pane_index']}"
    if pane_state(primary) is not None:
        return primary
    fmt = "#{session_name}\t#{window_name}\t#{pane_index}\t#{session_name}:#{window_index}.#{pane_index}"
    for line in run([TMUX, "list-panes", "-a", "-F", fmt]).splitlines():
        session, window_name, pane_index, address = (line.split("\t") + [""] * 4)[:4]
        if (
            session == record["session"]
            and window_name == record["window_name"]
            and pane_index == record["pane_index"]
        ):
            return address
    return None


def transcript_for(record: dict, agent: str, session_id: str | None) -> str | None:
    if not session_id:
        return None
    if agent == "claude":
        path = os.path.join(
            CLAUDE_PROJECTS,
            munge(record["cwd"]),
            f"{session_id}.jsonl",
        )
        return path if os.path.exists(path) else None
    if agent == "codex":
        return codex_transcript_path(session_id, record.get("transcript_path"))
    return None


def restore(dry: bool = False) -> int:
    if not os.path.exists(LATEST):
        print(f"[restore] no manifest at {LATEST}; nothing to do")
        return 0
    with open(LATEST) as fh:
        manifest = json.load(fh)
    panes = manifest.get("panes", [])
    if not panes:
        print("[restore] manifest has no agent panes")
        return 0

    if not dry:
        time.sleep(SETTLE_SECONDS)

    resumed = {"claude": 0, "codex": 0}
    fresh = {"claude": 0, "codex": 0}
    skipped = 0
    for record in panes:
        # Version-1 manifests contained only Claude records and no agent field.
        agent = record.get("agent", "claude")
        if agent not in ("claude", "codex"):
            skipped += 1
            continue

        target = find_target(record)
        if target is None:
            print(
                f"[restore] skip (pane not found): "
                f"{record['session']}:{record['window_index']}.{record['pane_index']} "
                f"{record.get('title', '')[:40]}"
            )
            skipped += 1
            continue

        state = pane_state(target)
        if state is None:
            skipped += 1
            continue
        current_command, current_path = state
        if not (
            current_command in SHELLS
            or os.path.basename(current_command) in SHELLS
        ):
            skipped += 1
            continue

        session_id = record.get("session_id")
        cwd = record.get("cwd") or current_path
        transcript = transcript_for(record, agent, session_id)
        if agent == "claude":
            command = f"claude --resume {shlex.quote(session_id)}" if transcript else "claude"
        else:
            command = f"codex resume {shlex.quote(session_id)}" if transcript else "codex"
        if current_path != cwd:
            command = f"cd {shlex.quote(cwd)} && {command}"

        bucket = resumed if transcript else fresh
        bucket[agent] += 1

        if dry:
            action = f"resume {agent} {session_id[:8]}" if transcript else f"fresh {agent}"
            print(f"[dry-run] {target:<16} {action:<23} {record.get('title', '')[:42]}")
            continue

        subprocess.run([TMUX, "send-keys", "-t", target, "--", command, "Enter"])
        time.sleep(STAGGER_SECONDS)

    resumed_total = sum(resumed.values())
    fresh_total = sum(fresh.values())
    verb = "would launch" if dry else "launched"
    print(
        f"[restore] {verb} {resumed_total + fresh_total} "
        f"({resumed_total} resumed: {resumed['claude']} Claude, "
        f"{resumed['codex']} Codex; {fresh_total} fresh), "
        f"skipped {skipped} (already running or unavailable)"
    )
    return 0


# --------------------------------------------------------------------------- #
# List
# --------------------------------------------------------------------------- #
def list_live() -> int:
    records = detect()
    for record in records:
        session_id = record["session_id"] or "?" * 8
        location = f"{record['session']}:{record['window_index']}.{record['pane_index']}"
        print(
            f"  {record['agent']:<7} {record['method']:<10} {session_id[:8]}  "
            f"{location:<10} {record['window_name'][:14]:<14} {record['title'][:40]}"
        )
    resolved = sum(1 for record in records if record["session_id"])
    claude = sum(1 for record in records if record["agent"] == "claude")
    codex = sum(1 for record in records if record["agent"] == "codex")
    print(f"  -> {resolved}/{len(records)} resolved ({claude} Claude, {codex} Codex)")
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    if command == "snapshot":
        return snapshot()
    if command == "restore":
        return restore(dry="--dry-run" in sys.argv)
    if command == "list":
        return list_live()
    if command == "codex-hook":
        return codex_hook()
    print(__doc__)
    print(
        f"usage: {os.path.basename(sys.argv[0])} "
        "{snapshot|restore [--dry-run]|list|codex-hook}"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
