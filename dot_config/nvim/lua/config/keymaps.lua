local map = vim.keymap.set

-- Cut mappings for vim-cutlass (remap d to m for actual cut)
map("n", "m", "d")
map("x", "m", "d")
map("n", "mm", "dd")
map("n", "M", "D")

-- Prettify JSON with jq
map("n", "<C-j>", ":%!jq<CR>", { silent = true })

-- Paste over selection without yanking
map("x", "p", '"_dP')

-- Clear search highlight
map("n", "<C-S>", ":nohlsearch<CR>", { silent = true })

-- Diagnostics
map("n", "]d", vim.diagnostic.goto_next, { desc = "Next diagnostic" })
map("n", "[d", vim.diagnostic.goto_prev, { desc = "Prev diagnostic" })
