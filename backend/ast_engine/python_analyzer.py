"""
Python AST Analyzer
Uses the built-in ast module to detect code constructs by walking the syntax tree.
No keyword scanning — all detection is done via proper AST node type checking.
"""

import ast
from typing import Any


CONSTRUCT_MAP = {
    "while_loop": ast.While,
    "for_loop": ast.For,
    "if_else": ast.If,
    "switch": None,  # Python uses ast.Match (3.10+)
    "function": ast.FunctionDef,
    "class": ast.ClassDef,
    "exception_handling": ast.Try,
}


def analyze(code: str) -> list[dict]:
    """
    Parse Python code and return all detected constructs with line numbers.
    Returns a list of dicts: [{"construct": str, "line": int, "details": str}]
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [
            {
                "construct": "syntax_error",
                "line": e.lineno or 1,
                "details": f"Syntax error: {e.msg}",
            }
        ]

    found = []
    function_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            function_names.add(node.name)

    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            found.append(
                {
                    "construct": "while_loop",
                    "line": node.lineno,
                    "details": "while loop detected",
                }
            )

        elif isinstance(node, ast.For):
            found.append(
                {
                    "construct": "for_loop",
                    "line": node.lineno,
                    "details": "for loop detected",
                }
            )

        elif isinstance(node, ast.If):
            found.append(
                {
                    "construct": "if_else",
                    "line": node.lineno,
                    "details": "if/else conditional detected",
                }
            )

        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            found.append(
                {
                    "construct": "function",
                    "line": node.lineno,
                    "details": f"function '{node.name}' defined",
                }
            )

            _check_recursion(node, node.name, found)

        elif isinstance(node, ast.ClassDef):
            found.append(
                {
                    "construct": "class",
                    "line": node.lineno,
                    "details": f"class '{node.name}' defined",
                }
            )

            if node.bases:
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = ast.dump(base)
                    found.append(
                        {
                            "construct": "inheritance",
                            "line": node.lineno,
                            "details": f"class '{node.name}' inherits from '{base_name}'",
                        }
                    )

        elif isinstance(node, ast.Try):
            found.append(
                {
                    "construct": "exception_handling",
                    "line": node.lineno,
                    "details": "try/except block detected",
                }
            )

        # Detect Match statement (Python 3.10+ switch equivalent)
        elif hasattr(ast, "Match") and isinstance(node, ast.Match):
            found.append(
                {
                    "construct": "switch",
                    "line": node.lineno,
                    "details": "match/case statement detected (Python switch equivalent)",
                }
            )

        # Detect data structures
        elif isinstance(node, ast.List):
            found.append(
                {
                    "construct": "array",
                    "line": node.lineno,
                    "details": "list (array) literal detected",
                }
            )

        elif isinstance(node, ast.Dict):
            found.append(
                {
                    "construct": "dictionary",
                    "line": node.lineno,
                    "details": "dictionary detected",
                }
            )

        elif isinstance(node, ast.Set):
            found.append(
                {
                    "construct": "set",
                    "line": node.lineno,
                    "details": "set detected",
                }
            )

        # Detect deque, stack, queue imports and calls
        elif isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name == "deque":
                found.append(
                    {
                        "construct": "queue",
                        "line": node.lineno,
                        "details": "deque (double-ended queue) usage detected",
                    }
                )
            elif call_name in ("Queue", "PriorityQueue", "LifoQueue"):
                found.append(
                    {
                        "construct": "queue",
                        "line": node.lineno,
                        "details": f"{call_name} usage detected",
                    }
                )
            elif call_name == "LifoQueue":
                found.append(
                    {
                        "construct": "stack",
                        "line": node.lineno,
                        "details": "LifoQueue (stack) usage detected",
                    }
                )

        # Detect do-while pattern (Python doesn't have do-while natively)
        # A common pattern is: while True: ... if condition: break
        # We don't flag this as do_while_loop since Python lacks native do-while

    # Check for linked list patterns (class with self.next or self.val)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in ast.walk(node):
                if isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name):
                    if item.value.id == "self" and item.attr == "next":
                        found.append(
                            {
                                "construct": "linked_list",
                                "line": node.lineno,
                                "details": f"linked list node class '{node.name}' detected (has self.next)",
                            }
                        )
                        break

    # Detect stack usage via list append/pop pattern
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("append", "pop") and isinstance(
                    node.func.value, ast.Name
                ):
                    # Check if the variable was assigned as a list
                    found.append(
                        {
                            "construct": "stack",
                            "line": node.lineno,
                            "details": f"potential stack operation ({node.func.attr}) detected",
                        }
                    )

    return found


def _check_recursion(func_node: ast.FunctionDef, func_name: str, found: list):
    """Check if a function calls itself (recursion detection)."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name == func_name:
                found.append(
                    {
                        "construct": "recursion",
                        "line": node.lineno,
                        "details": f"recursive call to '{func_name}' detected",
                    }
                )
                return


def _get_call_name(node: ast.Call) -> str:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""
