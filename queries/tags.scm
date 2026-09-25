(grammar_rule
 rule_def:  (lhs rule_name: (nonterminal)) @name) @definition.class

(grammar_rule
  action_def: (named_action (action_name) @name)) @definition.interface

(ditto_rule
  action_def: (named_action (action_name) @name)) @definition.interface

(grammar_rule
  (rhs rule_name: (terminal) @name)) @reference.enum

(grammar_rule
  (rhs rule_name: (multiterminal (terminal) @name))) @reference.enum

(ditto_rule
  (rhs rule_name: (terminal) @name)) @reference.enum

(ditto_rule
  (rhs rule_name: (multiterminal (terminal) @name))) @reference.enum

(grammar_rule
  (rhs rule_name: (nonterminal) @name)) @reference.class

(ditto_rule
  (rhs rule_name: (nonterminal) @name)) @reference.class

(directive
  (terminal) @name) @reference.enum

(directive
  (multiterminal (terminal) @name)) @reference.enum

(precedence_mark
  (terminal) @name) @reference.enum

(directive
  action_impl: (named_action (action_name) @name)) @reference.implementation
