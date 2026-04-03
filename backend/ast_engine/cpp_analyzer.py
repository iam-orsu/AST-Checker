"""
C++ AST Analyzer
Uses tree-sitter with tree-sitter-cpp grammar for lightweight AST parsing.
All detection is done via proper AST node type checking — no keyword scanning.
Chosen over libclang to keep the Docker image small for the demo.
"""

import tree_sitter_cpp as tscpp
import tree_sitter as ts
from typing import Any


CPP_LANGUAGE = ts.Language(tscpp.language())
PARSER = ts.Parser(CPP_LANGUAGE)


# tree-sitter node types for C++ constructs
NODE_TYPE_MAP = {
    "while_statement": "while_loop",
    "for_statement": "for_loop",
    "for_range_loop": "for_loop",
    "do_statement": "do_while_loop",
    "if_statement": "if_else",
    "switch_statement": "switch",
    "function_definition": "function",
    "class_specifier": "class",
    "struct_specifier": "class",
    "try_statement": "exception_handling",
    "catch_clause": "exception_handling",
    "throw_statement": "exception_handling",
}

# STL type names for data structure detection
STL_TYPES = {
    "vector": "array",
    "array": "array",
    "list": "linked_list",
    "forward_list": "linked_list",
    "stack": "stack",
    "queue": "queue",
    "deque": "queue",
    "priority_queue": "queue",
    "set": "set",
    "unordered_set": "set",
    "map": "dictionary",
    "unordered_map": "dictionary",
}


def analyze(code: str) -> list[dict]:
    """
    Parse C++ code and return all detected constructs with line numbers.
    Returns a list of dicts: [{"construct": str, "line": int, "details": str}]
    """
    try:
        tree = PARSER.parse(bytes(code, "utf8"))
    except Exception as e:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": f"C++ parse error: {str(e)}",
            }
        ]

    if tree.root_node.has_error:
        # Still try to analyze what we can — tree-sitter is error-tolerant
        pass

    found = []
    function_names = set()

    # First pass: collect all function names for recursion detection
    _collect_function_names(tree.root_node, function_names)

    # Second pass: detect all constructs
    _traverse(tree.root_node, found, function_names, current_function=None)

    return found


def _collect_function_names(node, function_names: set):
    """Collect all function/method names for recursion detection."""
    if node.type == "function_definition":
        name = _get_function_name(node)
        if name:
            function_names.add(name)

    for child in node.children:
        _collect_function_names(child, function_names)


def _get_function_name(func_node) -> str:
    """Extract the function name from a function_definition node."""
    declarator = func_node.child_by_field_name("declarator")
    if declarator:
        return _find_identifier_in_declarator(declarator)
    return ""


def _find_identifier_in_declarator(node) -> str:
    """Recursively find the function/method name identifier in a declarator."""
    if node.type == "function_declarator":
        inner = node.child_by_field_name("declarator")
        if inner:
            return _find_identifier_in_declarator(inner)
    elif node.type == "identifier":
        return node.text.decode("utf8")
    elif node.type == "qualified_identifier":
        # For class::method patterns, get the method name
        name_node = node.child_by_field_name("name")
        if name_node:
            return name_node.text.decode("utf8")
    elif node.type == "field_identifier":
        return node.text.decode("utf8")
    elif node.type == "destructor_name":
        return "~" + (node.children[1].text.decode("utf8") if len(node.children) > 1 else "")
    elif node.type == "pointer_declarator" or node.type == "reference_declarator":
        inner = node.child_by_field_name("declarator")
        if inner:
            return _find_identifier_in_declarator(inner)

    # Fallback: search children
    for child in node.children:
        result = _find_identifier_in_declarator(child)
        if result:
            return result
    return ""


