(nonterminal) @identifier
(terminal) @constant
(rule_alias) @variable.parameter
(action_name) @function
(macro_terminal) @constant.macro
(macro_nonterminal) @constant.macro
(directive_name) @attribute.builtin
(impl_name) @type
(macro_name) @type
(arg_directive_name) @attribute.builtin
(token_directive_name) @attribute.builtin

(directive
  (arg_directive_name "type")
  (identifier) @type)

(directive
  (directive_name
    [
      "name"
      "token_type"
      "default_type"
      "parse_error_type"
      "token_enum"
      "token_enum_integer"
    ])
  (identifier) @type)

(comment) @spell
(string) @string.quoted.double
(number) @constant.numeric
["::=" "|" "/" "``" ] @operator
["%"] @operator.directive
[ "!" "&&" "||" ] @operator.boolean
["." ";" ","] @punctuation.delimiter
["{"] @punctuation.section.braces.begin
["}"] @punctuation.section.braces.end
(comment) @comment
