# Keybindings Cheatsheet

Vi-mode everywhere. Leader key is `,` in Neovim, prefix is `Ctrl-a` in tmux.

## tmux

### Basics

| Key | Action |
|-----|--------|
| `C-a` | Prefix (replaces default `C-b`) |
| `C-a C-a` | Send literal `C-a` to inner program |

### Windows

| Key | Action |
|-----|--------|
| `C-a c` | Create window |
| `C-a n` | Next window |
| `C-a p` | Previous window |
| `C-a 0-9` | Switch to window by number |
| `C-a w` | Visual window/pane picker |
| `C-a ,` | Rename window |
| `C-a &` | Close window |

### Panes

| Key | Action |
|-----|--------|
| `C-a %` | Split vertically |
| `C-a "` | Split horizontally |
| `C-h/j/k/l` | Navigate panes (vim-tmux-navigator) |
| `C-a z` | Toggle pane zoom |
| `C-a x` | Close pane |
| `C-a {` / `C-a }` | Swap pane left / right |
| `C-a Opt-Arrow` | Resize pane in arrow direction |
| `C-a Space` | Cycle pane layouts |

### Copy Mode (vi)

| Key | Action |
|-----|--------|
| `C-a [` | Enter copy mode |
| `v` | Begin selection |
| `y` | Yank selection (tmux-yank) |
| `q` | Exit copy mode |
| `/` | Search forward |
| `?` | Search backward |

### Sessions

| Key | Action |
|-----|--------|
| `C-a d` | Detach |
| `C-a s` | List sessions |
| `C-a $` | Rename session |
| `C-a (` / `C-a )` | Previous / next session |
| `C-a C-s` | Save session (resurrect) |
| `C-a C-r` | Restore session (resurrect) |

Sessions auto-save every 15 minutes via continuum.

---

## Cross-Tool Navigation

`Ctrl-h/j/k/l` moves seamlessly between tmux panes **and** Neovim splits thanks to vim-tmux-navigator. No prefix needed.

| Key | Action |
|-----|--------|
| `C-h` | Move left |
| `C-j` | Move down |
| `C-k` | Move up |
| `C-l` | Move right |

---

## Neovim

Leader key: `,` (comma)

### Navigation & Search

| Key | Action |
|-----|--------|
| `,f` or `,p` | Find files (fzf) |
| `,g` | Live grep (fzf) |
| `,b` or `C-b` | Browse buffers (fzf) |
| `,n` | Toggle file tree |
| `C-w v` | Split vertically |
| `C-w s` | Split horizontally |
| `C-w o` | Close all other splits |

### Editing

| Key | Action |
|-----|--------|
| `m` | Cut (replaces `d` via cutlass) |
| `mm` | Cut line |
| `M` | Cut to end of line |
| `d` | Delete without yanking |
| `p` (visual) | Paste over selection without yanking |
| `cs"'` | Change surrounding `"` to `'` (surround) |
| `ds"` | Delete surrounding `"` |
| `ysiw"` | Add `"` around word |
| `C-j` | Prettify JSON with jq |
| `C-s` | Clear search highlight |
| `gc` | Comment/uncomment (built-in) |

### LSP

| Key | Action |
|-----|--------|
| `gd` | Go to definition |
| `gr` | Find references |
| `K` | Hover documentation |
| `,rn` | Rename symbol |
| `,ca` | Code action |
| `]d` / `[d` | Next / previous diagnostic |

### Completion (blink.cmp)

| Key | Action |
|-----|--------|
| `Tab` | Next completion / snippet forward |
| `S-Tab` | Previous completion / snippet backward |
| `Enter` | Accept completion |
| `C-Space` | Show completions / toggle docs |
| `C-e` | Cancel completion |
| `C-d` / `C-u` | Scroll docs down / up |

### AI (Claude Code)

| Key | Action |
|-----|--------|
| `,ac` | Toggle Claude Code |
| `,af` | Focus Claude Code |
| `,aC` | Continue mode |
| `,ar` | Resume |
| `,ab` | Add current file |
| `,as` (visual) | Send selection |
| `,aa` | Accept diff |
| `,ad` | Deny diff |

### Testing (vim-test)

| Command | Action |
|---------|--------|
| `:TestNearest` | Run nearest test |
| `:TestFile` | Run current file's tests |
| `:TestSuite` | Run full test suite |
| `:TestLast` | Re-run last test |

---

## Fish Shell

Vi-mode is enabled. Press `Esc` to enter normal mode, `i` to return to insert mode.

| Key | Action |
|-----|--------|
| `z <dir>` | Smart cd (zoxide) |
| `Esc` | Enter vi normal mode |
| `i` / `a` | Insert / append |
| `/` | Search command history |
| `v` (normal) | Open command in `$EDITOR` |

---

## Alacritty

| Key | Action |
|-----|--------|
| `Shift+Enter` | Insert newline in CLI tools (Claude Code, Codex) |
| `Option+key` | Send alt-key sequences (both Option keys) |
