"""
C AST Analyzer
Uses pycparser to parse C source code into an AST.
All detection is done via proper AST node type checking — no keyword scanning.

NOTE: C has no native exception handling (try/catch). This constraint is skipped
for C programs. The engine.py dispatcher handles this by not flagging
exception_handling as a missing required construct for C code.
"""

from pycparser import c_parser, c_ast
from typing import Any


class CAnalyzerVisitor(c_ast.NodeVisitor):
    """Visits all nodes in the C AST and records detected constructs."""

    def __init__(self):
        self.found = []
        self.function_names = set()
        self.current_function = None

    def visit_FuncDef(self, node):
        func_name = node.decl.name if node.decl else "unknown"
        line = node.coord.line if node.coord else 0

        self.function_names.add(func_name)
        self.found.append(
            {
                "construct": "function",
                "line": line,
                "details": f"function '{func_name}' defined",
            }
        )

        previous_function = self.current_function
        self.current_function = func_name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_While(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "while_loop",
                "line": line,
                "details": "while loop detected",
            }
        )
        self.generic_visit(node)

    def visit_For(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "for_loop",
                "line": line,
                "details": "for loop detected",
            }
        )
        self.generic_visit(node)

    def visit_DoWhile(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "do_while_loop",
                "line": line,
                "details": "do-while loop detected",
            }
        )
        self.generic_visit(node)

    def visit_If(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "if_else",
                "line": line,
                "details": "if statement detected",
            }
        )
        self.generic_visit(node)

    def visit_Switch(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "switch",
                "line": line,
                "details": "switch statement detected",
            }
        )
        self.generic_visit(node)

    def visit_FuncCall(self, node):
        line = node.coord.line if node.coord else 0

        call_name = ""
        if isinstance(node.name, c_ast.ID):
            call_name = node.name.name

        # Recursion detection: function calling itself by name
        if self.current_function and call_name == self.current_function:
            self.found.append(
                {
                    "construct": "recursion",
                    "line": line,
                    "details": f"recursive call to '{call_name}' detected",
                }
            )

        self.generic_visit(node)

    def visit_Struct(self, node):
        line = node.coord.line if node.coord else 0
        struct_name = node.name or "anonymous"
        self.found.append(
            {
                "construct": "class",
                "line": line,
                "details": f"struct '{struct_name}' detected (C equivalent of class)",
            }
        )

        # Check for linked list pattern: struct with a pointer to itself
        if node.decls:
            for decl in node.decls:
                if self._is_self_referencing_pointer(decl, node.name):
                    self.found.append(
                        {
                            "construct": "linked_list",
                            "line": line,
                            "details": f"linked list node struct '{struct_name}' detected (self-referencing pointer)",
                        }
                    )
                    break

        self.generic_visit(node)

    def visit_ArrayDecl(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "array",
                "line": line,
                "details": "array declaration detected",
            }
        )
        self.generic_visit(node)

    def visit_ArrayRef(self, node):
        line = node.coord.line if node.coord else 0
        self.found.append(
            {
                "construct": "array",
                "line": line,
                "details": "array access detected",
            }
        )
        self.generic_visit(node)

    def _is_self_referencing_pointer(self, decl, struct_name):
        """Check if a declaration is a pointer to the same struct type (linked list pattern)."""
        if not struct_name:
            return False
        try:
            if isinstance(decl, c_ast.Decl):
                type_node = decl.type
                if isinstance(type_node, c_ast.PtrDecl):
                    inner = type_node.type
                    if isinstance(inner, c_ast.TypeDecl):
                        if isinstance(inner.type, c_ast.Struct):
                            if inner.type.name == struct_name:
                                return True
        except Exception:
            pass
        return False


def analyze(code: str) -> list[dict]:
    """
    Parse C code and return all detected constructs with line numbers.
    Returns a list of dicts: [{"construct": str, "line": int, "details": str}]

    NOTE: C has no native exception handling (try/catch/finally).
    The 'exception_handling' construct will never be detected for C code.
    This is by design — the engine.py dispatcher accounts for this by not
    reporting exception_handling as a missing required construct for C.
    """
    parser = c_parser.CParser()

    # pycparser requires valid C with resolved includes.
    # We prepend minimal typedefs so common code can parse without preprocessing.
    preamble = """
typedef int size_t;
typedef int ssize_t;
typedef int bool;
typedef void FILE;
typedef int uint8_t;
typedef int uint16_t;
typedef int uint32_t;
typedef int uint64_t;
typedef int int8_t;
typedef int int16_t;
typedef int int32_t;
typedef int int64_t;
"""

    try:
        full_code = preamble + "\n" + code
        tree = parser.parse(full_code, filename="<user_code>")
    except Exception as e:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": f"C parse error: {str(e)}",
            }
        ]

    # Adjust line numbers: subtract preamble lines
    preamble_lines = preamble.count("\n")

    visitor = CAnalyzerVisitor()
    visitor.visit(tree)

    # Adjust line numbers to account for preamble
    adjusted = []
    for item in visitor.found:
        adjusted_line = item["line"] - preamble_lines
        if adjusted_line < 1:
            continue  # Skip constructs from the preamble itself
        adjusted.append(
            {
                "construct": item["construct"],
                "line": adjusted_line,
                "details": item["details"],
            }
        )

    return adjusted
