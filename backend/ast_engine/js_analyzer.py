"""
JavaScript AST Analyzer
Uses acorn (via Node.js subprocess) to parse JavaScript into an ESTree-compliant AST.
All detection is done via proper AST node type checking — no keyword scanning.
The Node.js script js_ast_worker.js does the actual parsing and traversal,
outputting results as JSON to stdout.
"""

import json
import subprocess
import tempfile
import os
from typing import Any

# Path to the JS AST worker script (lives alongside this file)
JS_WORKER_PATH = os.path.join(os.path.dirname(__file__), "js_ast_worker.js")


def analyze(code: str) -> list[dict]:
    """
    Parse JavaScript code via acorn (Node.js subprocess) and return all
    detected constructs with line numbers.
    Returns a list of dicts: [{"construct": str, "line": int, "details": str}]
    """
    # Write code to a temporary file
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".js", prefix="ast_check_")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(code)

        # Run the Node.js AST worker as a subprocess
        result = subprocess.run(
            ["node", JS_WORKER_PATH, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(JS_WORKER_PATH),
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown JS parse error"
            return [
                {
                    "construct": "syntax_error",
                    "line": 1,
                    "details": f"JavaScript parse error: {error_msg}",
                }
            ]

        # Parse the JSON output
        output = result.stdout.strip()
        if not output:
            return []

        try:
            found = json.loads(output)
        except json.JSONDecodeError as e:
            return [
                {
                    "construct": "syntax_error",
                    "line": 1,
                    "details": f"Failed to parse JS analyzer output: {str(e)}",
                }
            ]

        return found

    except subprocess.TimeoutExpired:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": "JavaScript analysis timed out (10 seconds)",
            }
        ]
    except FileNotFoundError:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": "Node.js not found. Required for JavaScript AST analysis.",
            }
        ]
    except Exception as e:
        return [
            {
                "construct": "syntax_error",
                "line": 1,
                "details": f"JavaScript analysis error: {str(e)}",
            }
        ]
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
