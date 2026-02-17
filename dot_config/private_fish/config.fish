# Suppress greeting
set -g fish_greeting

# Default editor
set -gx EDITOR nvim

# GPG signing (for git commits)
set -gx GPG_TTY (tty)

# vi mode
fish_vi_key_bindings

# Disable blinking cursor
set fish_cursor_unknown block

# Homebrew (macOS only)
if test -x /opt/homebrew/bin/brew
    eval (/opt/homebrew/bin/brew shellenv)
end

# PATH
fish_add_path $HOME/.local/bin

# Volta (if installed)
if test -d "$HOME/.volta/bin"
    fish_add_path "$HOME/.volta/bin"
    set -gx VOLTA_HOME "$HOME/.volta"
end

# rbenv (if installed)
if command -q rbenv
    status --is-interactive; and source (rbenv init -|psub)
end

# OrbStack (macOS only)
source ~/.orbstack/shell/init2.fish 2>/dev/null || :

# Zoxide (smart cd)
zoxide init fish | source

# Starship prompt
starship init fish | source
