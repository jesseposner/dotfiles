# fish greeting
set -x fish_greeting ""

# fisher plugins
if not functions -q fisher
  set -q XDG_CONFIG_HOME; or set XDG_CONFIG_HOME ~/.config
  curl https://git.io/fisher --create-dirs -sLo $XDG_CONFIG_HOME/fish/functions/fisher.fish
  fish -c fisher
end

# onedark color for VI mode
set SPACEFISH_VI_MODE_COLOR abb2bf

# don't show VI mode
set SPACEFISH_VI_MODE_SHOW false

# set default editor
set -gx EDITOR nvim

# load rbenv
status --is-interactive; and source (rbenv init -|psub)
