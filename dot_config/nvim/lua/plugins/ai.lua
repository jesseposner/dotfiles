return {
  {
    "coder/claudecode.nvim",
    keys = {
      { "<leader>ac", "<cmd>ClaudeCode<CR>", desc = "Toggle Claude" },
      { "<leader>af", "<cmd>ClaudeCodeFocus<CR>", desc = "Focus Claude" },
      { "<leader>aC", "<cmd>ClaudeCode --continue<CR>", desc = "Claude continue" },
      { "<leader>ar", "<cmd>ClaudeCode --resume<CR>", desc = "Claude resume" },
      { "<leader>ab", "<cmd>ClaudeCodeAdd %<CR>", desc = "Add file to Claude" },
      { "<leader>as", "<cmd>ClaudeCodeSend<CR>", mode = "v", desc = "Send selection to Claude" },
      { "<leader>aa", "<cmd>ClaudeCodeDiffAccept<CR>", desc = "Accept diff" },
      { "<leader>ad", "<cmd>ClaudeCodeDiffDeny<CR>", desc = "Deny diff" },
    },
    opts = {},
  },
  { "folke/snacks.nvim", lazy = false, priority = 1000, opts = {} },
}
