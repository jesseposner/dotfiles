return {
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = "markdown",
    build = function()
      vim.fn["mkdp#util#install"]()
    end,
  },
  {
    "m-pilia/vim-mediawiki",
    ft = "mediawiki",
    init = function()
      vim.g.vim_mediawiki_site = "en.bitcoin.it"
    end,
  },
}
