package tree_sitter_zitron_test

import (
	"testing"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	tree_sitter_zitron "github.com/mnemnion/tree-sitter-zitron/bindings/go"
)

func TestCanLoadGrammar(t *testing.T) {
	language := tree_sitter.NewLanguage(tree_sitter_zitron.Language())
	if language == nil {
		t.Errorf("Error loading Zitron Parser grammar")
	}
}
