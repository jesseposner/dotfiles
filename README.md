# dotfiles

macOS dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## What's included

- **Neovim** — modular Lua config with lazy.nvim, native LSP, blink.cmp, treesitter, fzf-lua, conform.nvim
- **Fish** — vi mode, OneDark syntax theme, Starship prompt
- **Alacritty** — OneDark color scheme, MesloLGS Nerd Font Mono
- **tmux** — C-a prefix, vi mode, OneDark status bar with powerline separators, TPM plugins
- **Starship** — cross-shell prompt (fish, bash, zsh) with shell name indicator
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
