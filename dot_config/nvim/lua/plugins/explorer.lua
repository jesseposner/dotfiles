return {
  "nvim-tree/nvim-tree.lua",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  keys = {
    { "<leader>n", "<cmd>NvimTreeToggle<CR>", desc = "Toggle file tree" },
  },
  cmd = "NvimTreeOpen",
  init = function()
    -- If nvim is opened with a directory argument, open nvim-tree instead of netrw
    if vim.fn.argc() == 1 and vim.fn.isdirectory(vim.fn.argv(0)) == 1 then
      vim.api.nvim_create_autocmd("VimEnter", {
        once = true,
        callback = function()
          vim.cmd("NvimTreeOpen")
        end,
      })
    end
  end,
  opts = {},
}
