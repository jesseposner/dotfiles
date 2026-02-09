# Suppress greeting
set -g fish_greeting

# Default editor
set -gx EDITOR nvim

# vi mode
fish_vi_key_bindings

# Disable blinking cursor
set fish_cursor_unknown block

# Homebrew
eval (/opt/homebrew/bin/brew shellenv)

# PATH
fish_add_path $HOME/.local/bin
fish_add_path "$HOME/.volta/bin"
set -gx VOLTA_HOME "$HOME/.volta"

# rbenv
status --is-interactive; and source (rbenv init -|psub)

# Cargo/Rust (loaded via conf.d/rustup.fish)

# OrbStack
source ~/.orbstack/shell/init2.fish 2>/dev/null || :

# Starship prompt
starship init fish | source
