// static/app.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const nameInput = document.getElementById('username');
        const username = nameInput.value.trim();
        
        if (!username) return;

        // Перенаправляем на серверный /profile, передавая имя в URL
        window.location.href = '/profile?user=' + encodeURIComponent(username);
    });
});