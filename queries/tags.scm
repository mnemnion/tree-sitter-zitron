(grammar_rule
 rule_def:  (lhs rule_name: (nonterminal)) @name) @definition.class

(grammar_rule
  action_def: (named_action (action_name) @name)) @definition.interface

(ditto_rule
  action_def: (named_action (action_name) @name)) @definition.interface

(grammar_rule
  (rhs rule_name: (nonterminal) @name)) @reference.class

(ditto_rule
  (rhs rule_name: (nonterminal) @name)) @reference.class

(directive
  action_impl: (named_action (action_name) @name)) @reference.implementation
