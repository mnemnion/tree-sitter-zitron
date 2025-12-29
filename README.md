# Tree-sitter for Zitron

A pleasantly-functional [Treesitter](https://tree-sitter.github.io/tree-sitter/) grammar
for the [Zitron](https://github.com/mnemnion/zitron) LALR(1) parser
generator.  Alpha edition.

## Use

Mostly you're on your own there.

If you're using Neovim, and [Lazy](https://github.com/folke/lazy.nvim), this
might work:

```lua
{
  "mnemnion/tree-sitter-zitron",
  dependencies = { "nvim-treesitter/nvim-treesitter" },
  build = ":TSInstall zitron",
}
```

