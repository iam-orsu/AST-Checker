/**
 * JavaScript AST Worker
 * Uses acorn to parse JavaScript code into an ESTree-compliant AST,
 * then walks the tree to detect code constructs.
 * All detection is done via proper AST node type checking — no keyword scanning.
 *
 * Usage: node js_ast_worker.js <filepath>
 * Output: JSON array of detected constructs to stdout
 */

const path = require("path");

// Try to load acorn from /app/node_modules (Docker), then from CWD, then global
let acorn;
try {
  acorn = require("/app/node_modules/acorn");
} catch (_) {
  acorn = require("acorn");
}

const fs = require("fs");

const filePath = process.argv[2];
if (!filePath) {
  process.stderr.write("Usage: node js_ast_worker.js <filepath>\n");
  process.exit(1);
}

let code;
try {
  code = fs.readFileSync(filePath, "utf-8");
} catch (err) {
  process.stderr.write(`Failed to read file: ${err.message}\n`);
  process.exit(1);
}

let ast;
try {
  ast = acorn.parse(code, {
    ecmaVersion: "latest",
    sourceType: "module",
    locations: true,
  });
} catch (err) {
  process.stderr.write(`Parse error: ${err.message}\n`);
  process.exit(1);
}

const found = [];
const functionNames = new Set();

// First pass: collect all function names for recursion detection
collectFunctionNames(ast);

// Second pass: detect all constructs
traverse(ast, null);

// Output results as JSON
process.stdout.write(JSON.stringify(found));

/**
 * Collect all declared function names for recursion detection.
 */
function collectFunctionNames(node) {
  if (!node || typeof node !== "object") return;

  if (node.type === "FunctionDeclaration" && node.id) {
    functionNames.add(node.id.name);
  }
  if (node.type === "VariableDeclarator" && node.id && node.init) {
    if (
      node.init.type === "FunctionExpression" ||
      node.init.type === "ArrowFunctionExpression"
    ) {
      functionNames.add(node.id.name);
    }
  }

  for (const key of Object.keys(node)) {
    if (key === "type" || key === "loc" || key === "start" || key === "end")
      continue;
    const child = node[key];
    if (Array.isArray(child)) {
      child.forEach((c) => {
        if (c && typeof c === "object" && c.type) collectFunctionNames(c);
      });
    } else if (child && typeof child === "object" && child.type) {
      collectFunctionNames(child);
    }
  }
}

/**
 * Recursively traverse the AST and detect constructs.
 * @param {object} node - Current AST node
 * @param {string|null} currentFunction - Name of the enclosing function (for recursion detection)
 */
