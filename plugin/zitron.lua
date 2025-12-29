local ok, parsers = pcall(require, "nvim-treesitter.parsers")
if ok then
	local parser_config = parsers.get_parser_configs()
	parser_config.zitron = parser_config.zitron or {}
	parser_config.zitron.install_info = {
		url = "https://github.com/mnemnion/tree-sitter-zitron",
		files = { "src/parser.c", "src/scanner.c" },
		branch = "trunk",
	}
	parser_config.zitron.filetype = "zy"
end

vim.filetype.add({
	extension = { zy = "zitron" },
})
