return {
  "nvim-treesitter/nvim-treesitter",
  lazy = false,
  build = ":TSUpdate",
  config = function()
    require("nvim-treesitter").install({
      "go", "rust", "python", "typescript", "javascript",
      "lua", "markdown", "markdown_inline", "json", "yaml",
      "html", "css", "bash", "toml", "vim", "vimdoc",
    })
  end,
}
