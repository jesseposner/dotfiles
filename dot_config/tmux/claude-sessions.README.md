# claude-sessions: persist & restore Claude Code sessions across reboots

Layered on top of tmux-resurrect + tmux-continuum (which already persist the
window/pane/layout/cwd tree and auto-restore on boot). This adds the one thing
resurrect can't: re-attaching each restored pane to its **exact** Claude Code
conversation.

## How it works

- `claude-sessions.py snapshot` detects every tmux pane running Claude Code,
  resolves its exact session id, and writes a manifest to
  `claude-sessions/latest.json` (plus timestamped history, last 30 kept).
- `claude-sessions.py restore` reads the latest manifest and, for each Claude
  pane that came back as a bare shell, injects `claude --resume <id>`
  (staggered, to avoid a thundering herd of transcript loads at login). A pane
  whose recorded session has no transcript on disk relaunches bare `claude`.

### Exact session-id detection (the hard part)

Every Claude process injects `CLAUDE_CODE_SESSION_ID` into the environment of
its child processes (MCP servers, Bash-tool shells). Those children often have
no controlling tty, so we climb the ppid chain from any env-bearing process to
its `claude` ancestor, read that ancestor's tty, and join to `tmux list-panes`
by tty. This disambiguates multiple Claude panes sharing one cwd, which a
newest-jsonl-by-mtime heuristic cannot (it collapses them to the single
most-recently-written session).

## Wiring (in ~/.tmux.conf)

- `@resurrect-hook-post-save-all`    -> snapshot (fires with every continuum
  save, ~15 min, and manual `prefix + C-s`)
- `@resurrect-hook-post-restore-all` -> restore (fires after continuum rebuilds
  the layout on boot)
- `prefix + S` -> manual snapshot on demand

So continuum keeps the manifest fresh; on reboot, continuum restores the layout
and the post-restore hook re-resumes every Claude pane. Fully automatic.

## Manual use / testing

    python3 claude-sessions.py list                 # show live detection
    python3 claude-sessions.py snapshot             # write the manifest now
    python3 claude-sessions.py restore --dry-run    # show what restore would do
    CLAUDE_SESSIONS_MANIFEST=/tmp/x.json python3 claude-sessions.py restore   # test against a synthetic manifest
    CLAUDE_RESTORE_STAGGER=0.4                       # seconds between launches (default 0.4)

## Notes / gotchas

- Hooks use absolute paths (`/opt/homebrew/bin/python3`) because resurrect hooks
  run with a minimal PATH. If Homebrew's python moves, update the paths in
  ~/.tmux.conf.
- Log: `claude-sessions/hook.log` (append-only, one line per save/restore).
- Restore never clobbers a pane already running something (claude, nvim, etc.).
- Restore deliberately does **not** title-match: a stale tmux pane title could
  resume the wrong conversation, which is worse than starting fresh.
- To disable: remove the two `@resurrect-hook-*` lines from ~/.tmux.conf.
