/**
 * admin.js — Admin dashboard logic
 * Fetches and displays problems in a table, handles delete with confirmation.
 */

(function () {
    // Auth guard — admin only
    if (!AUTH.requireAuth('admin')) return;
    AUTH.setupNavbar();
    AUTH.setupLogout();

    let deleteTargetId = null;

    // ── Load Problems ──
    async function loadProblems() {
        showLoading(true);
        try {
            const res = await fetch('/api/admin/problems', {
                headers: AUTH.getAuthHeaders(),
            });

            if (res.status === 401 || res.status === 403) {
                AUTH.clearAuth();
                window.location.href = '/admin.html';
                return;
            }

            const data = await res.json();
            renderTable(data.problems || []);
        } catch (err) {
            showToast('Failed to load problems', 'error');
            console.error('Load error:', err);
        } finally {
            showLoading(false);
        }
    }

    function renderTable(problems) {
        const tbody = document.getElementById('problemsTableBody');
        const emptyState = document.getElementById('emptyState');
        const table = document.getElementById('problemsTable');

        if (problems.length === 0) {
            table.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        }

        table.classList.remove('hidden');
        emptyState.classList.add('hidden');

        tbody.innerHTML = problems.map(p => {
            const tags = (p.topic_tags || []).map(t =>
                `<span class="badge badge-tag" style="font-size:0.7rem;">${escapeHtml(t)}</span>`
            ).join(' ');

            const diffBadge = `<span class="badge badge-${p.difficulty.toLowerCase()}">${p.difficulty}</span>`;

            return `
                <tr>
                    <td style="color:var(--text-muted); font-family:var(--font-mono);">${p.id}</td>
                    <td>
                        <a href="/admin_edit.html?id=${p.id}" style="color:var(--text-bright); font-weight:500;">
                            ${escapeHtml(p.title)}
                        </a>
                    </td>
                    <td>${diffBadge}</td>
                    <td>${tags || '<span style="color:var(--text-muted);">—</span>'}</td>
                    <td style="color:var(--text-muted); font-size:0.85rem;">—</td>
                    <td>
                        <div class="actions">
                            <a href="/admin_edit.html?id=${p.id}" class="btn btn-secondary btn-sm">Edit</a>
                            <button class="btn btn-danger btn-sm" onclick="confirmDelete(${p.id})">Delete</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // ── Delete ──
    window.confirmDelete = function (id) {
        deleteTargetId = id;
        document.getElementById('deleteModal').style.display = 'block';
    };

    document.getElementById('cancelDeleteBtn')?.addEventListener('click', () => {
        deleteTargetId = null;
        document.getElementById('deleteModal').style.display = 'none';
    });

    document.getElementById('confirmDeleteBtn')?.addEventListener('click', async () => {
        if (!deleteTargetId) return;

        const modal = document.getElementById('deleteModal');
        const btn = document.getElementById('confirmDeleteBtn');

        btn.disabled = true;
        btn.textContent = 'Deleting...';

        try {
            const res = await fetch(`/api/admin/problems/${deleteTargetId}`, {
                method: 'DELETE',
                headers: AUTH.getAuthHeaders(),
            });

            if (res.ok) {
                showToast('Problem deleted successfully', 'success');
                loadProblems();
            } else {
                const data = await res.json();
                showToast(data.detail || 'Failed to delete', 'error');
            }
        } catch (err) {
            showToast('Delete failed', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Delete';
            deleteTargetId = null;
            modal.style.display = 'none';
        }
    });

    // Close modal on backdrop click
    document.getElementById('deleteModal')?.addEventListener('click', function (e) {
        if (e.target === this) {
            deleteTargetId = null;
            this.style.display = 'none';
        }
    });

    // ── Helpers ──
    function showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.classList.toggle('visible', show);
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
