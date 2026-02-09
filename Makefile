# Bootstrap a fresh macOS machine with dotfiles dependencies.
# Run: chezmoi cd && make

# Core tools required by the dotfiles
brew:
	brew install fish neovim tmux starship chezmoi
	brew install fzf ripgrep tree-sitter-cli jq
	brew install rbenv ruby-build rustup uv

# Font used by Alacritty and Neovim
font:
	brew install --cask font-meslo-lg-nerd-font

# Terminal
terminal:
	brew install --cask alacritty

# Tmux Plugin Manager
tpm:
	git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Set fish as default shell
shell:
	echo /opt/homebrew/bin/fish | sudo tee -a /etc/shells
	chsh -s /opt/homebrew/bin/fish

# Install Neovim plugins and LSP servers
nvim:
	nvim --headless "+Lazy install" +qa

# Everything for a fresh machine
all: brew font terminal tpm shell nvim
	@echo "Done. Open Alacritty and run: tmux, then prefix+I to install tmux plugins."

.PHONY: brew font terminal tpm shell nvim all
