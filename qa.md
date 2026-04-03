Paste this into Opus with all the generated code:

---

You are doing a brutal QA audit on this entire project. Do not explain what the code does. Find every bug, every broken assumption, every edge case that will crash or silently fail, and fix all of it. Rewrite entire files if needed. No partial patches.

Check the database layer — does init_db run correctly on first startup, does it crash on restart if tables already exist, are editable_ranges and topic_tags stored and retrieved as proper JSON and not raw strings, does the migration handle missing columns gracefully, do all foreign key relationships actually enforce correctly in SQLite.

Check the AST engine — do all 5 language analyzers actually import and initialize without errors inside Docker, does tree-sitter-cpp load its grammar correctly, does the Node.js acorn subprocess get spawned correctly from inside the backend container and is Node.js actually installed in the backend Dockerfile, does javalang handle malformed Java without crashing the server, does pycparser handle code with no headers without crashing, are line numbers 0-indexed or 1-indexed and does engine.py and every analyzer agree on the same indexing, does recursion detection actually work for all 5 languages or just Python, does the editable_ranges filter in engine.py correctly use startLine and endLine inclusive bounds.

Check the Docker execution engine — does the Docker socket mount actually work, does the SDK correctly create and remove sibling containers with no leaks even when code crashes or times out, does stdin piping work correctly for all 5 languages, does the 5 second timeout actually kill the container or just stop waiting, does memory limit enforcement work, what happens if the runner image does not exist on the host yet.

Check the constrained-editor-plugin integration — is the CDN script loaded before Monaco initializes, does the plugin correctly apply multiple non-contiguous editable ranges, when language changes are all old restrictions torn down before new ones applied, do decorations for locked and editable zones render without conflicting with each other, does the violation red glow decoration clear correctly when the user fixes the issue, what happens if editable_ranges comes back as null or empty array from the API.

Check the admin editor — does the Monaco instance initialize correctly inside each language tab even before the tab is clicked, when admin marks lines as editable does the range serialization produce correct startLine and endLine values matching what the user editor expects, does the auto-detect function body on paste work for all 5 languages or hardcoded for Python only, does saving with zero editable ranges actually warn the admin before proceeding.

Check all API endpoints — do all admin CRUD endpoints correctly read and write template_code and editable_ranges, does /api/problems/{id}/template/{language} return the correct fields, does /api/check-constraints correctly pass editable_ranges to the engine on every call, does /api/submit assemble the full code correctly before passing to AST engine, are all endpoints protected so a user cannot hit admin routes.

Check auth and routing — does localStorage token persist across page refresh, does role-based routing actually prevent users from accessing admin pages, does logout clear the token correctly.

Check edge cases — user submits empty code, code that crashes, infinite loop hitting timeout, unicode characters in code, very large output from code, admin saves a problem then edits it and shrinks the template so old editable_ranges reference lines that no longer exist, two adjacent editable ranges like lines 5-7 and 8-10, single line editable range.

For every bug: show the broken code, explain exactly why it breaks, show the fixed code. Fix everything. Do not leave any known issue unfixed.