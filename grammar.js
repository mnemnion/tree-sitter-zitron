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
    source_file: ($) => repeat($._declaration),

    _declaration: ($) =>
      choice(
        $.grammar_rule,
        // $.directive
      ),

    grammar_rule: ($) =>
      seq($._nonterminal_m_alias, "::=", repeat($._production), "."),

    _nonterminal_m_alias: ($) =>
      seq(field("rule_name", $.nonterminal), field("alias", optional($.alias))),

    _production: ($) =>
      choice(
        $._nonterminal_m_alias,
        $._terminal_m_alias,
        $._multiterminal_m_alias,
      ),

    _terminal_m_alias: ($) =>
      prec(
        2,
        seq(field("rule_name", $.terminal), field("alias", optional($.alias))),
      ),

    _multiterminal_m_alias: ($) =>
      seq(
        field("rule_name", $.multiterminal),
        field("alias", optional($.alias)),
      ),

    nonterminal: ($) => /[a-z][a-zA-Z0-9_]*/,

    terminal: ($) => /[A-Z][a-zA-Z0-9_]*/,

    multiterminal: ($) =>
      seq($.terminal, repeat(seq(choice("|", "/"), $.terminal))),

    alias: ($) => seq("(", /[A-Za-z][A-Za-z0-9_]*/, ")"),
  },
});
