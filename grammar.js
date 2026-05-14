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

  // We only have one external token, but the fake one prevents
  // it from being used in error recovery.
  externals: ($) => [$.zig_code, $.spurious],

  rules: {
    source_file: ($) => repeat($._declaration),

    _declaration: ($) =>
      choice($.grammar_rule, $.ditto_rule, $.directive, $.bad_directive),

    grammar_rule: ($) =>
      seq(
        field("rule_def", $.lhs),
        "::=",
        optional($.rhs),
        ".",
        optional($._action),
      ),

    ditto_rule: ($) =>
      seq("``", optional("::="), optional($.rhs), ".", optional($._action)),

    directive: ($) =>
      choice(
        $._ordinary_directive,
        $._impl_directive,
        $._macro_directive,
        $._arg_directive,
        $._token_directive,
        $._token_class_directive,
      ),

    bad_directive: ($) =>
      seq("%", alias($.identifier, $.bad_directive_name), $._directive_defn),

    _production: ($) =>
      choice(
        $._nonterminal_m_alias,
        $._terminal_m_alias,
        $._multiterminal_m_alias,
      ),

    lhs: ($) => $._nonterminal_m_alias,

    rhs: ($) => repeat1($._production),

    _nonterminal_m_alias: ($) =>
      seq(
        field("rule_name", $.nonterminal),
        field("alias", optional($._alias_paren)),
      ),

    _terminal_m_alias: ($) =>
      prec.left(
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

    _action: ($) => choice($.code_block, field("action_def", $.named_action)),

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

    _ordinary_directive: ($) => seq("%", $.directive_name, $._directive_defn),

    _impl_directive: ($) =>
      seq(
        "%",
        alias("impl", $.impl_name),
        field("action_impl", $.named_action),
        $.code_block,
      ),

    _arg_directive: ($) =>
      seq("%", $.arg_directive_name, $._grammar_particle, $._directive_defn),

    _grammar_particle: ($) => choice($.nonterminal, $.terminal),

    _token_directive: ($) =>
      seq("%", $.token_directive_name, repeat($._grammar_particle), "."),

    _token_class_directive: ($) =>
      seq(
        "%",
        alias("token_class", $.impl_name),
        $.nonterminal,
        $.multiterminal,
        ".",
      ),

    _macro_directive: ($) =>
      prec.left(seq("%", $.macro_name, optional($._macro_args))),

    _macro_args: ($) =>
      repeat1(choice(seq("(", $._macro_element, ")"), $._macro_element)),

    _macro_element: ($) =>
      choice(
        alias($.nonterminal, $.macro_nonterminal),
        alias($.terminal, $.macro_terminal),
        "&&",
        "||",
        "!",
      ),

    nonterminal: ($) => /[a-z][a-zA-Z0-9_]*/,

    terminal: ($) => /[A-Z][a-zA-Z0-9_]*/,

    multiterminal: ($) =>
      prec.left(3, seq($.terminal, repeat1(seq(choice("|", "/"), $.terminal)))),

    rule_alias: ($) => /[A-Za-z][A-Za-z0-9_]*/,

    identifier: ($) => /[A-Za-z][A-Za-z0-9_]*/,

    action_name: ($) => /@[a-z][a-zA-Z0-9_]*/,

    word: ($) => /[a-z_]+/,

    directive_name: ($) =>
      choice(
        "name",
        "include",
        "code",
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
        "wildcard",
        "token_destructor",
        "default_destructor",
      ),

    arg_directive_name: ($) => choice("type", "destructor"),

    token_directive_name: ($) =>
      choice("left", "right", "nonassoc", "token", "fallback"),

    macro_name: ($) => choice("if", "ifdef", "ifndef", "else", "endif"),

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
