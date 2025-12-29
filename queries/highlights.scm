(nonterminal) @identifier
(terminal) @constant
(rule_alias) @variable.parameter
(action_name) @function
(macro_terminal) @constant.macro
(macro_nonterminal) @constant.macro
(directive_name) @type
(impl_name) @type
(macro_name) @type
(arg_directive_name) @type
(token_directive_name) @type
(comment) @spell
(string) @string.quoted.double
(number) @constant.numeric
["::=" "|" "/" "``" ] @operator
[ "!" "&&" "||" ] @operator.boolean
["." ";" ","] @punctuation.delimiter
["{"] @punctuation.section.braces.begin
["}"] @punctuation.section.braces.end
(comment) @comment

