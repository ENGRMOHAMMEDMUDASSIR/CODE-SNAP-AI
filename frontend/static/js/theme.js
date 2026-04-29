// frontend/static/js/theme.js - Auto Dark/Light Theme Switcher

function detectSystemTheme() {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    } else {
        return 'light';
    }
}

function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
        localStorage.setItem('codeSnapTheme', 'dark');
    } else {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
        localStorage.setItem('codeSnapTheme', 'light');
    }
}

function getInitialTheme() {
    const savedTheme = localStorage.getItem('codeSnapTheme');
    if (savedTheme) {
        return savedTheme;
    }
    return detectSystemTheme();
}

function initTheme() {
    const theme = getInitialTheme();
    applyTheme(theme);
    
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('codeSnapTheme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}

async function getFormattingSuggestions(language, code) {
    try {
        const response = await fetch('/api/formatting-suggestions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ language: language, code: code })
        });
        
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to get formatting suggestions:', error);
    }
    
    return {
        theme: 'default',
        font: 'monospace',
        font_size: 14,
        suggestions: ['Use consistent formatting', 'Add comments for clarity']
    };
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === 'success' ? '#238636' : '#f85149'};
        color: white;
        border-radius: 8px;
        z-index: 10000;
        animation: fadeInOut 3s ease;
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
});