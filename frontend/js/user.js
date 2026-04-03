/**
 * user.js — Problem listing page logic
 * Fetches problems, renders cards, handles filtering.
 */

(function () {
    // Auth guard
    if (!AUTH.requireAuth()) return;
    AUTH.setupNavbar();
    AUTH.setupLogout();

    let allProblems = [];
    let allTags = new Set();

    // ── Fetch & Render ──
    async function loadProblems() {
        showLoading(true);
        try {
            const res = await fetch('/api/problems', {
                headers: AUTH.getAuthHeaders(),
            });

            if (res.status === 401) {
                AUTH.clearAuth();
                window.location.href = '/index.html';
                return;
            }

            const data = await res.json();
            allProblems = data.problems || [];

            // Collect all unique tags
            allTags.clear();
            allProblems.forEach(p => {
                (p.topic_tags || []).forEach(tag => allTags.add(tag));
            });

            populateTagFilter();
            renderProblems(allProblems);
        } catch (err) {
            showToast('Failed to load problems. Is the server running?', 'error');
            console.error('Load error:', err);
        } finally {
            showLoading(false);
        }
    }

    function populateTagFilter() {
        const select = document.getElementById('tagFilter');
        if (!select) return;

        // Keep the "All Topics" option
        const firstOption = select.querySelector('option');
        select.innerHTML = '';
        select.appendChild(firstOption);

        const sorted = Array.from(allTags).sort();
        sorted.forEach(tag => {
            const opt = document.createElement('option');
            opt.value = tag;
            opt.textContent = tag;
            select.appendChild(opt);
        });
    }

    function renderProblems(problems) {
        const grid = document.getElementById('problemsGrid');
        const empty = document.getElementById('emptyState');

        if (!grid) return;

        if (problems.length === 0) {
            grid.innerHTML = '';
            if (empty) empty.classList.remove('hidden');
            return;
        }

        if (empty) empty.classList.add('hidden');

        grid.innerHTML = problems.map(p => `
            <div class="problem-card glass-card" onclick="window.location.href='/solve.html?id=${p.id}'" data-id="${p.id}">
                <div class="problem-card-header">
                    <span class="problem-card-title">${escapeHtml(p.title)}</span>
                    <span class="badge badge-${p.difficulty.toLowerCase()}">${p.difficulty}</span>
                </div>
                <p class="problem-card-desc">${escapeHtml(p.description)}</p>
                <div class="problem-card-tags">
                    ${(p.topic_tags || []).map(tag =>
                        `<span class="badge badge-tag">${escapeHtml(tag)}</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');
    }

    // ── Filtering ──
    function applyFilters() {
        const difficulty = document.getElementById('difficultyFilter').value;
        const tag = document.getElementById('tagFilter').value;

        let filtered = allProblems;

        if (difficulty) {
            filtered = filtered.filter(p => p.difficulty === difficulty);
        }

        if (tag) {
            filtered = filtered.filter(p =>
                (p.topic_tags || []).some(t => t === tag)
            );
        }

        renderProblems(filtered);
    }

    document.getElementById('difficultyFilter')?.addEventListener('change', applyFilters);
    document.getElementById('tagFilter')?.addEventListener('change', applyFilters);

    // ── Helpers ──
    function showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.toggle('visible', show);
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Init ──
    loadProblems();
})();
