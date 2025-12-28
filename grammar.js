/**
 * @file A Tree-sitter grammar for the Zitron grammar dialect
 * @author Sam Atman <atmanistan@gmail.com>
 * @license MIT
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

export default grammar({
  name: "zitron",

  extras: ($) => [/\s|\\\r?\n/, $.comment],

  externals: ($) => [$.zig_code],

  rules: {
    // TODO: add the actual grammar rules
    source_file: ($) => repeat($._declaration),

    _declaration: ($) => choice($.grammar_rule, $.ditto_rule, $.directive),

    grammar_rule: ($) =>
      seq(
        $._nonterminal_m_alias,
        "::=",
        optional(repeat($._production)),
        ".",
        optional($._action),
      ),

    ditto_rule: ($) =>
      seq(
        "``",
        optional("::="),
        optional(repeat($._production)),
        ".",
        optional($._action),
      ),

    directive: ($) => seq("%", $.directive_name, $._directive_defn),

    _production: ($) =>
      choice(
        $._nonterminal_m_alias,
        $._terminal_m_alias,
        $._multiterminal_m_alias,
      ),

    _nonterminal_m_alias: ($) =>
      seq(
        field("rule_name", $.nonterminal),
        field("alias", optional($._alias_paren)),
      ),

    _terminal_m_alias: ($) =>
      prec(
        2,
        seq(
          field("rule_name", $.terminal),
          field("alias", optional($._alias_paren)),
        ),
      ),

    _directive_defn: ($) =>
      choice($.code_block, $.string, $.number, $.identifier),

    _multiterminal_m_alias: ($) =>
      seq(
        field("rule_name", $.multiterminal),
        field("alias", optional($._alias_paren)),
      ),

    _alias_paren: ($) => seq("(", $.rule_alias, ")"),

    _action: ($) => choice($.code_block, $.named_action),

    code_block: ($) => seq("{", $.zig_code, "}"),

    named_action: ($) => seq($.action_name, $._act_aliases),

    _act_aliases: ($) =>
      seq(
        "(",
        optional(
          seq(
            optional($.rule_alias),
            ";",
            optional($.rule_alias),
            optional(repeat(seq(",", $.rule_alias))),
            optional(","),
          ),
        ),
        ")",
      ),

    nonterminal: ($) => /[a-z][a-zA-Z0-9_]*/,

    terminal: ($) => /[A-Z][a-zA-Z0-9_]*/,

    multiterminal: ($) =>
      seq($.terminal, repeat(seq(choice("|", "/"), $.terminal))),

    rule_alias: ($) => /[A-Za-z][A-Za-z0-9_]*/,

    identifier: ($) => /[A-Za-z][A-Za-z0-9_]*/,

    action_name: ($) => /@[a-z][a-zA-Z0-9_]*/,

    word: ($) => /[a-z]+/,

    directive_name: ($) =>
      choice(
        "name",
        "include",
        "impl",
        "code",
        "token_destructor",
        "default_destructor",
        "token_enum",
        "token_enum_integer",
        "trace_writer",
        "syntax_error",
        "parse_accept",
        "parse_error_type",
        "parse_failure",
        "stack_overflow",
        "extra_argument",
        "extra_context",
        "token_type",
        "default_type",
        "stack_size",
        "start_symbol",
        "left",
        "right",
        "nonassoc",
        "destructor",
        "type",
        "fallback",
        "token",
        "wildcard",
        "token_class",
      ),

    string: ($) => /"[^\"]*"/,

    number: ($) => /\d+/,

    comment: (_) =>
      token(
        choice(
          seq("//", /(\\+(.|\r?\n)|[^\\\n])*/),
          seq("/*", /[^*]*\*+([^/*][^*]*\*+)*/, "/"),
        ),
      ),
  },
});
