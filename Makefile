# Bootstrap a fresh macOS machine with dotfiles dependencies.
# Run: chezmoi cd && make

# Core tools required by the dotfiles
brew:
	brew install fish neovim tmux starship chezmoi
	brew install fzf ripgrep tree-sitter-cli jq git-delta zoxide
	brew install rbenv ruby-build uv

# Font used by Ghostty and Neovim
font:
	brew install --cask font-meslo-lg-nerd-font

# Terminal
terminal:
	brew install --cask ghostty

# Tmux Plugin Manager
tpm:
	git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Rust
rust:
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Set fish as default shell
shell:
	echo /opt/homebrew/bin/fish | sudo tee -a /etc/shells
	chsh -s /opt/homebrew/bin/fish

# Install Neovim plugins and LSP servers
nvim:
	nvim --headless "+Lazy install" +qa

# Markdown to PDF tool (puppeteer + marked)
mdpdf:
	cd ~/.local/share/mdpdf && npm install

# Everything for a fresh machine
all: brew font terminal tpm rust shell nvim mdpdf
	@echo "Done. Open Ghostty and run: tmux, then prefix+I to install tmux plugins."

.PHONY: brew font terminal tpm rust shell nvim mdpdf all
