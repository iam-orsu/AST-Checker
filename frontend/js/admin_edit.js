/**
 * admin_edit.js — Admin problem create/edit page logic
 * Monaco Editor per language tab with editable range marking via deltaDecorations.
 * Auto-detects function body on paste, serializes editable_ranges on save.
 */

(function () {
    // Auth guard
    if (!AUTH.requireAuth('admin')) return;
    AUTH.setupNavbar();
    AUTH.setupLogout();

    // ── State ──
    const urlParams = new URLSearchParams(window.location.search);
    const editId = urlParams.get('id');
    const isEditMode = !!editId;

    const LANGUAGES = ['python', 'c', 'cpp', 'java', 'javascript'];
    const MONACO_LANG_MAP = {
        python: 'python',
        c: 'c',
        cpp: 'cpp',
        java: 'java',
        javascript: 'javascript',
    };

    const TOPIC_TAGS = [
        'Arrays', 'Strings', 'Hash Table', 'Two Pointers', 'Sorting',
        'Searching', 'Recursion', 'Trees', 'Graphs', 'Dynamic Programming',
        'Linked Lists', 'Stacks', 'Queues', 'Math', 'Greedy',
        'Backtracking', 'Bit Manipulation', 'Design',
    ];

    const CONSTRUCTS = [
        'while_loop', 'for_loop', 'do_while_loop', 'if_else', 'switch',
        'function', 'recursion', 'class', 'inheritance', 'polymorphism',
        'exception_handling', 'array', 'linked_list', 'stack', 'queue',
    ];

    let monacoInstance = null;
    const editors = {};            // lang -> monaco editor instance
    const editableRanges = {};      // lang -> [{startLine, endLine}]
    const editorDecorations = {};   // lang -> decoration IDs
    let selectedTopicTags = [];
    let selectedRequired = [];
    let selectedBanned = [];
    let testCases = [];

    // ── Initialize ──
    if (isEditMode) {
        document.getElementById('pageTitle').textContent = 'Edit Problem';
        document.title = 'Edit Problem — AST-Compiler Admin';
    }

    // Render tag/construct grids
    renderChipGrid('topicTagsGrid', TOPIC_TAGS, selectedTopicTags);
    renderChipGrid('requiredConstructsGrid', CONSTRUCTS, selectedRequired, formatConstruct);
    renderChipGrid('bannedConstructsGrid', CONSTRUCTS, selectedBanned, formatConstruct);

    // Add initial test case
    if (!isEditMode) {
        addTestCase('', '', 1);
    }

    // ── Monaco Setup ──
    require.config({
        paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' },
    });

    require(['vs/editor/editor.main'], function (monaco) {
        monacoInstance = monaco;

        // Custom theme
        monaco.editor.defineTheme('astDarkAdmin', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'comment', foreground: '6A6A7A', fontStyle: 'italic' },
                { token: 'keyword', foreground: 'E94560' },
                { token: 'string', foreground: '2ECC71' },
            ],
            colors: {
                'editor.background': '#1a1a2e',
                'editor.foreground': '#e0e0e0',
                'editor.lineHighlightBackground': '#16213e',
                'editorCursor.foreground': '#e94560',
                'editorLineNumber.foreground': '#6a6a7a',
            },
        });

        // Create editor for each language
        LANGUAGES.forEach(lang => {
            const container = document.getElementById(`monaco-${lang}`);
            if (!container) return;

            editableRanges[lang] = [];
            editorDecorations[lang] = [];

            editors[lang] = monaco.editor.create(container, {
                value: '',
                language: MONACO_LANG_MAP[lang],
                theme: 'astDarkAdmin',
                fontSize: 13,
                fontFamily: "'JetBrains Mono', monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                padding: { top: 8 },
                automaticLayout: true,
                tabSize: 4,
                insertSpaces: true,
                detectIndentation: false,
                renderWhitespace: 'all',
                renderControlCharacters: true,
                glyphMargin: true,
            });

            // Auto-detect on paste
            editors[lang].onDidPaste(() => {
                setTimeout(() => autoDetectEditable(lang), 100);
            });
        });

        // If edit mode, load existing problem data
        if (isEditMode) {
            loadProblem();
        }
    });

    // ── Language Tabs ──
    document.querySelectorAll('.language-tab').forEach(tab => {
        tab.addEventListener('click', function () {
            const lang = this.dataset.lang;

            // Update tab states
            document.querySelectorAll('.language-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Show corresponding editor
            document.querySelectorAll('.language-editor-container').forEach(c => c.classList.remove('active'));
            const container = document.getElementById(`editor-${lang}`);
            if (container) container.classList.add('active');

            // Layout the editor (needed after display change)
            if (editors[lang]) {
                setTimeout(() => editors[lang].layout(), 50);
            }
        });
    });

    // ── Chip Grid ──
    function renderChipGrid(containerId, items, selectedArray, labelFn) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = items.map(item => {
            const label = labelFn ? labelFn(item) : item;
            const selected = selectedArray.includes(item);
            return `<button type="button" class="construct-chip ${selected ? 'selected' : ''}" 
                     data-value="${item}" onclick="toggleChip(this, '${containerId}')">${label}</button>`;
        }).join('');
    }

    window.toggleChip = function (el, containerId) {
        el.classList.toggle('selected');
        updateSelectedFromGrid(containerId);
    };

    function updateSelectedFromGrid(containerId) {
        const chips = document.querySelectorAll(`#${containerId} .construct-chip.selected`);
        const values = Array.from(chips).map(c => c.dataset.value);

        if (containerId === 'topicTagsGrid') selectedTopicTags = values;
        else if (containerId === 'requiredConstructsGrid') selectedRequired = values;
        else if (containerId === 'bannedConstructsGrid') selectedBanned = values;
    }

    function formatConstruct(name) {
        return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    // ── Editable Range Management ──
    window.markEditable = function (lang) {
        const editor = editors[lang];
        if (!editor) return;

        const selection = editor.getSelection();
        if (!selection || selection.isEmpty()) {
            showToast('Select lines first, then click Mark as Editable', 'warning');
            return;
        }

        const startLine = selection.startLineNumber;
        const endLine = selection.endLineNumber;

        // Add range (merge overlapping)
        addEditableRange(lang, startLine, endLine);
        updateDecorations(lang);
        updateRangeInfo(lang);
    };

    window.markLocked = function (lang) {
        const editor = editors[lang];
        if (!editor) return;

        const selection = editor.getSelection();
        if (!selection || selection.isEmpty()) {
            showToast('Select lines first, then click Mark as Locked', 'warning');
            return;
        }

        const startLine = selection.startLineNumber;
        const endLine = selection.endLineNumber;

        // Remove the selected lines from editable ranges
        removeFromEditableRanges(lang, startLine, endLine);
        updateDecorations(lang);
        updateRangeInfo(lang);
    };

    window.clearAllRanges = function (lang) {
        editableRanges[lang] = [];
        updateDecorations(lang);
        updateRangeInfo(lang);
    };

    window.autoDetectEditable = function (lang) {
        const editor = editors[lang];
        if (!editor) return;

        const code = editor.getValue();
        const lines = code.split('\n');

        // Auto-detect: find function/method body lines
        // Look for lines between function signature and closing brace
        const detectedRanges = [];
        let inFunction = false;
        let funcStart = -1;
        let braceDepth = 0;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const lineNum = i + 1;

            // Detect function/method start
            const isFuncStart = detectFunctionStart(line, lang);

            if (isFuncStart && !inFunction) {
                inFunction = true;
                funcStart = lineNum;
                braceDepth = 0;

                // For Python: function body starts on next line
                if (lang === 'python') {
                    funcStart = lineNum + 1;
                }
            }

            if (inFunction) {
                // Count braces for C-like languages
                if (lang !== 'python') {
                    for (const ch of line) {
                        if (ch === '{') braceDepth++;
                        if (ch === '}') braceDepth--;
                    }

                    // Opening brace of function
                    if (line.includes('{') && funcStart === lineNum) {
                        funcStart = lineNum + 1;
                    }

                    // Closing brace of function
                    if (braceDepth <= 0 && line.includes('}')) {
                        const bodyEnd = lineNum - 1;
                        if (bodyEnd >= funcStart) {
                            detectedRanges.push({ startLine: funcStart, endLine: bodyEnd });
                        }
                        inFunction = false;
                    }
                } else {
                    // Python: function body is indented lines after def
                    if (lineNum > funcStart && line !== '' && !line.startsWith(' ') && !line.startsWith('\t')) {
                        // End of indented block
                        const bodyEnd = lineNum - 1;
                        if (bodyEnd >= funcStart) {
                            detectedRanges.push({ startLine: funcStart, endLine: bodyEnd });
                        }
                        inFunction = false;
                    }
                }
            }
        }

        // Handle function at end of file
        if (inFunction && funcStart > 0) {
            const lastContentLine = findLastContentLine(lines);
            if (lastContentLine >= funcStart) {
                detectedRanges.push({ startLine: funcStart, endLine: lastContentLine });
            }
        }

        if (detectedRanges.length > 0) {
            // Only use the first detected function body (usually the solution function)
            editableRanges[lang] = [detectedRanges[0]];
            updateDecorations(lang);
            updateRangeInfo(lang);
            showToast(`Auto-detected editable range: lines ${detectedRanges[0].startLine}-${detectedRanges[0].endLine}`, 'success');
        } else {
            showToast('Could not auto-detect function body. Select lines manually.', 'warning');
        }
    };

    function detectFunctionStart(line, lang) {
        if (lang === 'python') {
            return /^\s*def\s+\w+/.test(line);
        }
        if (lang === 'java') {
            return /^\s*(public|private|protected|static|\s)+\s+\w+\s+\w+\s*\(/.test(line) &&
                !line.includes('class ') && !line.includes('interface ');
        }
        if (lang === 'c' || lang === 'cpp') {
            return /^\s*(\w+\s+)+\w+\s*\(/.test(line) && !line.includes('#') && !line.includes('class ');
        }
        if (lang === 'javascript') {
            return /^\s*(function\s+\w+|const\s+\w+\s*=\s*(function|\()|\w+\s*\()/.test(line);
        }
        return false;
    }

    function findLastContentLine(lines) {
        for (let i = lines.length - 1; i >= 0; i--) {
            if (lines[i].trim() !== '') return i + 1;
        }
        return lines.length;
    }

    function addEditableRange(lang, start, end) {
        const ranges = editableRanges[lang];
        ranges.push({ startLine: start, endLine: end });
        mergeRanges(lang);
    }

    function removeFromEditableRanges(lang, start, end) {
        const newRanges = [];
        for (const r of editableRanges[lang]) {
            if (r.endLine < start || r.startLine > end) {
                // No overlap — keep as is
                newRanges.push(r);
            } else {
                // Overlap — split
                if (r.startLine < start) {
                    newRanges.push({ startLine: r.startLine, endLine: start - 1 });
                }
                if (r.endLine > end) {
                    newRanges.push({ startLine: end + 1, endLine: r.endLine });
                }
            }
        }
        editableRanges[lang] = newRanges;
    }

    function mergeRanges(lang) {
        const ranges = editableRanges[lang];
        if (ranges.length <= 1) return;

        ranges.sort((a, b) => a.startLine - b.startLine);

        const merged = [ranges[0]];
        for (let i = 1; i < ranges.length; i++) {
            const last = merged[merged.length - 1];
            const curr = ranges[i];

            if (curr.startLine <= last.endLine + 1) {
                last.endLine = Math.max(last.endLine, curr.endLine);
            } else {
                merged.push(curr);
            }
        }
        editableRanges[lang] = merged;
    }

    function updateDecorations(lang) {
        const editor = editors[lang];
        if (!editor || !monacoInstance) return;

        const totalLines = editor.getModel().getLineCount();
        const ranges = editableRanges[lang] || [];

        // Build set of editable lines
        const editableLines = new Set();
        ranges.forEach(r => {
            for (let i = r.startLine; i <= r.endLine; i++) {
                editableLines.add(i);
            }
        });

        const decorations = [];

        for (let line = 1; line <= totalLines; line++) {
            if (editableLines.has(line)) {
                decorations.push({
                    range: new monacoInstance.Range(line, 1, line, 1),
                    options: {
                        isWholeLine: true,
                        className: 'admin-editable-line',
                        glyphMarginClassName: 'admin-editable-gutter',
                    },
                });
            } else {
                decorations.push({
                    range: new monacoInstance.Range(line, 1, line, 1),
                    options: {
                        isWholeLine: true,
                        className: 'admin-locked-line',
                        glyphMarginClassName: 'admin-locked-gutter',
                    },
                });
            }
        }

        editorDecorations[lang] = editor.deltaDecorations(editorDecorations[lang] || [], decorations);
    }

    function updateRangeInfo(lang) {
        const infoEl = document.getElementById(`ranges-info-${lang}`);
        if (!infoEl) return;

        const ranges = editableRanges[lang] || [];

        if (ranges.length === 0) {
            infoEl.innerHTML = '<span style="color:var(--warning);">⚠ No editable ranges defined</span>';
        } else {
            infoEl.innerHTML = ranges.map(r =>
                `<span class="range-item">Lines ${r.startLine}–${r.endLine}</span>`
            ).join('');
        }

        checkZeroRangesWarning();
    }

    function checkZeroRangesWarning() {
        const warning = document.getElementById('zeroRangesWarning');
        if (!warning) return;

        let hasContent = false;
        let hasZeroRanges = false;

        LANGUAGES.forEach(lang => {
            const editor = editors[lang];
            if (editor && editor.getValue().trim() !== '') {
                hasContent = true;
                if (!editableRanges[lang] || editableRanges[lang].length === 0) {
                    hasZeroRanges = true;
                }
            }
        });

        if (hasContent && hasZeroRanges) {
            warning.classList.remove('hidden');
        } else {
            warning.classList.add('hidden');
        }
    }

    // ── Test Cases ──
    document.getElementById('addTestCaseBtn')?.addEventListener('click', () => {
        addTestCase('', '', 1);
    });

    function addTestCase(input, expected, isSample) {
        const idx = testCases.length;
        testCases.push({ input_data: input, expected_output: expected, is_sample: isSample });
        renderTestCases();
    }

    function renderTestCases() {
        const container = document.getElementById('testCasesList');
        if (!container) return;

        container.innerHTML = testCases.map((tc, idx) => `
            <div class="test-case-item" data-index="${idx}">
                <div class="input-group">
                    <label>Input</label>
                    <textarea placeholder="Test input..." data-field="input_data" data-index="${idx}"
                        onchange="updateTestCase(${idx}, 'input_data', this.value)">${escapeHtml(tc.input_data)}</textarea>
                </div>
                <div class="input-group">
                    <label>Expected Output</label>
                    <textarea placeholder="Expected output..." data-field="expected_output" data-index="${idx}"
                        onchange="updateTestCase(${idx}, 'expected_output', this.value)">${escapeHtml(tc.expected_output)}</textarea>
                </div>
                <div style="display:flex; flex-direction:column; gap:8px; align-items:center;">
                    <label style="font-size:0.75rem; color:var(--text-muted);">
                        <input type="checkbox" ${tc.is_sample ? 'checked' : ''} 
                            onchange="updateTestCase(${idx}, 'is_sample', this.checked ? 1 : 0)"> Sample
                    </label>
                    <button class="btn btn-danger btn-sm" onclick="removeTestCase(${idx})" ${testCases.length <= 1 ? 'disabled' : ''}>✕</button>
                </div>
            </div>
        `).join('');
    }

    window.updateTestCase = function (idx, field, value) {
        if (testCases[idx]) {
            testCases[idx][field] = value;
        }
    };

    window.removeTestCase = function (idx) {
        testCases.splice(idx, 1);
        renderTestCases();
    };

    // ── Load Existing Problem (Edit Mode) ──
    async function loadProblem() {
        showLoading(true, 'Loading problem...');
        try {
            const res = await fetch(`/api/admin/problems/${editId}`, {
                headers: AUTH.getAuthHeaders(),
            });

            if (!res.ok) {
                showToast('Failed to load problem', 'error');
                return;
            }

            const data = await res.json();

            // Fill form fields
            document.getElementById('problemTitle').value = data.title || '';
            document.getElementById('problemDescription').value = data.description || '';
            document.getElementById('problemDifficulty').value = data.difficulty || 'Easy';

            // Topic tags
            selectedTopicTags = data.topic_tags || [];
            renderChipGrid('topicTagsGrid', TOPIC_TAGS, selectedTopicTags);

            // Constructs
            selectedRequired = data.required_constructs || [];
            selectedBanned = data.banned_constructs || [];
            renderChipGrid('requiredConstructsGrid', CONSTRUCTS, selectedRequired, formatConstruct);
            renderChipGrid('bannedConstructsGrid', CONSTRUCTS, selectedBanned, formatConstruct);

            // Templates
            if (data.templates) {
                data.templates.forEach(t => {
                    const lang = t.language;
                    if (editors[lang]) {
                        editors[lang].setValue(t.template_code || '');
                        editableRanges[lang] = t.editable_ranges || [];
                        setTimeout(() => {
                            updateDecorations(lang);
                            updateRangeInfo(lang);
                        }, 100);
                    }
                });
            }

            // Test cases
            testCases = (data.test_cases || []).map(tc => ({
                input_data: tc.input_data || '',
                expected_output: tc.expected_output || '',
                is_sample: tc.is_sample || 0,
            }));
            if (testCases.length === 0) {
                testCases.push({ input_data: '', expected_output: '', is_sample: 1 });
            }
            renderTestCases();

        } catch (err) {
            showToast('Failed to load problem data', 'error');
            console.error('Load error:', err);
        } finally {
            showLoading(false);
        }
    }

    // ── Save Problem ──
    document.getElementById('saveProblemBtn')?.addEventListener('click', saveProblem);

    async function saveProblem() {
        const title = document.getElementById('problemTitle').value.trim();
        const description = document.getElementById('problemDescription').value.trim();
        const difficulty = document.getElementById('problemDifficulty').value;

        if (!title) {
            showToast('Title is required', 'error');
            return;
        }
        if (!description) {
            showToast('Description is required', 'error');
            return;
        }

        // Refresh selected values from chip grids
        updateSelectedFromGrid('topicTagsGrid');
        updateSelectedFromGrid('requiredConstructsGrid');
        updateSelectedFromGrid('bannedConstructsGrid');

        // Build templates array
        const templates = [];
        LANGUAGES.forEach(lang => {
            const editor = editors[lang];
            if (editor) {
                const code = editor.getValue().trim();
                if (code) {
                    templates.push({
                        language: lang,
                        template_code: editor.getValue(),
                        editable_ranges: editableRanges[lang] || [],
                    });
                }
            }
        });

        // Validate test cases
        const validTestCases = testCases.filter(tc =>
            tc.input_data.trim() !== '' || tc.expected_output.trim() !== ''
        );

        // Re-read textarea values (in case onchange didn't fire)
        document.querySelectorAll('.test-case-item').forEach(item => {
            const idx = parseInt(item.dataset.index);
            if (testCases[idx]) {
                const inputEl = item.querySelector('[data-field="input_data"]');
                const outputEl = item.querySelector('[data-field="expected_output"]');
                if (inputEl) testCases[idx].input_data = inputEl.value;
                if (outputEl) testCases[idx].expected_output = outputEl.value;
            }
        });

        const payload = {
            title,
            description,
            topic_tags: selectedTopicTags,
            difficulty,
            required_constructs: selectedRequired,
            banned_constructs: selectedBanned,
            templates,
            test_cases: testCases.filter(tc =>
                tc.input_data.trim() !== '' || tc.expected_output.trim() !== ''
            ),
        };

        showLoading(true, 'Saving problem...');

        try {
            let res;
            if (isEditMode) {
                res = await fetch(`/api/admin/problems/${editId}`, {
                    method: 'PUT',
                    headers: AUTH.getAuthHeaders(),
                    body: JSON.stringify(payload),
                });
            } else {
                res = await fetch('/api/admin/problems', {
                    method: 'POST',
                    headers: AUTH.getAuthHeaders(),
                    body: JSON.stringify(payload),
                });
            }

            const data = await res.json();

            if (res.ok && data.success) {
                showToast(isEditMode ? 'Problem updated!' : 'Problem created!', 'success');
                setTimeout(() => {
                    window.location.href = '/admin_dashboard.html';
                }, 1000);
            } else {
                showToast(data.detail || data.message || 'Save failed', 'error');
            }
        } catch (err) {
            showToast('Save failed. Is the server running?', 'error');
            console.error('Save error:', err);
        } finally {
            showLoading(false);
        }
    }

    // ── Helpers ──
    function showLoading(show, text) {
        const overlay = document.getElementById('loadingOverlay');
        const textEl = document.getElementById('loadingText');
        if (overlay) overlay.classList.toggle('visible', show);
        if (textEl && text) textEl.textContent = text;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
})();
