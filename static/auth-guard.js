/**
 * Auth Guard - Frontend Route Protection
 * Checks localStorage for user authentication and role-based access
 */

class AuthGuard {
    constructor() {
        this.role = localStorage.getItem('role');
        this.isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
        this.username = localStorage.getItem('username');
        this.userId = localStorage.getItem('user_id');
    }

    /**
     * Check if user is logged in
     */
    isAuthenticated() {
        return this.isLoggedIn && this.role;
    }

    /**
     * Check if user is admin
     */
    isAdmin() {
        return this.isAuthenticated() && this.role === 'admin';
    }

    /**
     * Check if user is regular user
     */
    isUser() {
        return this.isAuthenticated() && this.role === 'user';
    }

    /**
     * Require authentication - redirect to login if not authenticated
     */
    requireAuth(redirectToLogin = true) {
        if (!this.isAuthenticated()) {
            if (redirectToLogin) {
                window.location.href = '/login';
            }
            return false;
        }
        return true;
    }

    /**
     * Require admin role - show access denied if not admin
     */
    requireAdmin(showAccessDenied = true) {
        if (!this.isAdmin()) {
            if (showAccessDenied) {
                this.showAccessDenied();
            }
            return false;
        }
        return true;
    }

    /**
     * Require user role
     */
    requireUser(redirectToLogin = true) {
        if (!this.isUser()) {
            if (redirectToLogin) {
                window.location.href = '/login';
            }
            return false;
        }
        return true;
    }

    /**
     * Show access denied message
     */
    showAccessDenied() {
        document.body.innerHTML = `
            <div class="access-denied-container">
                <div class="access-denied-content">
                    <h1>🔒 Access Denied</h1>
                    <p>You do not have permission to access this page.</p>
                    <p style="color: #94a3b8; margin-top: 10px; font-size: 14px;">
                        Your role: <strong>${this.role}</strong>
                    </p>
                    <div style="margin-top: 30px;">
                        <a href="/user-dashboard" class="btn-primary" style="display: inline-block; text-decoration: none;">
                            Go to Dashboard
                        </a>
                        <a href="/logout" class="btn-secondary" style="display: inline-block; text-decoration: none; margin-left: 10px;">
                            Logout
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Logout - clear localStorage and redirect
     */
    logout() {
        localStorage.removeItem('role');
        localStorage.removeItem('user_id');
        localStorage.removeItem('username');
        localStorage.removeItem('isLoggedIn');
        window.location.href = '/login';
    }

    /**
     * Get user info
     */
    getUserInfo() {
        return {
            userId: this.userId,
            username: this.username,
            role: this.role,
            isLoggedIn: this.isLoggedIn
        };
    }

    /**
     * Manually set auth state (used after login via JS)
     */
    setAuth(role, userId, username) {
        localStorage.setItem('role', role);
        localStorage.setItem('user_id', userId);
        localStorage.setItem('username', username);
        localStorage.setItem('isLoggedIn', 'true');
        this.role = role;
        this.userId = userId;
        this.username = username;
        this.isLoggedIn = true;
    }
}

// Create global auth instance
const auth = new AuthGuard();

// Add styles for access denied page
if (!document.getElementById('auth-guard-styles')) {
    const style = document.createElement('style');
    style.id = 'auth-guard-styles';
    style.textContent = `
        .access-denied-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #0F172A;
            background-image: 
                radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                radial-gradient(at 50% 0%, hsla(225,39%,30%,0.2) 0, transparent 50%), 
                radial-gradient(at 100% 0%, hsla(339,49%,30%,0.2) 0, transparent 50%);
            font-family: 'Inter', sans-serif;
            color: #F8FAFC;
        }
        
        .access-denied-content {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        
        .access-denied-content h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #E0E7FF 0%, #818CF8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .access-denied-content p {
            color: #94A3B8;
            font-size: 16px;
            line-height: 1.6;
        }
    `;
    document.head.appendChild(style);
}
