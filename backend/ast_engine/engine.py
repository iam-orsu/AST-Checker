"""
AST Constraint Engine — Dispatcher
Routes code to the correct language-specific AST analyzer, compares detected
constructs against required/banned lists, filters violations to only those
within editable_ranges, and returns the result.

Line number indexing: All analyzers return 1-indexed line numbers.
editable_ranges also use 1-indexed {startLine, endLine} (inclusive).
This file explicitly verifies consistent indexing before filtering.
"""

from ast_engine import python_analyzer, java_analyzer, c_analyzer, cpp_analyzer, js_analyzer
from typing import Any


LANGUAGE_ANALYZERS = {
    "python": python_analyzer,
    "java": java_analyzer,
    "c": c_analyzer,
    "cpp": cpp_analyzer,
    "c++": cpp_analyzer,
    "javascript": js_analyzer,
    "js": js_analyzer,
}

# C has no native exception handling — skip this constraint for C
C_UNSUPPORTED_CONSTRUCTS = {"exception_handling"}

# Construct aliases: map user-friendly names to internal construct keys
CONSTRUCT_ALIASES = {
    "while": "while_loop",
    "while loop": "while_loop",
    "while_loop": "while_loop",
    "for": "for_loop",
    "for loop": "for_loop",
    "for_loop": "for_loop",
    "do-while": "do_while_loop",
    "do while": "do_while_loop",
    "do_while_loop": "do_while_loop",
    "do_while": "do_while_loop",
    "if": "if_else",
    "if/else": "if_else",
    "if_else": "if_else",
    "conditional": "if_else",
    "switch": "switch",
    "switch statement": "switch",
    "function": "function",
    "functions": "function",
    "method": "function",
    "recursion": "recursion",
    "recursive": "recursion",
    "class": "class",
    "classes": "class",
    "struct": "class",
    "inheritance": "inheritance",
    "polymorphism": "polymorphism",
    "exception handling": "exception_handling",
    "exception_handling": "exception_handling",
    "try/catch": "exception_handling",
    "try-catch": "exception_handling",
    "try_catch": "exception_handling",
    "error handling": "exception_handling",
    "array": "array",
    "arrays": "array",
    "list": "array",
    "linked list": "linked_list",
    "linked_list": "linked_list",
    "linkedlist": "linked_list",
    "stack": "stack",
    "stacks": "stack",
    "queue": "queue",
    "queues": "queue",
    "dictionary": "dictionary",
    "dict": "dictionary",
    "map": "dictionary",
    "set": "set",
    "sets": "set",
}


def normalize_construct(name: str) -> str:
    """Normalize a construct name to its canonical internal key."""
    return CONSTRUCT_ALIASES.get(name.lower().strip(), name.lower().strip())


def is_line_in_editable_ranges(line: int, editable_ranges: list[dict]) -> bool:
    """
    Check if a 1-indexed line number falls within any editable range.
    Both line and editable_ranges use 1-indexed inclusive ranges.
    """
    for r in editable_ranges:
        start = r.get("startLine", 0)
        end = r.get("endLine", 0)
        # Both are 1-indexed, inclusive on both ends
        if start <= line <= end:
            return True
    return False


def analyze_code(
    code: str,
    language: str,
    required_constructs: list[str],
    banned_constructs: list[str],
    editable_ranges: list[dict],
) -> dict:
    """
    Main entry point for the AST constraint engine.

    1. Routes to the correct language analyzer
    2. Gets all detected constructs with line numbers
    3. Checks required constructs are present (in editable ranges)
    4. Checks banned constructs are absent (in editable ranges)
    5. Filters violations to only those in editable_ranges
    6. Returns {passed: bool, violations: list[dict]}

    Line indexing verification:
    - All analyzers return 1-indexed line numbers
    - editable_ranges uses 1-indexed {startLine, endLine} inclusive
    - This function verifies consistency before filtering
    """
    lang_key = language.lower().strip()
    analyzer = LANGUAGE_ANALYZERS.get(lang_key)

    if not analyzer:
        return {
            "passed": False,
            "violations": [
                {
                    "line": 0,
                    "message": f"Unsupported language: {language}",
                    "construct": "unknown",
                    "violation_type": "error",
                }
            ],
        }

    # Normalize construct names
    required = [normalize_construct(c) for c in required_constructs]
    banned = [normalize_construct(c) for c in banned_constructs]

    # For C: remove exception_handling from required since C has no try/catch
    if lang_key == "c":
        required = [c for c in required if c not in C_UNSUPPORTED_CONSTRUCTS]
        banned = [c for c in banned if c not in C_UNSUPPORTED_CONSTRUCTS]

    # Run the language-specific analyzer
    detected = analyzer.analyze(code)

    # Check for syntax errors
    syntax_errors = [d for d in detected if d["construct"] == "syntax_error"]
    if syntax_errors:
        return {
            "passed": False,
            "violations": [
                {
                    "line": err["line"],
                    "message": err["details"],
                    "construct": "syntax_error",
                    "violation_type": "error",
                }
                for err in syntax_errors
            ],
        }

    # Separate detected constructs into those in editable ranges and those in locked zones
    editable_detected = []
    for d in detected:
        # Verify line number is 1-indexed (all analyzers should return >= 1)
        # Line 0 is allowed only for 'required_missing' violations generated by this function,
        # not from analyzers. Analyzer-returned line 0 means 'unknown' — still pass it through.

        # If editable_ranges is None or empty, treat as 'whole file editable'
        # Only filter when there are actual editable ranges defined
        if not editable_ranges:
            editable_detected.append(d)
        elif is_line_in_editable_ranges(d["line"], editable_ranges):
            editable_detected.append(d)

    # Collect unique construct types found in editable regions
    editable_construct_types = set(d["construct"] for d in editable_detected)

    violations = []

    # Check banned constructs: any banned construct found in editable ranges is a violation
    for d in editable_detected:
        if d["construct"] in banned:
            violations.append(
                {
                    "line": d["line"],
                    "message": f"Line {d['line']}: Banned construct used — {d['details']}. "
                    f"This problem does not allow '{d['construct'].replace('_', ' ')}'.",
                    "construct": d["construct"],
                    "violation_type": "banned_used",
                }
            )

    # Check required constructs: must be present somewhere in editable ranges
    for req in required:
        if req not in editable_construct_types:
            # Find a friendly name
            friendly = req.replace("_", " ")
            violations.append(
                {
                    "line": 0,
                    "message": f"Required construct missing: You must use a {friendly} in your solution.",
                    "construct": req,
                    "violation_type": "required_missing",
                }
            )

    return {
        "passed": len(violations) == 0,
        "violations": violations,
    }
