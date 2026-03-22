#!/usr/bin/env python3
"""Fuzz `%code { ... }` handling by comparing Zig validity to Tree-sitter parseability."""

from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IDENTS = [
    "alpha",
    "beta",
    "gamma",
    "delta",
    "trace_me",
    "Tokenizer",
    "ParseContext",
]

STRING_FRAGMENTS = [
    "",
    "plain",
    "}",
    "{{{s}}}",
    "// not comment",
    "quote: \\\"",
    "slashes: \\\\",
    "mix } // \\\" \\\\",
]

MULTILINE_FRAGMENTS = [
    "hello",
    "}",
    "\"quoted\"",
    "// not comment",
    "mix } \\\"",
]

QUOTED_IDENTS = [
    "@\"}\"",
    "@\"//\"",
    "@\"quoted name\"",
    "@\"mix } //\"",
]

CHAR_LITERALS = [
    "'a'",
    "'}'",
    "'\\n'",
    "'\\\\'",
    "'\\''",
]


def run(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def zig_valid(zig_file: Path) -> bool:
    result = run(["zig", "fmt", "--ast-check", str(zig_file)])
    return result.returncode == 0


def tree_sitter_valid(zy_file: Path) -> tuple[bool, str]:
    result = run(["tree-sitter", "parse", "-q", str(zy_file)])
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def rand_ident(rng: random.Random) -> str:
    return rng.choice(IDENTS)


def rand_string_literal(rng: random.Random) -> str:
    return '"' + rng.choice(STRING_FRAGMENTS) + '"'


def rand_multiline_string(rng: random.Random) -> str:
    count = rng.randint(1, 3)
    parts = [f"    \\\\{rng.choice(MULTILINE_FRAGMENTS)}" for _ in range(count)]
    return "const s =\n" + "\n".join(parts) + "\n;"


def rand_quoted_ident(rng: random.Random) -> str:
    return rng.choice(QUOTED_IDENTS)


def rand_expr(rng: random.Random) -> str:
    options = [
        "42",
        rand_string_literal(rng),
        rand_quoted_ident(rng),
        "true",
        f"struct {{ const x = {rand_string_literal(rng)}; }}",
    ]
    return rng.choice(options)


def rand_block_statement(rng: random.Random) -> str:
    lhs = rand_ident(rng)
    quoted = rand_quoted_ident(rng)
    string_lit = rand_string_literal(rng)
    char_lit = rng.choice(CHAR_LITERALS)
    statements = [
        f"const {lhs} = {string_lit};",
        f"const {lhs}: u8 = {char_lit};",
        f"const {lhs} = {quoted};",
        f"if (true) {{ const inner = {string_lit}; }}",
        f"while (false) {{ const inner = {rand_expr(rng)}; }}",
        f"// {rng.choice(STRING_FRAGMENTS)}",
        "comptime { const inner = \"}\"; }",
        "std.debug.print(\"{{{s}}}\", .{\"}\"});",
        "const s =\n    \\\\hello\n    \\\\}\n;",
    ]
    return rng.choice(statements)


def rand_toplevel_decl(rng: random.Random) -> str:
    lhs = rand_ident(rng)
    string_lit = rand_string_literal(rng)
    quoted = rand_quoted_ident(rng)
    decls = [
        f"const {lhs} = {string_lit};",
        f"const {quoted} = {rng.randint(0, 9)};",
        f"const {lhs}: u8 = {rng.choice(CHAR_LITERALS)};",
        f"const {lhs} = @import({string_lit});",
        rand_multiline_string(rng),
        (
            "pub fn f() void {\n"
            + "\n".join(f"    {rand_block_statement(rng)}" for _ in range(rng.randint(1, 5)))
            + "\n}"
        ),
    ]
    return rng.choice(decls)


def make_snippet(rng: random.Random) -> str:
    line_count = rng.randint(1, 6)
    lines = [rand_toplevel_decl(rng) for _ in range(line_count)]
    if rng.random() < 0.35:
        lines.append(f"const {rand_ident(rng)} = {rand_string_literal(rng)};")
    return "\n".join(lines)


def write_code_block(path: Path, code: str) -> None:
    path.write_text("%code {\n" + code + "\n}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of fuzz runs to execute. Each run uses seed + run_index.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print progress every N attempts. Use 0 to disable.",
    )
    parser.add_argument(
        "--keep-dir",
        type=Path,
        help="Directory to keep generated repros. Defaults to a temporary directory.",
    )
    return parser.parse_args()


def run_once(args: argparse.Namespace, seed: int, keep_dir: Path | None) -> int:
    rng = random.Random(seed)
    temp_dir_obj: tempfile.TemporaryDirectory[str] | None = None
    if keep_dir is None:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="zitron-scanner-fuzz-")
        keep_dir = Path(temp_dir_obj.name)
    else:
        keep_dir.mkdir(parents=True, exist_ok=True)

    attempted = 0
    zig_ok = 0

    try:
        for i in range(args.iterations):
            attempted += 1
            code = make_snippet(rng)
            zig_file = keep_dir / f"case-{i:05d}.zig"
            zy_file = keep_dir / f"case-{i:05d}.zy"
            zig_file.write_text(code + "\n", encoding="utf-8")

            if not zig_valid(zig_file):
                if args.progress_every and attempted % args.progress_every == 0:
                    print(f"attempted={attempted} zig_valid={zig_ok}")
                continue

            zig_ok += 1
            write_code_block(zy_file, code)
            ts_ok, ts_output = tree_sitter_valid(zy_file)
            if not ts_ok:
                print(f"Mismatch found after {attempted} attempts and {zig_ok} Zig-valid cases.", flush=True)
                print(f"Run seed: {seed}", flush=True)
                print(f"Reproducer Zig: {zig_file}", flush=True)
                print(f"Reproducer ZY:  {zy_file}", flush=True)
                if ts_output:
                    print("\nTree-sitter output:", flush=True)
                    print(ts_output, flush=True)
                return 1

            zig_file.unlink(missing_ok=True)
            zy_file.unlink(missing_ok=True)
            if args.progress_every and attempted % args.progress_every == 0:
                print(f"attempted={attempted} zig_valid={zig_ok}", flush=True)
    finally:
        if temp_dir_obj is None:
            pass
        elif not any(keep_dir.iterdir()):
            temp_dir_obj.cleanup()

    print(
        f"No mismatch found in {attempted} attempts "
        f"({zig_ok} Zig-valid cases), seed={seed}."
    , flush=True)
    if temp_dir_obj is None:
        print(f"Artifacts kept in {keep_dir}", flush=True)
    return 0


def main() -> int:
    args = parse_args()

    for run_index in range(args.runs):
        seed = args.seed + run_index
        keep_dir = args.keep_dir
        if keep_dir is not None and args.runs > 1:
            keep_dir = keep_dir / f"run-{run_index:03d}"

        if args.runs > 1:
            print(f"Starting run {run_index + 1}/{args.runs} with seed={seed}", flush=True)

        result = run_once(args, seed, keep_dir)
        if result != 0:
            return result

    return 0


if __name__ == "__main__":
    if shutil.which("zig") is None or shutil.which("tree-sitter") is None:
        print("Required commands missing: need both `zig` and `tree-sitter` on PATH.", file=sys.stderr, flush=True)
        sys.exit(2)
    sys.exit(main())