def _traverse(node, found: list, function_names: set, current_function: str | None):
    """Recursively traverse the tree-sitter AST and detect constructs."""
    # Line numbers in tree-sitter are 0-indexed; we convert to 1-indexed
    line = node.start_point[0] + 1

    # Check if this node type maps to a known construct
    if node.type in NODE_TYPE_MAP:
        construct = NODE_TYPE_MAP[node.type]

        if node.type == "function_definition":
            func_name = _get_function_name(node)
            found.append(
                {
                    "construct": "function",
                    "line": line,
                    "details": f"function '{func_name}' defined",
                }
            )
            # Recurse into the function body with current_function set
            for child in node.children:
                _traverse(child, found, function_names, current_function=func_name)
            return

        elif node.type == "class_specifier" or node.type == "struct_specifier":
            class_name = ""
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = name_node.text.decode("utf8")

            kind = "class" if node.type == "class_specifier" else "struct"
            found.append(
                {
                    "construct": "class",
                    "line": line,
                    "details": f"{kind} '{class_name}' declared",
                }
            )

            # Check for base class (inheritance)
            for child in node.children:
                if child.type == "base_class_clause":
                    for base_child in child.children:
                        if base_child.type == "base_class_specifier":
                            base_name = base_child.text.decode("utf8").strip()
                            # Remove access specifiers like "public ", "private "
                            for prefix in ("public ", "protected ", "private "):
                                if base_name.startswith(prefix):
                                    base_name = base_name[len(prefix):]
                                    break
                            found.append(
                                {
                                    "construct": "inheritance",
                                    "line": line,
                                    "details": f"'{class_name}' inherits from '{base_name}'",
                                }
                            )

        else:
            details_map = {
                "while_loop": "while loop detected",
                "for_loop": "for loop detected",
                "do_while_loop": "do-while loop detected",
                "if_else": "if statement detected",
                "switch": "switch statement detected",
                "exception_handling": f"{node.type.replace('_', ' ')} detected",
            }
            found.append(
                {
                    "construct": construct,
                    "line": line,
                    "details": details_map.get(construct, f"{construct} detected"),
                }
            )

    # Detect function calls for recursion
    elif node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        if func_node:
            call_name = func_node.text.decode("utf8")
            # Handle qualified calls like obj.method or Class::method
            if "::" in call_name:
                call_name = call_name.split("::")[-1]
            if "." in call_name:
                call_name = call_name.split(".")[-1]

            if current_function and call_name == current_function:
                found.append(
                    {
                        "construct": "recursion",
                        "line": line,
                        "details": f"recursive call to '{call_name}' detected",
                    }
                )

    # Detect STL template types for data structures
    elif node.type == "template_type":
        type_name_node = node.child_by_field_name("name")
        if type_name_node:
            type_name = type_name_node.text.decode("utf8")
            # Remove std:: prefix if present
            if type_name.startswith("std::"):
                type_name = type_name[5:]

            if type_name in STL_TYPES:
                found.append(
                    {
                        "construct": STL_TYPES[type_name],
                        "line": line,
                        "details": f"std::{type_name} usage detected",
                    }
                )

    # Detect raw array declarations (e.g., int arr[10])
    elif node.type == "array_declarator":
        found.append(
            {
                "construct": "array",
                "line": line,
                "details": "array declaration detected",
            }
        )

    # Detect new[] expressions
    elif node.type == "new_expression":
        # Check if it's an array new (new int[10])
        for child in node.children:
            if child.type == "new_declarator":
                found.append(
                    {
                        "construct": "array",
                        "line": line,
                        "details": "dynamic array allocation detected",
                    }
                )
                break

    # Detect qualified identifiers referencing STL types
    elif node.type == "qualified_identifier":
        text = node.text.decode("utf8")
        if text.startswith("std::"):
            stl_name = text[5:]
            if stl_name in STL_TYPES:
                found.append(
                    {
                        "construct": STL_TYPES[stl_name],
                        "line": line,
                        "details": f"{text} usage detected",
                    }
                )

    # Continue traversal for children
    for child in node.children:
        _traverse(child, found, function_names, current_function)
