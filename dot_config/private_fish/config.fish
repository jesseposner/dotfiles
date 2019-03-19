# fish greeting
set -x fish_greeting ""

# fisher plugins
if not functions -q fisher
  set -q XDG_CONFIG_HOME; or set XDG_CONFIG_HOME ~/.config
  curl https://git.io/fisher --create-dirs -sLo $XDG_CONFIG_HOME/fish/functions/fisher.fish
  fish -c fisher
end

# set spacefish prompts
set SPACEFISH_PROMPT_ORDER time user dir host git package node ruby golang php rust haskell julia docker aws venv conda pyenv dotnet kubecontext exec_time line_sep battery jobs exit_code char

# set default editor
set -gx EDITOR nvim

# load rbenv
status --is-interactive; and source (rbenv init -|psub)

# vi mode
fish_vi_key_bindings
