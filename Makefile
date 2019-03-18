font:
	brew tap caskroom/fonts
	brew cask install font-fira-code

vim-plug:
	curl -fLo ~/.local/share/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

TPM:
	git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

fisher:
	curl https://git.io/fisher --create-dirs -sLo ~/.config/fish/functions/fisher.fish
