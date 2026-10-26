document.addEventListener('DOMContentLoaded', async () => {
    
    const urlParams = new URLSearchParams(window.location.search);
    const username = urlParams.get('user');

    if (!username) {
        window.location.href = '/';
        return;
    }

    const buttons = document.querySelectorAll('.theme-switch button');
    const saveIndicator = document.getElementById('theme-save-indicator');

    function applyTheme(themeName) {
        document.body.classList.remove('light', 'dark'); 
        document.body.classList.add(themeName);

        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === themeName);
        });
    }

    // Загрузка темы с сервера
    try {
        const res = await fetch(`/api/get_theme?user=${encodeURIComponent(username)}`);
        const data = await res.json();
        applyTheme(data && data.theme ? data.theme : 'light'); 
    } catch (error) {
        console.error("Ошибка связи с API (загрузка):", error);
        applyTheme('light'); 
    }

    // Обработчик клика по кнопкам смены темы
    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const selectedTheme = btn.dataset.theme;
            applyTheme(selectedTheme);
            
            if (saveIndicator) {
                saveIndicator.classList.remove('show');
                setTimeout(() => {
                    saveIndicator.classList.add('show');
                    setTimeout(() => {
                        saveIndicator.classList.remove('show');
                    }, 2000);
                }, 10);
            }

            try {
                await fetch('/api/save_theme', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({
                        user: username,
                        theme: selectedTheme
                    }).toString()
                });
            } catch (e) {
                console.error("Не удалось сохранить тему на сервере", e);
            }
        });
    });

    // Логика импорта JSON-файлов
    const importForm = document.getElementById('importForm');
    const fileInput = document.getElementById('jsonFileInput');
    const resultMessage = document.getElementById('importResult');

    if (importForm) {
        importForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const file = fileInput.files[0];
            if (!file) return;

            const reader = new FileReader();
            
            reader.onload = async (event) => {
                try {
                    const jsonText = event.target.result;
                    
                    // Проверка валидности структуры перед отправкой
                    JSON.parse(jsonText); 

                    const response = await fetch('/api/import_recipes', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: jsonText
                    });

                    const result = await response.json();

                    if (response.ok && result.status === 'ok') {
                        resultMessage.style.color = '#42b72a';
                        resultMessage.textContent = `Успешно добавлено новых рецептов: ${result.imported_recipes}`;
                        importForm.reset();
                    } else {
                        resultMessage.style.color = '#e41e3f';
                        resultMessage.textContent = `Ошибка: ${result.message || 'Не удалось импортировать данные.'}`;
                    }

                } catch (error) {
                    resultMessage.style.color = '#e41e3f';
                    resultMessage.textContent = 'Ошибка: Выбранный файл поврежден или не является корректным JSON.';
                    console.error(error);
                }
            };

            reader.readAsText(file);
        });
    }
});
