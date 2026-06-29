# dotfiles

macOS dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## What's included

- **Neovim** — modular Lua config with lazy.nvim, native LSP, blink.cmp, treesitter, fzf-lua, conform.nvim
- **Fish** — vi mode, OneDark syntax theme, Starship prompt, zoxide
- **Ghostty** — Atom One Dark theme, MesloLGS Nerd Font Mono, quick terminal, shell integration
- **tmux** — C-a prefix, vi mode, OneDark status bar with powerline separators, resurrect + continuum, Claude Code session persistence (re-resumes every pane to its exact session on reboot)
- **Starship** — cross-shell prompt (fish, bash, zsh) with shell name indicator
- **Git** — GPG-signed commits, delta syntax-highlighted diffs, histogram algorithm
- **Bash / Zsh** — minimal configs with Starship and `EDITOR=nvim`
- **mdpdf** — custom markdown-to-PDF converter with Splendor editorial theme

## Install

```sh
# Install Homebrew, then:
brew install chezmoi
chezmoi init https://github.com/jesseposner/dotfiles.git
chezmoi apply

# Install dependencies
chezmoi cd && make all
```

## Keybindings

See [KEYBINDINGS.md](KEYBINDINGS.md) for the full cheatsheet — tmux, Neovim, Fish, and cross-tool navigation.

## Update

```sh
chezmoi update
```
