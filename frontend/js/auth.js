/**
 * auth.js — Shared authentication utilities
 * Handles login, logout, token management, and auth guards.
 */

const AUTH = {
    TOKEN_KEY: 'ast_token',
    ROLE_KEY: 'ast_role',
    USERNAME_KEY: 'ast_username',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    getRole() {
        return localStorage.getItem(this.ROLE_KEY);
    },

    getUsername() {
        return localStorage.getItem(this.USERNAME_KEY);
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    setAuth(token, role, username) {
        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.ROLE_KEY, role);
        localStorage.setItem(this.USERNAME_KEY, username);
    },

    clearAuth() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.ROLE_KEY);
        localStorage.removeItem(this.USERNAME_KEY);
    },

    getAuthHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : '',
        };
    },

    /** Redirect to login if not authenticated */
    requireAuth(requiredRole) {
        if (!this.isLoggedIn()) {
            window.location.href = '/index.html';
            return false;
        }
        if (requiredRole && this.getRole() !== requiredRole) {
            window.location.href = '/index.html';
            return false;
        }
        return true;
    },

    /** Set up user display in navbar */
    setupNavbar() {
        const username = this.getUsername() || 'User';
        const avatarEl = document.getElementById('userAvatar');
        const nameEl = document.getElementById('userName');

        if (avatarEl) avatarEl.textContent = username.charAt(0).toUpperCase();
        if (nameEl) nameEl.textContent = username;
    },

    /** Set up logout button */
    setupLogout() {
        const btn = document.getElementById('logoutBtn');
        if (btn) {
            btn.addEventListener('click', async () => {
                try {
                    const token = this.getToken();
                    if (token) {
                        await fetch(`/api/logout?token=${token}`, { method: 'POST' });
                    }
                } catch (e) {
                    // Ignore errors during logout
                }
                this.clearAuth();
                window.location.href = '/index.html';
            });
        }
    },
};

// ── Login form handler (for index.html) ──
(function () {
    const form = document.getElementById('loginForm');
    if (!form) return;

    // If on index.html (not admin.html) and already logged in, redirect
    const isAdminPage = window.location.pathname.includes('admin');
    if (!isAdminPage && AUTH.isLoggedIn()) {
        const role = AUTH.getRole();
        if (role === 'admin') {
            window.location.href = '/admin_dashboard.html';
        } else {
            window.location.href = '/user.html';
        }
        return;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('loginError');
        const btn = document.getElementById('loginBtn');

        if (!username || !password) {
            errorEl.textContent = 'Please enter both username and password.';
            errorEl.style.display = 'block';
            errorEl.classList.add('visible');
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Signing in...';
        errorEl.style.display = 'none';

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            const data = await res.json();

            if (data.success) {
                AUTH.setAuth(data.token, data.role, username);

                if (data.role === 'admin') {
                    window.location.href = '/admin_dashboard.html';
                } else {
                    window.location.href = '/user.html';
                }
            } else {
                errorEl.textContent = data.message || 'Invalid credentials';
                errorEl.style.display = 'block';
                errorEl.classList.add('visible');
            }
        } catch (err) {
            errorEl.textContent = 'Connection error. Is the server running?';
            errorEl.style.display = 'block';
            errorEl.classList.add('visible');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    });
})();

// ── Toast notification system ──
function showToast(message, type = 'success', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = { success: '✓', error: '✕', warning: '⚠' };
    toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
