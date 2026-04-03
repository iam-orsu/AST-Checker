/**
 * solve.js — Problem solving page logic
 * Monaco Editor with constrained-editor-plugin for locked/editable zones.
 * Debounced real-time AST constraint checking with violation highlighting.
 * Submit flow: AST check → Docker execution → results display.
 */

(function () {
    // Auth guard
    if (!AUTH.requireAuth()) return;
    AUTH.setupNavbar();
    AUTH.setupLogout();

    // ── State ──
    let editor = null;
    let monacoInstance = null;
    let constrainedInstance = null;
    let currentProblem = null;
    let currentTemplate = null;
    let currentLanguage = 'python';
    let violationDecorations = [];
    let editableDecorations = [];
    let lockedDecorations = [];
    let constraintCheckTimer = null;
    const DEBOUNCE_MS = 1500;

    // Get problem ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const problemId = urlParams.get('id');

    if (!problemId) {
        window.location.href = '/user.html';
        return;
    }

    // ── Monaco Language Map ──
    const MONACO_LANG_MAP = {
        python: 'python',
        c: 'c',
        cpp: 'cpp',
        'c++': 'cpp',
        java: 'java',
        javascript: 'javascript',
        js: 'javascript',
    };

    // ── Load Monaco Editor ──
    require.config({
        paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' },
    });

    require(['vs/editor/editor.main'], function (monaco) {
        monacoInstance = monaco;

        // Define custom dark theme
        monaco.editor.defineTheme('astDark', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'comment', foreground: '6A6A7A', fontStyle: 'italic' },
                { token: 'keyword', foreground: 'E94560' },
                { token: 'string', foreground: '2ECC71' },
                { token: 'number', foreground: 'F39C12' },
                { token: 'type', foreground: '3498DB' },
            ],
            colors: {
                'editor.background': '#1a1a2e',
                'editor.foreground': '#e0e0e0',
                'editor.lineHighlightBackground': '#16213e',
                'editor.selectionBackground': '#0f346050',
                'editorCursor.foreground': '#e94560',
                'editorLineNumber.foreground': '#6a6a7a',
                'editorLineNumber.activeForeground': '#e94560',
            },
        });

        editor = monaco.editor.create(document.getElementById('monacoEditor'), {
            value: '// Loading...',
            language: 'python',
            theme: 'astDark',
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            padding: { top: 12 },
            automaticLayout: true,
            tabSize: 4,
            insertSpaces: true,
            renderWhitespace: 'all',
            renderControlCharacters: true,
            detectIndentation: false,
            wordWrap: 'on',
        });

        // Set up content change listener for debounced constraint checking
        editor.onDidChangeModelContent(() => {
            clearTimeout(constraintCheckTimer);
            constraintCheckTimer = setTimeout(() => {
                checkConstraints();
            }, DEBOUNCE_MS);
        });

        // Load the problem
        loadProblem();
    });

    // ── Load Problem ──
    async function loadProblem() {
        showLoading(true, 'Loading problem...');
        try {
            const res = await fetch(`/api/problems/${problemId}?language=${currentLanguage}`, {
                headers: AUTH.getAuthHeaders(),
            });

            if (res.status === 401) {
                AUTH.clearAuth();
                window.location.href = '/index.html';
                return;
            }

            if (res.status === 404) {
                showToast('Problem not found', 'error');
                window.location.href = '/user.html';
                return;
            }

            currentProblem = await res.json();

            // Render problem info
            renderProblemInfo();

            // Populate language selector
            populateLanguages();

            // Load template for current language
            if (currentProblem.template) {
                currentTemplate = currentProblem.template;
                applyTemplate();
            } else {
                editor.setValue('// No template available for this language');
                editor.updateOptions({ readOnly: true });
            }
        } catch (err) {
            showToast('Failed to load problem', 'error');
            console.error('Load error:', err);
        } finally {
            showLoading(false);
        }
    }

    function renderProblemInfo() {
        const p = currentProblem;

        document.getElementById('problemTitle').textContent = p.title;
        document.title = `${p.title} — AST-Compiler`;

        // Meta badges
        const metaEl = document.getElementById('problemMeta');
        metaEl.innerHTML = `
            <span class="badge badge-${p.difficulty.toLowerCase()}">${p.difficulty}</span>
            ${(p.topic_tags || []).map(tag =>
                `<span class="badge badge-tag">${escapeHtml(tag)}</span>`
            ).join('')}
        `;

        // Description (simple markdown rendering)
        const descEl = document.getElementById('problemDescription');
        descEl.innerHTML = renderMarkdown(p.description);

        // Sample test cases
        const testsEl = document.getElementById('sampleTestsList');
        if (p.sample_tests && p.sample_tests.length > 0) {
            testsEl.innerHTML = p.sample_tests.map((tc, i) => `
                <div style="padding:12px; background:var(--bg-secondary); border:1px solid var(--border); border-radius:var(--radius-md); margin-bottom:8px;">
                    <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:6px;">Test Case ${i + 1}</div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <div>
                            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">Input</div>
                            <pre style="font-size:0.82rem; padding:8px; background:var(--bg-primary); border-radius:var(--radius-sm); margin:0; white-space:pre-wrap;">${escapeHtml(tc.input_data)}</pre>
                        </div>
                        <div>
                            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">Expected Output</div>
                            <pre style="font-size:0.82rem; padding:8px; background:var(--bg-primary); border-radius:var(--radius-sm); margin:0; white-space:pre-wrap;">${escapeHtml(tc.expected_output)}</pre>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            testsEl.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem;">No sample test cases available.</p>';
        }

        // Show constraint info
        if (p.required_constructs && p.required_constructs.length > 0) {
            const reqHtml = p.required_constructs.map(c => `<span class="badge badge-tag" style="border-color:var(--success); color:var(--success);">✓ ${c.replace(/_/g, ' ')}</span>`).join(' ');
            descEl.innerHTML += `<div style="margin-top:16px;"><strong>Required:</strong> ${reqHtml}</div>`;
        }
        if (p.banned_constructs && p.banned_constructs.length > 0) {
            const banHtml = p.banned_constructs.map(c => `<span class="badge badge-tag" style="border-color:var(--error); color:var(--error);">✕ ${c.replace(/_/g, ' ')}</span>`).join(' ');
            descEl.innerHTML += `<div style="margin-top:8px;"><strong>Banned:</strong> ${banHtml}</div>`;
        }
    }

    function populateLanguages() {
        const select = document.getElementById('languageSelect');
        select.innerHTML = '';

        const langs = currentProblem.available_languages || [];
        const labelMap = {
            python: 'Python',
            c: 'C',
            cpp: 'C++',
            java: 'Java',
            javascript: 'JavaScript',
        };

        langs.forEach(lang => {
            const opt = document.createElement('option');
            opt.value = lang;
            opt.textContent = labelMap[lang] || lang;
            if (lang === currentLanguage) opt.selected = true;
            select.appendChild(opt);
        });

        // If current language not in available, switch to first available
        if (langs.length > 0 && !langs.includes(currentLanguage)) {
            currentLanguage = langs[0];
            select.value = currentLanguage;
            loadTemplate(currentLanguage);
        }
    }

    // ── Apply Template to Editor ──
    function applyTemplate() {
        if (!editor || !currentTemplate) return;

        const monacoLang = MONACO_LANG_MAP[currentLanguage] || 'plaintext';

        // Tear down existing constraints completely before re-applying
        teardownConstraints();

        // Set editor content and language
        const model = editor.getModel();
        monacoInstance.editor.setModelLanguage(model, monacoLang);
        editor.setValue(currentTemplate.template_code);

        const editableRanges = currentTemplate.editable_ranges || [];

        if (editableRanges.length === 0) {
            // No editable ranges — make entire editor read-only with warning
            editor.updateOptions({ readOnly: true });
            document.getElementById('noEditableBanner').classList.add('visible');
            applyLockedDecorations(1, model.getLineCount());
        } else {
            editor.updateOptions({ readOnly: false });
            document.getElementById('noEditableBanner').classList.remove('visible');

            // Apply visual decorations for locked and editable zones
            applyZoneDecorations(editableRanges, model.getLineCount());

            // Apply constrained-editor-plugin restrictions
            applyConstraints(editableRanges);
        }

        // Clear any previous violations
        clearViolations();

        // Update constraint status
        document.getElementById('constraintStatus').textContent = 'Ready';
        document.getElementById('constraintStatus').style.color = 'var(--text-muted)';
    }

    function teardownConstraints() {
        // Completely tear down constrained-editor-plugin to avoid bleed between languages.
        // The plugin doesn't have a clean dispose API, so we destroy and recreate the model.
        if (constrainedInstance) {
            try {
                // The plugin attaches listeners to the model. Replacing the model is the
                // only reliable way to remove all restrictions without calling private APIs.
                const oldValue = editor.getValue();
                const oldLang = editor.getModel().getLanguageId();
                const newModel = monacoInstance.editor.createModel(oldValue, oldLang);
                editor.setModel(newModel);
            } catch (e) {
                // Fallback: just continue — new constraints will override
            }
            constrainedInstance = null;
        }

        // Clear all decorations
        if (editor) {
            violationDecorations = editor.deltaDecorations(violationDecorations, []);
            editableDecorations = editor.deltaDecorations(editableDecorations, []);
            lockedDecorations = editor.deltaDecorations(lockedDecorations, []);
        }
    }

    function applyConstraints(editableRanges) {
        if (!editor || !monacoInstance) return;

        try {
            // Initialize constrained editor plugin fresh
            constrainedInstance = constrainedEditor(monacoInstance);
            constrainedInstance.initializeIn(editor);

            const model = editor.getModel();
            const totalLines = model.getLineCount();

            // Clamp ranges to actual model line count to prevent OOB crash
            const clampedRanges = editableRanges
                .map(range => ({
                    startLine: Math.max(1, Math.min(range.startLine, totalLines)),
                    endLine: Math.max(1, Math.min(range.endLine, totalLines)),
                }))
                .filter(range => range.startLine <= range.endLine);

            const restrictions = clampedRanges.map((range, idx) => {
                const endLineContent = model.getLineContent(range.endLine);
                return {
                    range: [range.startLine, 1, range.endLine, endLineContent.length + 1],
                    label: `editable-range-${idx}`,
                    allowMultiline: true,
                };
            });

            constrainedInstance.addRestrictionsTo(model, restrictions);
        } catch (err) {
            console.error('Failed to apply constraints:', err);
            // Fallback: editor remains fully editable
        }
    }

    function applyZoneDecorations(editableRanges, totalLines) {
        const newEditable = [];
        const newLocked = [];

        // Build set of editable line numbers (clamped to actual line count)
        const editableLines = new Set();
        editableRanges.forEach(range => {
            const start = Math.max(1, range.startLine);
            const end = Math.min(totalLines, range.endLine);
            for (let i = start; i <= end; i++) {
                editableLines.add(i);
            }
        });

        // Apply decorations line by line
        for (let line = 1; line <= totalLines; line++) {
            if (editableLines.has(line)) {
                newEditable.push({
                    range: new monacoInstance.Range(line, 1, line, 1),
                    options: {
                        isWholeLine: true,
                        className: 'editable-line-decoration',
                        glyphMarginClassName: 'editable-line-gutter',
                    },
                });
            } else {
                newLocked.push({
                    range: new monacoInstance.Range(line, 1, line, 1),
                    options: {
                        isWholeLine: true,
                        className: 'locked-line-decoration',
                        glyphMarginClassName: 'locked-line-gutter',
                    },
                });
            }
        }

        editableDecorations = editor.deltaDecorations(editableDecorations, newEditable);
        lockedDecorations = editor.deltaDecorations(lockedDecorations, newLocked);
    }

    function applyLockedDecorations(startLine, endLine) {
        const newLocked = [];
        for (let line = startLine; line <= endLine; line++) {
            newLocked.push({
                range: new monacoInstance.Range(line, 1, line, 1),
                options: {
                    isWholeLine: true,
                    className: 'locked-line-decoration',
                    glyphMarginClassName: 'locked-line-gutter',
                },
            });
        }
        lockedDecorations = editor.deltaDecorations(lockedDecorations, newLocked);
    }

    // ── Language Switching ──
    document.getElementById('languageSelect')?.addEventListener('change', async function () {
        const newLang = this.value;
        if (newLang === currentLanguage) return;

        currentLanguage = newLang;
        await loadTemplate(currentLanguage);
    });

    async function loadTemplate(language) {
        try {
            const res = await fetch(`/api/problems/${problemId}/template/${language}`, {
                headers: AUTH.getAuthHeaders(),
            });

            if (res.ok) {
                currentTemplate = await res.json();
                applyTemplate();
            } else {
                currentTemplate = null;
                teardownConstraints();
                editor.setValue(`// No template available for ${language}`);
                editor.updateOptions({ readOnly: true });
                document.getElementById('noEditableBanner').classList.add('visible');
            }
        } catch (err) {
            console.error('Template load error:', err);
            showToast('Failed to load template', 'error');
        }
    }

    // ── Real-time Constraint Checking ──
    async function checkConstraints() {
        if (!editor || !currentProblem) return;

        const code = editor.getValue();
        const statusEl = document.getElementById('constraintStatus');

        statusEl.textContent = 'Checking...';
        statusEl.style.color = 'var(--warning)';

        try {
            const res = await fetch('/api/check-constraints', {
                method: 'POST',
                headers: AUTH.getAuthHeaders(),
                body: JSON.stringify({
                    code: code,
                    language: currentLanguage,
                    problem_id: parseInt(problemId),
                }),
            });

            const data = await res.json();

            if (data.passed) {
                clearViolations();
                statusEl.textContent = '✓ Constraints OK';
                statusEl.style.color = 'var(--success)';
            } else {
                showViolations(data.violations || []);
                statusEl.textContent = '✕ Violations found';
                statusEl.style.color = 'var(--error)';
            }
        } catch (err) {
            statusEl.textContent = 'Check failed';
            statusEl.style.color = 'var(--text-muted)';
        }
    }

    function showViolations(violations) {
        // Show violation messages
        const msgEl = document.getElementById('violationMessage');
        const listEl = document.getElementById('violationList');

        if (violations.length === 0) {
            clearViolations();
            return;
        }

        listEl.innerHTML = violations.map(v =>
            `<li>${escapeHtml(v.message)}</li>`
        ).join('');
        msgEl.classList.add('visible');

        // Highlight violation lines in Monaco with red glow
        const newDecorations = violations
            .filter(v => v.line > 0)
            .map(v => ({
                range: new monacoInstance.Range(v.line, 1, v.line, 1),
                options: {
                    isWholeLine: true,
                    className: 'violation-line-decoration',
                    glyphMarginClassName: 'violation-line-gutter',
                },
            }));

        violationDecorations = editor.deltaDecorations(violationDecorations, newDecorations);
    }

    function clearViolations() {
        const msgEl = document.getElementById('violationMessage');
        if (msgEl) msgEl.classList.remove('visible');

        if (editor) {
            violationDecorations = editor.deltaDecorations(violationDecorations, []);
        }
    }

    // ── Submit ──
    document.getElementById('submitBtn')?.addEventListener('click', submitCode);

    async function submitCode() {
        if (!editor || !currentProblem) return;

        const code = editor.getValue();
        const submitBtn = document.getElementById('submitBtn');

        submitBtn.disabled = true;
        showLoading(true, 'Running AST check & executing code...');

        try {
            const res = await fetch('/api/submit', {
                method: 'POST',
                headers: AUTH.getAuthHeaders(),
                body: JSON.stringify({
                    code: code,
                    language: currentLanguage,
                    problem_id: parseInt(problemId),
                }),
            });

            const data = await res.json();
            displayResults(data);

            if (data.status === 'constraint_failed') {
                showViolations(data.constraint_check?.violations || []);
                showToast('Constraint check failed', 'error');
            } else if (data.status === 'accepted') {
                clearViolations();
                showToast('All test cases passed! ✓', 'success');
            } else if (data.status === 'wrong_answer') {
                clearViolations();
                showToast('Some test cases failed', 'warning');
            } else if (data.status === 'timeout') {
                clearViolations();
                showToast('Time limit exceeded', 'error');
            } else if (data.status === 'runtime_error') {
                clearViolations();
                showToast('Runtime error', 'error');
            }
        } catch (err) {
            showToast('Submission failed. Is the server running?', 'error');
            console.error('Submit error:', err);
        } finally {
            submitBtn.disabled = false;
            showLoading(false);
        }
    }

    function displayResults(data) {
        const panel = document.getElementById('resultsPanel');
        const statusEl = document.getElementById('resultsStatus');
        const summaryEl = document.getElementById('resultsSummary');
        const listEl = document.getElementById('testResultsList');

        panel.classList.add('visible');

        // Status
        const statusLabels = {
            accepted: 'Accepted',
            wrong_answer: 'Wrong Answer',
            constraint_failed: 'Constraint Failed',
            runtime_error: 'Runtime Error',
            timeout: 'Time Limit Exceeded',
        };

        statusEl.textContent = statusLabels[data.status] || data.status;
        statusEl.className = 'results-status ' +
            (data.status === 'accepted' ? 'accepted' : 'failed');

        // Summary
        if (data.total_tests > 0) {
            summaryEl.textContent = ` — ${data.total_passed}/${data.total_tests} passed` +
                (data.execution_time ? ` (${data.execution_time}s)` : '');
        } else if (data.status === 'constraint_failed') {
            summaryEl.textContent = ' — Fix constraint violations before running tests';
        } else {
            summaryEl.textContent = '';
        }

        // Test results
        if (data.test_results && data.test_results.length > 0) {
            listEl.innerHTML = data.test_results.map((tr, i) => `
                <div class="test-result-item ${tr.passed ? 'passed' : 'failed'}">
                    <div class="test-result-header">
                        <span class="test-result-label">
                            ${tr.passed
                                ? '<span class="icon-pass">✓</span>'
                                : '<span class="icon-fail">✕</span>'}
                            Test Case ${i + 1}
                        </span>
                    </div>
                    <div class="test-result-detail">
                        <div>
                            <span class="label">Input</span>
                            <div class="value">${escapeHtml(tr.input_data)}</div>
                        </div>
                        <div>
                            <span class="label">Expected</span>
                            <div class="value">${escapeHtml(tr.expected_output)}</div>
                        </div>
                        <div>
                            <span class="label">Actual</span>
                            <div class="value" style="${tr.passed ? '' : 'color:var(--error);'}">${escapeHtml(tr.actual_output || tr.error || '(empty)')}</div>
                        </div>
                    </div>
                </div>
            `).join('');
        } else if (data.status === 'constraint_failed' && data.constraint_check?.violations) {
            listEl.innerHTML = `
                <div style="padding:16px; color:var(--error); font-size:0.9rem;">
                    <p style="margin-bottom:8px; font-weight:600;">Constraint Violations:</p>
                    <ul style="padding-left:16px;">
                        ${data.constraint_check.violations.map(v =>
                            `<li style="margin-bottom:4px;">${escapeHtml(v.message)}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        } else {
            listEl.innerHTML = '<p style="padding:16px; color:var(--text-muted);">No test results.</p>';
        }
    }

    // Close results panel
    document.getElementById('closeResultsBtn')?.addEventListener('click', () => {
        document.getElementById('resultsPanel').classList.remove('visible');
    });

    // ── Reset ──
    document.getElementById('resetBtn')?.addEventListener('click', () => {
        if (currentTemplate) {
            applyTemplate();
            clearViolations();
            document.getElementById('resultsPanel').classList.remove('visible');
            showToast('Editor reset to template', 'success');
        }
    });

    // ── Resizer ──
    (function initResizer() {
        const resizer = document.getElementById('solveResizer');
        const leftPanel = document.getElementById('solveLeft');
        if (!resizer || !leftPanel) return;

        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const containerRect = leftPanel.parentElement.getBoundingClientRect();
            const newWidth = e.clientX - containerRect.left;
            const minWidth = 280;
            const maxWidth = containerRect.width * 0.7;
            if (newWidth >= minWidth && newWidth <= maxWidth) {
                leftPanel.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                if (editor) editor.layout();
            }
        });
    })();

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

    function renderMarkdown(md) {
        if (!md) return '';
        // Simple markdown rendering
        let html = md
            // Headers
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            // Code blocks
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold + italic
            .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
            // Bold
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Unordered lists
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            // Line breaks for paragraphs
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        // Wrap loose <li> tags in <ul>
        html = html.replace(/((?:<li>.*?<\/li>\s*)+)/g, '<ul>$1</ul>');

        return `<p>${html}</p>`;
    }
})();