function traverse(node, currentFunction) {
  if (!node || typeof node !== "object") return;

  const line = node.loc ? node.loc.start.line : 0;

  switch (node.type) {
    case "WhileStatement":
      found.push({
        construct: "while_loop",
        line: line,
        details: "while loop detected",
      });
      break;

    case "ForStatement":
      found.push({
        construct: "for_loop",
        line: line,
        details: "for loop detected",
      });
      break;

    case "ForInStatement":
      found.push({
        construct: "for_loop",
        line: line,
        details: "for...in loop detected",
      });
      break;

    case "ForOfStatement":
      found.push({
        construct: "for_loop",
        line: line,
        details: "for...of loop detected",
      });
      break;

    case "DoWhileStatement":
      found.push({
        construct: "do_while_loop",
        line: line,
        details: "do-while loop detected",
      });
      break;

    case "IfStatement":
      found.push({
        construct: "if_else",
        line: line,
        details: "if statement detected",
      });
      break;

    case "SwitchStatement":
      found.push({
        construct: "switch",
        line: line,
        details: "switch statement detected",
      });
      break;

    case "FunctionDeclaration":
      {
        const funcName = node.id ? node.id.name : "anonymous";
        found.push({
          construct: "function",
          line: line,
          details: `function '${funcName}' declared`,
        });
        // Traverse body with function name for recursion detection
        traverseChildren(node, funcName);
        return; // Don't double-traverse
      }

    case "FunctionExpression":
      {
        const feName = node.id ? node.id.name : "anonymous";
        found.push({
          construct: "function",
          line: line,
          details: `function expression '${feName}' detected`,
        });
        traverseChildren(node, feName !== "anonymous" ? feName : currentFunction);
        return;
      }

    case "ArrowFunctionExpression":
      found.push({
        construct: "function",
        line: line,
        details: "arrow function detected",
      });
      // Arrow functions inherit the parent function name for recursion
      traverseChildren(node, currentFunction);
      return;

    case "ClassDeclaration":
      {
        const className = node.id ? node.id.name : "anonymous";
        found.push({
          construct: "class",
          line: line,
          details: `class '${className}' declared`,
        });

        // Check for inheritance (extends)
        if (node.superClass) {
          let superName = "unknown";
          if (node.superClass.type === "Identifier") {
            superName = node.superClass.name;
          } else if (node.superClass.type === "MemberExpression") {
            superName = getNodeText(node.superClass);
          }
          found.push({
            construct: "inheritance",
            line: line,
            details: `class '${className}' extends '${superName}'`,
          });
        }
      }
      break;

    case "ClassExpression":
      {
        const ceClassName = node.id ? node.id.name : "anonymous";
        found.push({
          construct: "class",
          line: line,
          details: `class expression '${ceClassName}' detected`,
        });
        if (node.superClass) {
          let superName = "unknown";
          if (node.superClass.type === "Identifier") {
            superName = node.superClass.name;
          }
          found.push({
            construct: "inheritance",
            line: line,
            details: `class '${ceClassName}' extends '${superName}'`,
          });
        }
      }
      break;

    case "TryStatement":
      found.push({
        construct: "exception_handling",
        line: line,
        details: "try statement detected",
      });
      break;

    case "CatchClause":
      found.push({
        construct: "exception_handling",
        line: line,
        details: "catch clause detected",
      });
      break;

    case "ThrowStatement":
      found.push({
        construct: "exception_handling",
        line: line,
        details: "throw statement detected",
      });
      break;

    case "CallExpression":
      {
        const callName = getCallName(node);

        // Recursion detection
        if (currentFunction && callName === currentFunction) {
          found.push({
            construct: "recursion",
            line: line,
            details: `recursive call to '${callName}' detected`,
          });
        }

        // Data structure detection via constructor calls
        if (node.callee && node.callee.type === "Identifier") {
          const name = node.callee.name;
          if (name === "Array") {
            found.push({
              construct: "array",
              line: line,
              details: "Array constructor detected",
            });
          } else if (name === "Map") {
            found.push({
              construct: "dictionary",
              line: line,
              details: "Map usage detected",
            });
          } else if (name === "Set") {
            found.push({
              construct: "set",
              line: line,
              details: "Set usage detected",
            });
          }
        }
      }
      break;

    case "NewExpression":
      {
        if (node.callee && node.callee.type === "Identifier") {
          const name = node.callee.name;
          if (name === "Array") {
            found.push({
              construct: "array",
              line: line,
              details: "new Array() detected",
            });
          } else if (name === "Map") {
            found.push({
              construct: "dictionary",
              line: line,
              details: "new Map() detected",
            });
          } else if (name === "Set") {
            found.push({
              construct: "set",
              line: line,
              details: "new Set() detected",
            });
          }
        }
      }
      break;

    case "ArrayExpression":
      found.push({
        construct: "array",
        line: line,
        details: "array literal detected",
      });
      break;

    case "VariableDeclarator":
      // Check for function assigned to variable (for recursion tracking)
      if (node.id && node.init) {
        if (
          node.init.type === "FunctionExpression" ||
          node.init.type === "ArrowFunctionExpression"
        ) {
          // Already handled by FunctionExpression/ArrowFunctionExpression cases
        }
      }
      break;
  }

  // Continue traversal
  traverseChildren(node, currentFunction);
}

/**
 * Traverse all children of a node.
 */
function traverseChildren(node, currentFunction) {
  for (const key of Object.keys(node)) {
    if (key === "type" || key === "loc" || key === "start" || key === "end")
      continue;
    const child = node[key];
    if (Array.isArray(child)) {
      child.forEach((c) => {
        if (c && typeof c === "object" && c.type) traverse(c, currentFunction);
      });
    } else if (child && typeof child === "object" && child.type) {
      traverse(child, currentFunction);
    }
  }
}

/**
 * Extract the function name from a CallExpression node.
 */
function getCallName(node) {
  if (!node.callee) return "";
  if (node.callee.type === "Identifier") {
    return node.callee.name;
  }
  if (node.callee.type === "MemberExpression") {
    if (node.callee.property && node.callee.property.type === "Identifier") {
      return node.callee.property.name;
    }
  }
  return "";
}

/**
 * Get a text representation of a node (for display purposes).
 */
function getNodeText(node) {
  if (node.type === "Identifier") return node.name;
  if (node.type === "MemberExpression") {
    return getNodeText(node.object) + "." + getNodeText(node.property);
  }
  return "unknown";
}
