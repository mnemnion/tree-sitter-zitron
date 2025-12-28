#include "tree_sitter/parser.h"

enum TokenType {
    ZIG_BLOCK
};

void * tree_sitter_zitron_external_scanner_create() {
    return NULL;
}


void tree_sitter_zitron_external_scanner_destroy(void *payload) {
  // NOOP
}

unsigned tree_sitter_zitron_external_scanner_serialize(
  void *payload,
  char *buffer
) {
    return 0;
}

void tree_sitter_zitron_external_scanner_deserialize(
  void *payload,
  const char *buffer,
  unsigned length
) {
  // NOOP
}

static inline void advance(TSLexer *lexer) { lexer->advance(lexer, false); }

bool tree_sitter_zitron_external_scanner_scan(
  void *payload,
  TSLexer *lexer,
  const bool *valid_symbols
) {
    if (!valid_symbols[ZIG_BLOCK]) return false;
    lexer->result_symbol = ZIG_BLOCK;
    int depth = 0;
    while (lexer->lookahead) {
        if (lexer->lookahead == '}') {
            if (!depth) {
                return true;
            } else {
                --depth;
                advance(lexer);
            }
        } else if (lexer->lookahead == '{') {
            ++depth;
            advance(lexer);
        } else if (lexer->lookahead == '/') {
            advance(lexer);
            if (lexer->lookahead == '/') {
                /* Comment */
                while (lexer->lookahead != '\n' && lexer->lookahead) {
                    advance(lexer);
                }
                if (!lexer->lookahead) return true;
                advance(lexer);
            }
        } else if (lexer->lookahead == '\\') {
            advance(lexer);
            if (lexer->lookahead == '\\') {
                /* Multiline string */
                while (lexer->lookahead != '\n' && lexer->lookahead) {
                    advance(lexer);
                }
                if (!lexer->lookahead) return true;
                advance(lexer);
            }
        } else if (lexer->lookahead == '"') {
            /* Quoted string */
            advance(lexer);
            while (lexer->lookahead && lexer->lookahead != '"') {
                if (lexer->lookahead == '\\') {
                    advance(lexer);
                    if (!lexer->lookahead) return true;
                }
                advance(lexer);
            }
            if (!lexer->lookahead) return true;
            advance(lexer);
        } else if (lexer->lookahead == '\'') {
            /* Character literal */
            advance(lexer);
            while (lexer->lookahead && lexer->lookahead != '\'') {
                if (lexer->lookahead == '\\') {
                    advance(lexer);
                    if (!lexer->lookahead) return true;
                }
                advance(lexer);
            }
            if (!lexer->lookahead) return true;
            advance(lexer);
        } else {
            /* Everything else */
            advance(lexer);
        }
    }
    return true;
}

