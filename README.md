# dotfiles

macOS dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## What's included

- **Neovim** — modular Lua config with lazy.nvim, native LSP, blink.cmp, treesitter, fzf-lua, conform.nvim
- **Fish** — vi mode, OneDark syntax theme, Starship prompt, zoxide
- **Alacritty** — OneDark color scheme, MesloLGS Nerd Font Mono
- **tmux** — C-a prefix, vi mode, OneDark status bar with powerline separators, resurrect + continuum
- **Starship** — cross-shell prompt (fish, bash, zsh) with shell name indicator
- **Git** — GPG-signed commits, delta syntax-highlighted diffs, histogram algorithm
- **Bash / Zsh** — minimal configs with Starship and `EDITOR=nvim`

## Install

```sh
# Install Homebrew, then:
brew install chezmoi
chezmoi init https://github.com/jesseposner/dotfiles.git
chezmoi apply

# Install dependencies
chezmoi cd && make all
```

## Update

```sh
chezmoi update
```
