local opt = vim.opt

opt.termguicolors = true
opt.number = true
opt.signcolumn = "yes"
opt.updatetime = 300
opt.showmode = false
opt.list = true
opt.cmdheight = 1

-- Clipboard
opt.clipboard = "unnamedplus"

-- No swap/backup, but enable persistent undo
opt.swapfile = false
opt.backup = false
opt.writebackup = false
opt.undofile = true

-- Disable netrw (nvim-tree replaces it)
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

-- Completion menu
opt.shortmess:append("c")

-- Show diagnostic float automatically on cursor hold
vim.diagnostic.config({
  float = { border = "rounded" },
})
vim.api.nvim_create_autocmd("CursorHold", {
  callback = function()
    vim.diagnostic.open_float(nil, { focusable = false })
  end,
})
