# claude-sessions: persist Claude Code + Codex CLI sessions across reboots

Layered on top of tmux-resurrect + tmux-continuum, which already persist the
window/pane/layout/cwd tree. This adds the one thing resurrect cannot:
re-attaching each restored pane to its **exact agent conversation**.

The script and state directory keep their original `claude-sessions` name for
backward compatibility, but manifests now contain both Claude and Codex panes.

## Recovery after a reboot

The happy path is one command:

1. Open the terminal.
2. Run `tmux`.

Starting the tmux server triggers continuum, which rebuilds the
window/pane/layout/cwd tree. The post-restore hook then resumes every Claude and
Codex pane to its exact conversation, launching them 0.4 seconds apart. Done.

**Verify it worked:** `cat ~/.config/tmux/claude-sessions/hook.log` — look for a
recent line like `[restore] launched N (R resumed: C Claude, D Codex; F fresh)`.

**Fallbacks, in escalating order:**

- Layout came back but agent panes are bare shells (hook did not fire) -> run
  it by hand:
  `python3 ~/.config/tmux/claude-sessions.py restore`
- Nothing restored at all (blank tmux) -> trigger resurrect manually with
  `prefix + C-r`; that rebuilds the layout *and* fires the resume hook.
- Total fallback -> inspect the plain-JSON manifest, which records each pane's
  agent, session id, title, and cwd:
  `cat ~/.config/tmux/claude-sessions/latest.json`

**Before a planned reboot:** hit `prefix + S`. This runs a full resurrect save;
the post-save hook snapshots the matching Claude and Codex session ids.

Note: tmux does not auto-start at login unless `@continuum-boot 'on'` is set
(it is not by default) — you start tmux yourself.

## How it works

- `claude-sessions.py snapshot` detects every tmux pane running Claude Code or
  Codex, resolves its exact session id, and writes
  `claude-sessions/latest.json` plus timestamped history (everything newer
  than 7 days is kept, floor of 30 — the manifest that matters is the one
  written just before a disaster, and the loss may not be noticed for days).
- The manifest also captures every window's name, layout string, and
  automatic-rename setting (one atomic `list-windows` call). Capture only —
  resurrect remains the restore machinery — but it makes the manifest
  self-sufficient: if every resurrect save is corrupt, the full workspace
  shape is still in one JSON file and can be replayed with plain tmux
  commands.
- `restore` pins the manifest it acted on to `claude-sessions/restored-from.json`
  before launching anything. Later snapshots overwrite latest.json with the
  post-restore workspace; the pin preserves the boot-time truth. It also
  audits itself: recorded panes with no home in the restored layout are
  counted, and a nonzero count logs a `[restore] WARNING` naming the pinned
  manifest and the rerun command — a truncated layout announces itself
  instead of hiding behind a shrunken latest.json.
- `claude-sessions.py restore` reads that manifest and, for every recorded pane
  that came back as a bare shell, injects either `claude --resume <id>` or
  `codex resume <id>`.
- If a recorded transcript no longer exists, restore starts that agent fresh
  rather than handing it a dead resume id.
- Claude Code >= 2.1.226 shows an interactive "resume from summary or full?"
  menu when resuming an old or large session; a restored pane blocks there
  until answered. After launching, restore watches exactly the Claude panes it
  resumed and confirms the menu on each as it appears (panes load transcripts
  at very different speeds, so this polls for up to `AGENT_PROMPT_TIMEOUT`
  seconds, default 180). `AGENT_RESUME_CHOICE` picks the answer: `summary`
  (default), `full`, or `off` to disable the watcher. Detection requires both
  menu markers on the visible screen, so ordinary scrollback cannot trigger it.
- `claude-sessions.py answer-prompts` is the same sweep as a manual command,
  for panes launched outside the hook:
  `answer-prompts [--choice summary|full] [--timeout N] [--targets %1,%2]`
  (default: all live Claude panes except the one running the command).
- Version-1 Claude-only manifests remain restorable; a record without an
  `agent` field is treated as Claude.

### Save integrity guard

resurrect's dumps run as forked subprocesses; on a constrained machine their
output truncates silently while the save still advances the `last` symlink —
burying the newest good save under corrupt ones precisely when nobody is
watching. Observed 2026-08-06: the lid was closed on 20% battery and 16 hours
of dark-wake cycles wrote saves that shrank from 251 panes to 6 (first losing
their window/state sections, then most of the pane list) while the manifest
proved 112 agent panes were alive the whole time.

Since snapshot runs in lockstep with every resurrect save, it validates the
save it just paired with, two ways:

- **Structural**: sections are dumped panes -> windows -> state, so a
  complete save ends with its state line; a missing tail means the dump was
  cut off mid-write. Also catches a missing or broken `last` symlink.
