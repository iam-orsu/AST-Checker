"""
Java AST Analyzer
Uses the javalang library to parse Java source code into an AST.
All detection is done via proper AST node type checking — no keyword scanning.
"""

import javalang
from typing import Any


def analyze(code: str) -> list[dict]:
    """
    Parse Java code and return all detected constructs with line numbers.
    Returns a list of dicts: [{"construct": str, "line": int, "details": str}]
    """
    try:
        tree = javalang.parse.parse(code)
    except javalang.parser.JavaSyntaxError as e:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": f"Java syntax error: {str(e)}",
            }
        ]
    except Exception as e:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": f"Java parse error: {str(e)}",
            }
        ]

    found = []

    # Collect all method names for recursion detection
    method_names = set()
    for _, node in tree.filter(javalang.tree.MethodDeclaration):
        method_names.add(node.name)

    # Walk all nodes in the tree
    for path, node in tree:
        if isinstance(node, javalang.tree.WhileStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "while_loop",
                    "line": line,
                    "details": "while loop detected",
                }
            )

        elif isinstance(node, javalang.tree.ForStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "for_loop",
                    "line": line,
                    "details": "for loop detected",
                }
            )

        elif isinstance(node, javalang.tree.DoStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "do_while_loop",
                    "line": line,
                    "details": "do-while loop detected",
                }
            )

        elif isinstance(node, javalang.tree.IfStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "if_else",
                    "line": line,
                    "details": "if statement detected",
                }
            )

        elif isinstance(node, javalang.tree.SwitchStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "switch",
                    "line": line,
                    "details": "switch statement detected",
                }
            )

        elif isinstance(node, javalang.tree.MethodDeclaration):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "function",
                    "line": line,
                    "details": f"method '{node.name}' declared",
                }
            )

            # Check for recursion: method calling itself
            _check_recursion_in_method(node, node.name, found)

        elif isinstance(node, javalang.tree.ClassDeclaration):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "class",
                    "line": line,
                    "details": f"class '{node.name}' declared",
                }
            )

            # Check for inheritance
            if node.extends:
                extends_name = node.extends.name if hasattr(node.extends, 'name') else str(node.extends)
                found.append(
                    {
                        "construct": "inheritance",
                        "line": line,
                        "details": f"class '{node.name}' extends '{extends_name}'",
                    }
                )

            # Check for interface implementation (polymorphism)
            if node.implements:
                for impl in node.implements:
                    impl_name = impl.name if hasattr(impl, 'name') else str(impl)
                    found.append(
                        {
                            "construct": "polymorphism",
                            "line": line,
                            "details": f"class '{node.name}' implements '{impl_name}'",
                        }
                    )

        elif isinstance(node, javalang.tree.InterfaceDeclaration):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "class",
                    "line": line,
                    "details": f"interface '{node.name}' declared",
                }
            )

        elif isinstance(node, javalang.tree.TryStatement):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "exception_handling",
                    "line": line,
                    "details": "try statement detected",
                }
            )

        elif isinstance(node, javalang.tree.CatchClause):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "exception_handling",
                    "line": line,
                    "details": "catch clause detected",
                }
            )

        # Detect data structure usage via type references
        elif isinstance(node, javalang.tree.ReferenceType):
            type_name = node.name if hasattr(node, 'name') else ""
            line = node.position.line if node.position else 0

            if type_name in ("ArrayList", "LinkedList", "Vector", "List"):
                ds_type = "linked_list" if type_name == "LinkedList" else "array"
                found.append(
                    {
                        "construct": ds_type,
                        "line": line,
                        "details": f"{type_name} usage detected",
                    }
                )
            elif type_name in ("Stack", "ArrayDeque"):
                found.append(
                    {
                        "construct": "stack",
                        "line": line,
                        "details": f"{type_name} usage detected",
                    }
                )
            elif type_name in ("Queue", "PriorityQueue", "LinkedList", "Deque"):
                found.append(
                    {
                        "construct": "queue",
                        "line": line,
                        "details": f"{type_name} usage detected",
                    }
                )

        # Detect array declarations
        elif isinstance(node, javalang.tree.ArrayCreator):
            line = node.position.line if node.position else 0
            found.append(
                {
                    "construct": "array",
                    "line": line,
                    "details": "array creation detected",
                }
            )

    return found


def _check_recursion_in_method(method_node, method_name: str, found: list):
    """Check if a method contains a call to itself (recursion)."""
    for _, node in method_node:
        if isinstance(node, javalang.tree.MethodInvocation):
            if node.member == method_name:
                line = node.position.line if node.position else 0
                found.append(
                    {
                        "construct": "recursion",
                        "line": line,
                        "details": f"recursive call to '{method_name}' detected",
                    }
                )
                return
