" Specify a directory for plugins
" - For Neovim: ~/.local/share/nvim/plugged
" - Avoid using standard Vim directory names like 'plugin'
call plug#begin('~/.local/share/nvim/plugged')

" Make sure you use single quotes
Plug 'tpope/vim-sensible'
Plug 'joshdick/onedark.vim'
Plug '/usr/local/opt/fzf'
Plug 'junegunn/fzf.vim'
Plug 'scrooloose/nerdtree'
Plug 'sheerun/vim-polyglot'
Plug 'w0rp/ale'
Plug 'airblade/vim-gitgutter'
Plug 'neoclide/coc.nvim', {'tag': '*', 'do': 'yarn install'}
Plug 'terryma/vim-multiple-cursors'
Plug 'itchyny/lightline.vim'
Plug 'Shougo/unite.vim'
Plug 'Shougo/vimproc.vim', {'do' : 'make'}

" Initialize plugin system
call plug#end()

if (has("nvim"))
  "For Neovim 0.1.3 and 0.1.4 < https://github.com/neovim/neovim/pull/2198 >
  let $NVIM_TUI_ENABLE_TRUE_COLOR=1
endif
"For Neovim > 0.1.5 and Vim > patch 7.4.1799 < https://github.com/vim/vim/commit/61be73bb0f965a895bfb064ea3e55476ac175162 >
"Based on Vim patch 7.4.1770 (`guicolors` option) < https://github.com/vim/vim/commit/8a633e3427b47286869aa4b96f2bfc1fe65b25cd >
" < https://github.com/neovim/neovim/wiki/Following-HEAD#20160511 >
if (has("termguicolors"))
  set termguicolors
endif

syntax on
colorscheme onedark

" change the mapleader from \ to ,
let mapleader=","

nmap <leader>n :NERDTreeToggle<cr>
nmap <leader>f :FZF<cr>

" Use tab for trigger completion with characters ahead and navigate.
" Use command ':verbose imap <tab>' to make sure tab is not mapped by other plugin.
inoremap <silent><expr> <TAB>
      \ pumvisible() ? "\<C-n>" :
      \ <SID>check_back_space() ? "\<TAB>" :
      \ coc#refresh()
inoremap <expr><S-TAB> pumvisible() ? "\<C-p>" : "\<C-h>"

function! s:check_back_space() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction

" Disable mode status because it will be displayed by lightline.
set noshowmode

" onedark airline theme
let g:lightline = {
  \ 'colorscheme': 'onedark',
  \ }

" Show whitespace as characters
set list

" UNITE.VIM
call unite#custom#profile('searcher', 'context', {
      \ 'start_insert' : 1,
      \ 'update_time'  : 1,
      \ 'filters'      : 'sorter_rank'
      \})
call unite#custom#source('file_rec/async,file_rec/git,file_rec/neovim', 'ignore_globs', [])
call unite#custom#source('file_rec,file_rec/async,file_rec/git,file_rec/neovim', 'max_candidates', 1000)

nnoremap <C-p> :Unite -toggle -profile-name=searcher -buffer-name=search file_rec/neovim<CR>
nnoremap <C-b> :Unite -toggle -buffer-name=buffer buffer<CR>
nnoremap <C-_> :Unite -toggle grep:. -buffer-name=grep-pwd<CR>
nnoremap <C-\> :Unite -toggle grep -buffer-name=grep-buffer<CR>

let g:unite_data_directory             = '~/tmp/unite-cache'
let g:unite_source_grep_max_candidates = 200
let g:unite_redraw_hold_candidates     = 50000
let g:unite_source_rec_max_cache_files = 50000

" grep
let g:unite_source_grep_command       = 'ag'
let g:unite_source_grep_default_opts  = '--nogroup --nocolor -S'
let g:unite_source_grep_recursive_opt = ''
" file_rec
let g:unite_source_file_rec_max_cache_files = 0
let g:unite_source_rec_async_command        = ['ag', '--follow', '--nocolor', '--nogroup', '-i', '-g', '.']
