// Main Application Logic

console.log('LaunderPro Enterprise App Loaded');

// Global Error Handler for fetch requests
window.handleFetchError = (error) => {
    console.error('API Error:', error);
    alert('An unexpected error occurred. Please try again.');
};

// Utilities
function formatCurrency(amount) {
    return '₦' + amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

// Mobile Menu Logic
function toggleMobileMenu() {
    const sidebar = document.getElementById('mobile-sidebar');
    const backdrop = document.getElementById('mobile-backdrop');

    if (!sidebar || !backdrop) return;

    if (sidebar.classList.contains('hidden')) {
        // Open Menu
        sidebar.classList.remove('hidden');
        sidebar.classList.remove('-translate-x-full');
        backdrop.classList.remove('hidden');
    } else {
        // Close Menu
        sidebar.classList.add('-translate-x-full');
        backdrop.classList.add('hidden');
        setTimeout(() => {
            sidebar.classList.add('hidden');
        }, 300); // Wait for transition
    }
}

// Auth UI Logic
function updateAuthUI() {
    const token = localStorage.getItem('access_token');

    // Navbar
    const navGuest = document.getElementById('nav-guest');
    const navUser = document.getElementById('nav-user');

    if (navGuest && navUser) {
        if (token) {
            navGuest.classList.add('hidden');
            navUser.classList.remove('hidden');
        } else {
            navGuest.classList.remove('hidden');
            navUser.classList.add('hidden');
        }
    }

    // Hero Section (Landing Page)
    const heroGuest = document.getElementById('hero-guest');
    const heroUser = document.getElementById('hero-user');
    if (heroGuest && heroUser) {
        if (token) {
            heroGuest.classList.add('hidden');
            heroUser.classList.remove('hidden');
        } else {
            heroGuest.classList.remove('hidden');
            heroUser.classList.add('hidden');
        }
    }

    // CTA Section (Landing Page)
    const ctaGuest = document.getElementById('cta-guest');
    const ctaUser = document.getElementById('cta-user');
    if (ctaGuest && ctaUser) {
        if (token) {
            ctaGuest.classList.add('hidden');
            ctaUser.classList.remove('hidden');
        } else {
            ctaGuest.classList.remove('hidden');
            ctaUser.classList.add('hidden');
        }
    }
}

async function goToDashboard(e) {
    if (e) e.preventDefault();
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    try {
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (res.ok) {
            const user = await res.json();
            switch (user.role) {
                case 'admin': window.location.href = '/admin/dashboard'; break;
                case 'staff': window.location.href = '/staff/dashboard'; break;
                case 'rider': window.location.href = '/rider/dashboard'; break;
                default: window.location.href = '/dashboard';
            }
        } else {
            // Invalid token?
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
    } catch (e) {
        console.error('Nav Error:', e);
        window.location.href = '/dashboard';
    }
}

document.addEventListener('DOMContentLoaded', updateAuthUI);
