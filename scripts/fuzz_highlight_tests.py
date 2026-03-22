#!/usr/bin/env python3
"""Generate and repair highlight fixtures using a single tree-sitter binary.

This script uses `~/scripture/tree-sitter` as the default classifier:

* `pass` -> save the final fixture in `test/highlight`
* `fail` -> mutate assertion comments up to a bounded budget
* `fail` after the budget -> save the final fixture in `bucket/really-failed`
* `sus` (timeout) -> save the exact timed-out fixture in `sus`
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_TREE_SITTER = str(Path("~/scripture/tree-sitter").expanduser())
DEFAULT_TIMEOUT_SECONDS = 4
DEFAULT_MUTATION_BUDGET = 10
DEFAULT_TARGET_PASSES = 10
DEFAULT_MAX_ATTEMPTS = 40
DEFAULT_MAX_SUS = 10
DEFAULT_REPORT = REPO_ROOT / "reports" / "highlight_fuzz_report.jsonl"
GENERATED_PREFIX = "gen_"


DIRECTIVE_TYPES = ["%type", "%destructor"]
DIRECTIVE_IDENTS = ["expr", "term", "forms", "node"]
TYPE_NAMES = ["f64", "i64", "u8", "Token"]
STACK_SIZES = ["12", "16", "24", "32"]
TOKEN_DIRECTIVES = ["%left", "%right", "%nonassoc"]
TERMINALS = ["PLUS", "BAR", "BAZ", "STAR", "SLASH"]
NONTERMINALS = ["foo", "expr", "term", "node"]
ACTION_NAMES = ["@act", "@merge", "@reduce"]
MACRO_NAMES = ["foo", "TRACE", "NO_TRACE", "BAR"]
STRING_VALUES = ["hello", "world", "plain"]
COMMENT_VALUES = ["note", "todo", "trace"]


@dataclass(frozen=True)
class Candidate:
    family: str
    text: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--mutation-budget", type=int, default=DEFAULT_MUTATION_BUDGET)
    parser.add_argument("--tree-sitter-bin", default=DEFAULT_TREE_SITTER)
    parser.add_argument("--target-passes", type=int, default=DEFAULT_TARGET_PASSES)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--max-sus", type=int, default=DEFAULT_MAX_SUS)
    parser.add_argument("--family", action="append", dest="families")
    parser.add_argument("--report-jsonl", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--progress-every", type=int, default=1)
    return parser.parse_args()


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = "/tmp/tscache"
    env.setdefault("HOME", str(Path.home()))
    return env


def run(cmd: list[str], *, cwd: Path, timeout_seconds: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=command_env(),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )


def make_workspace() -> Path:
    workspace = Path(tempfile.mkdtemp(prefix="zitron-highlight-fuzz-"))
    shutil.copytree(
        REPO_ROOT,
        workspace,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git",
            "sus",
            "sus2",
            "bucket",
            "__pycache__",
            "*.pyc",
            ".DS_Store",
            "reports",
        ),
    )
    return workspace


def generated_name(family: str, seed: int, attempt: int) -> str:
    safe_family = family.replace("-", "_")
    return f"{GENERATED_PREFIX}{safe_family}_{seed}_{attempt:04d}.zy"


def next_available_path(directory: Path, filename: str) -> Path:
    path = directory / filename
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_r{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def persist_case(destination_dir: Path, filename: str, text: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / filename
    if destination.exists() and destination.read_text(encoding="utf-8") == text:
        return destination

    for candidate in sorted(destination_dir.glob(f"{destination.stem}_r*{destination.suffix}")):
        if candidate.read_text(encoding="utf-8") == text:
            return candidate

    destination = next_available_path(destination_dir, filename)
    write_text(destination, text)
    return destination


def append_report(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def case_summary(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def classify_case(workspace: Path, tree_sitter_bin: str, timeout_seconds: int) -> tuple[str, str]:
    try:
        result = run([tree_sitter_bin, "test"], cwd=workspace, timeout_seconds=timeout_seconds)
    except subprocess.TimeoutExpired:
        return "sus", "timeout"

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return "pass", output
    return "fail", output


def highlight_check(workspace: Path, tree_sitter_bin: str, candidate_path: Path) -> subprocess.CompletedProcess[str]:
    return run([tree_sitter_bin, "highlight", "--check", str(candidate_path)], cwd=workspace)


def make_directive_type(rng: random.Random) -> Candidate:
    directive = rng.choice(DIRECTIVE_TYPES)
    ident = rng.choice(DIRECTIVE_IDENTS)
    type_name = rng.choice(TYPE_NAMES)
    text = "\n".join(
        [
            f"{directive} {ident} {type_name}",
            "// ^ type",
            "//      ^ identifier",
        ]
    ) + "\n"
    return Candidate("directive_type", text, "Directive identifier shape")


def make_number(rng: random.Random) -> Candidate:
    size = rng.choice(STACK_SIZES)
    spaces = max(0, len("%stack_size ") - 1)
    text = "\n".join(
        [
            f"%stack_size {size}",
            "// ^ type",
            f"// {' ' * spaces}^ constant.numeric",
        ]
    ) + "\n"
    return Candidate("number", text, "Numeric directive shape")


def make_token_directive(rng: random.Random) -> Candidate:
    directive = rng.choice(TOKEN_DIRECTIVES)
    token_a = rng.choice(TERMINALS)
    token_b = rng.choice([t for t in TERMINALS if t != token_a])
    line = f"{directive} {token_a} {token_b}."
    good_delim_col = len(line) - 2
    delta = rng.choice([-1, 0, 1, 2])
    delim_col = max(0, good_delim_col + delta)
    text = "\n".join(
        [
            line,
            "// ^ type",
            "//      ^ constant",
            "//           ^ constant",
            f"// {' ' * delim_col}^ punctuation.delimiter",
        ]
    ) + "\n"
    return Candidate("token_directive", text, "Token directive punctuation drift")


def make_rule_action(rng: random.Random) -> Candidate:
    lhs = rng.choice(NONTERMINALS)
    rhs = rng.choice([n for n in NONTERMINALS if n != lhs]).upper()
    action = rng.choice(ACTION_NAMES)
    line = f"{lhs}(A) ::= {rhs}(B). {action}(A;B)"
    text = "\n".join(
        [
            line,
            "// <- identifier",
            "//    ^ variable.parameter",
            "//       ^ operator",
            "//           ^ constant",
            "//               ^ variable.parameter",
            "//                 ^ punctuation.delimiter",
            "//                   ^ function",
            "//                        ^ variable.parameter",
            "//                         ^ punctuation.delimiter",
            "//                          ^ variable.parameter",
        ]
    ) + "\n"
    return Candidate("rule_action", text, "Rule action with overlapping assertions")


def make_string_comment(rng: random.Random) -> Candidate:
    string_value = rng.choice(STRING_VALUES)
    comment_value = rng.choice(COMMENT_VALUES)
    text = "\n".join(
        [
            f'"{string_value}"',
            "// <- string.quoted.double",
            "",
            f"/* {comment_value} */",
            "// <- spell",
            "// <- comment",
        ]
    ) + "\n"
    return Candidate("string_comment", text, "Comment and spell overlap")


def make_braces(rng: random.Random) -> Candidate:
    mode = rng.choice(["stable", "end_assert", "bad_end"])
    lines = [
        "{ }",
        "// <- punctuation.section.braces.begin",
    ]
    if mode == "end_assert":
        lines.append("//^ punctuation.section.braces.end")
    elif mode == "bad_end":
        lines.append("//  <- punctuation.section.braces.end")
    return Candidate("braces", "\n".join(lines) + "\n", f"Brace case mode={mode}")


def make_macro_ops(rng: random.Random) -> Candidate:
    ident = rng.choice(MACRO_NAMES).lower()
    macro = rng.choice([m for m in MACRO_NAMES if m.upper() != ident.upper()])
    text = "\n".join(
        [
            f"%ifdef {ident} && !{macro.upper()}",
            "// ^ type",
            "//       ^ identifier",
            "//           ^ operator.boolean",
            "//              ^ operator.boolean",
        ]
    ) + "\n"
    return Candidate("macro_ops", text, "Macro boolean operator assertions")


FAMILY_BUILDERS = {
    "directive_type": make_directive_type,
    "number": make_number,
    "token_directive": make_token_directive,
    "rule_action": make_rule_action,
    "string_comment": make_string_comment,
    "braces": make_braces,
    "macro_ops": make_macro_ops,
}


def parse_assertion(line: str) -> tuple[str, int, str] | None:
    if not line.startswith("//"):
        return None
    rest = line[2:]
    if not rest.startswith(" "):
        return None
    rest = rest[1:]
    spaces = 0
    while spaces < len(rest) and rest[spaces] == " ":
        spaces += 1
    rest = rest[spaces:]
    if rest.startswith("^ "):
        return "^", spaces, rest[2:]
    if rest.startswith("<- "):
        return "<-", spaces, rest[3:]
    return None


def format_assertion(marker: str, spaces: int, capture: str) -> str:
    return "// " + (" " * max(0, spaces)) + marker + " " + capture


def mutation_candidates(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    assertion_indexes = [i for i, line in enumerate(lines) if parse_assertion(line) is not None]
    candidates: list[tuple[str, str]] = []

    for idx in reversed(assertion_indexes):
        parsed = parse_assertion(lines[idx])
        if parsed is None:
            continue
        marker, spaces, capture = parsed

        for delta in (-1, 1):
            new_lines = list(lines)
            new_lines[idx] = format_assertion(marker, spaces + delta, capture)
            candidates.append((f"shift_{delta:+d}", "\n".join(new_lines) + "\n"))

        toggled_marker = "<-" if marker == "^" else "^"
        new_lines = list(lines)
        new_lines[idx] = format_assertion(toggled_marker, spaces, capture)
        candidates.append(("toggle_marker", "\n".join(new_lines) + "\n"))

    if len(assertion_indexes) > 1:
        last_idx = assertion_indexes[-1]
        new_lines = lines[:last_idx] + lines[last_idx + 1 :]
        candidates.append(("drop_last_assertion", "\n".join(new_lines) + "\n"))

        for idx in reversed(assertion_indexes[:-1]):
            new_lines = lines[:idx] + lines[idx + 1 :]
            candidates.append(("drop_secondary_assertion", "\n".join(new_lines) + "\n"))

    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for op, candidate_text in candidates:
        if candidate_text in seen or candidate_text == text:
            continue
        seen.add(candidate_text)
        unique.append((op, candidate_text))
    return unique


def mutate_until_terminal(
    workspace: Path,
    workspace_file: Path,
    tree_sitter_bin: str,
    timeout_seconds: int,
    mutation_budget: int,
) -> tuple[str, str, list[dict[str, str]]]:
    original_text = workspace_file.read_text(encoding="utf-8")
    advisory = highlight_check(workspace, tree_sitter_bin, workspace_file)

    seen = {original_text}
    queue: list[tuple[str, str]] = mutation_candidates(original_text)
    history: list[dict[str, str]] = []

    while queue and len(history) < mutation_budget:
        op, candidate_text = queue.pop(0)
        if candidate_text in seen:
            continue
        seen.add(candidate_text)
        write_text(workspace_file, candidate_text)
        outcome, output = classify_case(workspace, tree_sitter_bin, timeout_seconds)
        history.append(
            {
                "operation": op,
                "outcome": outcome,
                "output": output,
                "text": candidate_text,
                "highlight_check_returncode": str(advisory.returncode),
            }
        )
        if outcome != "fail":
            return outcome, candidate_text, history

        for next_op, next_text in mutation_candidates(candidate_text):
            if next_text not in seen:
                queue.append((next_op, next_text))

    final_text = history[-1]["text"] if history else original_text
    return "fail", final_text, history


def run_case_in_workspace(
    source_text: str,
    filename: str,
    tree_sitter_bin: str,
    timeout_seconds: int,
    mutation_budget: int,
) -> dict:
    workspace = make_workspace()
    workspace_file = workspace / "test" / "highlight" / filename
    try:
        write_text(workspace_file, source_text)
        initial_outcome, initial_output = classify_case(workspace, tree_sitter_bin, timeout_seconds)
        final_outcome = initial_outcome
        final_output = initial_output
        final_text = source_text
        mutation_history: list[dict[str, str]] = []

        if initial_outcome == "fail":
            final_outcome, final_text, mutation_history = mutate_until_terminal(
                workspace,
                workspace_file,
                tree_sitter_bin,
                timeout_seconds,
                mutation_budget,
            )
            final_output = mutation_history[-1]["output"] if mutation_history else initial_output

        return {
            "initial_outcome": initial_outcome,
            "initial_output": initial_output,
            "final_outcome": final_outcome,
            "final_output": final_output,
            "final_text": final_text,
            "mutation_history": mutation_history,
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def process_generated_case(candidate: Candidate, filename: str, args: argparse.Namespace) -> dict:
    result = run_case_in_workspace(
        candidate.text,
        filename,
        args.tree_sitter_bin,
        args.timeout_seconds,
        args.mutation_budget,
    )

    saved_pass_path: str | None = None
    saved_sus_path: str | None = None
    saved_really_failed_path: str | None = None

    if result["final_outcome"] == "pass":
        saved = persist_case(REPO_ROOT / "test" / "highlight", filename, result["final_text"])
        saved_pass_path = str(saved.relative_to(REPO_ROOT))
    elif result["final_outcome"] == "sus":
        saved = persist_case(REPO_ROOT / "sus", filename, result["final_text"])
        saved_sus_path = str(saved.relative_to(REPO_ROOT))
    else:
        saved = persist_case(REPO_ROOT / "bucket" / "really-failed", filename, result["final_text"])
        saved_really_failed_path = str(saved.relative_to(REPO_ROOT))

    return {
        "family": candidate.family,
        "description": candidate.description,
        "original_text": candidate.text,
        "result": result,
        "saved_pass_path": saved_pass_path,
        "saved_sus_path": saved_sus_path,
        "saved_really_failed_path": saved_really_failed_path,
    }


def emit_report(
    args: argparse.Namespace,
    *,
    seed: int,
    attempt: int,
    filename: str,
    result: dict,
) -> None:
    case_result = result["result"]
    record = {
        "seed": seed,
        "attempt": attempt,
        "filename": filename,
        "family": result["family"],
        "description": result["description"],
        "initial_outcome": case_result["initial_outcome"],
        "outcome": case_result["final_outcome"],
        "initial_output": case_result["initial_output"],
        "final_output": case_result["final_output"],
        "mutation_history": [
            {
                "operation": item["operation"],
                "outcome": item["outcome"],
                "output": item["output"],
            }
            for item in case_result["mutation_history"]
        ],
        "saved_pass_path": result["saved_pass_path"],
        "saved_sus_path": result["saved_sus_path"],
        "saved_really_failed_path": result["saved_really_failed_path"],
        "original_text": result["original_text"],
        "final_text": case_result["final_text"],
    }
    append_report(args.report_jsonl, record)


def run_generation(args: argparse.Namespace) -> dict[str, int]:
    rng = random.Random(args.seed)
    families = args.families or list(FAMILY_BUILDERS)
    builders = [FAMILY_BUILDERS[family] for family in families]
    counts = {"pass": 0, "sus": 0, "really_failed": 0, "repaired": 0, "attempts": 0}

    for attempt in range(args.max_attempts):
        if counts["pass"] >= args.target_passes or counts["sus"] >= args.max_sus:
            break

        builder = builders[attempt % len(builders)]
        candidate = builder(rng)
        filename = generated_name(candidate.family, args.seed, attempt)
        result = process_generated_case(candidate, filename, args)
        emit_report(args, seed=args.seed, attempt=attempt, filename=filename, result=result)

        counts["attempts"] += 1
        if result["saved_pass_path"] is not None:
            counts["pass"] += 1
            if result["result"]["initial_outcome"] != "pass":
                counts["repaired"] += 1
        elif result["saved_sus_path"] is not None:
            counts["sus"] += 1
        elif result["saved_really_failed_path"] is not None:
            counts["really_failed"] += 1

        if args.progress_every and (attempt + 1) % args.progress_every == 0:
            print(
                f"attempt={attempt + 1} family={candidate.family} "
                f"initial={result['result']['initial_outcome']} outcome={result['result']['final_outcome']} "
                f"pass={result['saved_pass_path'] or 'none'} "
                f"sus={result['saved_sus_path'] or 'none'} "
                f"really_failed={result['saved_really_failed_path'] or 'none'}",
                flush=True,
            )

    return counts


def main() -> int:
    args = parse_args()
    if not Path(args.tree_sitter_bin).expanduser().exists():
        print(f"tree-sitter binary not found: {args.tree_sitter_bin}", flush=True)
        return 2

    counts = run_generation(args)
    print(case_summary(counts), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