- **Cross-check**: snapshot independently counts live agent panes from `ps`;
  a fresh save claiming fewer total panes than there are live agent panes is
  lying even if structurally complete. (Applied only to saves written within
  the last two minutes — older saves are allowed to predate workspace
  growth.)

On structural failure, the guard **repoints `last` to the newest structurally
healthy save**, so the post-reboot restore ignores the corrupt data with no
one at the keyboard; degraded files stay on disk for forensics. On a
cross-check failure it warns without repointing (an older save is not more
truthful about the current workspace; the next healthy save self-corrects).
Either way it logs a `[save-check] WARNING` to hook.log and flashes a
15-second tmux status message for the attended case. Healthy saves are
silent. /orient greps hook.log for warnings since the last session — that is
the channel that works when the failure happened with the lid closed.

The manifest side needs no guard: manifest writes are atomic (temp file +
rename), so they cannot be truncated into lies, and 30 timestamped manifests
are kept. In the 2026-08-06 incident the manifests kept resolving 112/112
panes on 1% battery and became the gold source for recovery — which is why
snapshots are never skipped on low battery.

`AGENT_RESURRECT_DIR` overrides the directory for testing; otherwise
`@resurrect-dir`, `~/.tmux/resurrect`, and the XDG default are tried in
resurrect's own order.

### Exact session-id detection (the hard part)

**Claude Code:** Claude injects `CLAUDE_CODE_SESSION_ID` into its child
processes (MCP servers, Bash-tool shells). Those children often have no
controlling tty, so the script climbs their ppid chain to the `claude` ancestor,
reads that ancestor's tty, and joins it to `tmux list-panes`.

**Codex CLI:** Codex's `SessionStart` hook provides the current `session_id` and
transcript path. A tiny hook records those values against the exact inherited
`TMUX_PANE`, along with the live Codex master pid so stale pane mappings are
rejected.

For Codex sessions that were already running before the hook was installed or
trusted, snapshot has two exact fallbacks:

1. Inspect rollout files held open by the live Codex master, ignoring subagent
   rollouts and accepting a result only when the top-level conversation is
   unambiguous.
2. Read an explicit UUID from `codex resume <id>` in the process argv.

This avoids newest-transcript-by-mtime or newest-in-cwd guesses, both of which
collapse multiple agent panes sharing the same cwd onto one conversation.

## Wiring

In `~/.tmux.conf`:

- `@resurrect-hook-post-save-all` -> snapshot after every continuum/resurrect
  save (about every 15 minutes, plus manual saves)
- `@resurrect-hook-post-restore-all` -> resume after resurrect rebuilds layout
- `prefix + S` -> full manual resurrect save; the post-save hook snapshots
  agent ids in lockstep with that exact layout

In `~/.codex/hooks.json`:

- `SessionStart` for `startup|resume|clear|compact` ->
  `claude-sessions.py codex-hook`

Codex requires one-time review of a new or changed non-managed hook. Start a
Codex session, run `/hooks`, inspect this command, and trust it. Until then the
open-transcript fallback still lets snapshots detect currently running Codex
sessions.

## Manual use / testing

    python3 ~/.config/tmux/claude-sessions.py list
    python3 ~/.config/tmux/claude-sessions.py snapshot
    python3 ~/.config/tmux/claude-sessions.py restore --dry-run
    python3 ~/.config/tmux/claude-sessions.py answer-prompts --timeout 30
    AGENT_SESSIONS_MANIFEST=/tmp/x.json python3 ~/.config/tmux/claude-sessions.py restore --dry-run
    AGENT_RESTORE_STAGGER=0.4 python3 ~/.config/tmux/claude-sessions.py restore

For isolated tests, set `AGENT_SESSIONS_STATE_DIR=/tmp/agent-sessions`; this
redirects the manifest history and Codex registry as well as `latest.json`.
The older `CLAUDE_SESSIONS_MANIFEST` and `CLAUDE_RESTORE_STAGGER` overrides are
still accepted.

## Notes / gotchas

- Hooks use absolute paths (`/opt/homebrew/bin/python3`) because resurrect and
  Codex hooks can run with a minimal PATH. If Homebrew's Python moves, update
  both `~/.tmux.conf` and `~/.codex/hooks.json`.
- Log: `~/.config/tmux/claude-sessions/hook.log` (append-only, one line per
  tmux save/restore).
- Codex registry: `~/.config/tmux/claude-sessions/codex-registry.json` (bounded
  to the 200 most recently updated pane ids).
- Restore never clobbers a pane already running something (Claude, Codex, nvim,
  etc.).
- Restore deliberately does **not** title-match: a stale tmux pane title could
  resume the wrong conversation, which is worse than starting fresh.
- To disable tmux persistence, remove the two `@resurrect-hook-*` lines from
  `~/.tmux.conf`. To disable Codex registration, remove the `SessionStart` hook
  from `~/.codex/hooks.json`.
