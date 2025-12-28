/**
 * @file A Tree-sitter grammar for the Zitron grammar dialect
 * @author Sam Atman <atmanistan@gmail.com>
 * @license MIT
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

export default grammar({
  name: "zitron",

  rules: {
    // TODO: add the actual grammar rules
    source_file: $ => "hello"
  }
});
