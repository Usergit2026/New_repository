import json
import sqlite3
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DB_NAME = 'fridgechef.db'

def init_db():
    db_exists = os.path.exists(DB_NAME)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, email TEXT UNIQUE, password_hash TEXT, theme TEXT DEFAULT 'light', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ingredients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_fridge (user_id INTEGER, ingredient_id INTEGER, PRIMARY KEY (user_id, ingredient_id), FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL UNIQUE, cooking_time_min INTEGER, instructions TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS recipe_ingredients (recipe_id INTEGER, ingredient_id INTEGER, PRIMARY KEY (recipe_id, ingredient_id), FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE, FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE)")
    if not db_exists:
        base_ingredients = [('Пармезан',), ('Томаты черри',), ('Спагетти',), ('Оливковое масло',), ('Чеснок',), ('Базилик',)]
        cursor.executemany("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", base_ingredients)
        recipes_data = [
            ('Паста Черри-Пармезан', 15, 'Отварить спагетти, обжарить томаты, смешать и посыпать пармезаном.'),
            ('Томатный суп с гренками', 25, 'Перетереть томаты, добавить оливковое масло и специи, подавать с гренками.'),
            ('Запеченные томаты', 20, 'Запечь томаты в духовке с чесноком и базиликом.')
        ]
        cursor.executemany("INSERT OR IGNORE INTO recipes (title, cooking_time_min, instructions) VALUES (?, ?, ?)", recipes_data)
        cursor.executemany("INSERT OR IGNORE INTO recipe_ingredients (recipe_id, ingredient_id) VALUES (?, ?)", [
            (1, 1), (1, 2), (1, 3),
            (2, 2), (2, 4),
            (3, 2), (3, 5), (3, 6)
        ])
    conn.commit()
    conn.close()
class CustomHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path == '/':
            self.serve_html('index.html')
            return
        if path == '/profile':
            query_params = parse_qs(parsed_path.query)
            username = query_params.get('user', ['Гость'])[0]
            try:
                with open('profile.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                html_content = html_content.replace('{greeting}', f'Привет, {username}!')
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "Файл профиля не найден")
            return
        if path.startswith('/static/'):
            filename = path[1:] 
            try:
                with open(filename, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                if filename.endswith('.css'):
                    self.send_header('Content-type', 'text/css; charset=utf-8')
                elif filename.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript; charset=utf-8')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "Статичный файл не найден")
            return
        if path == '/api/get_theme':
            query_params = parse_qs(parsed_path.query)
            user = query_params.get('user', [''])[0]
            theme = 'light'
            if user:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT theme FROM users WHERE username = ?", (user,))
                row = cursor.fetchone()
                if row:
                    theme = row[0]
                else:
                    cursor.execute("INSERT INTO users (username, theme) VALUES (?, ?)", (user, theme))
                    conn.commit()
                conn.close()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'theme': theme}).encode('utf-8'))
            return
        if path == '/api/export_recipes':
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, cooking_time_min, instructions FROM recipes")
                recipes_rows = cursor.fetchall()
                exported_data = []
                for r_id, title, time_min, inst in recipes_rows:
                    cursor.execute("SELECT i.name FROM ingredients i JOIN recipe_ingredients ri ON i.id = ri.ingredient_id WHERE ri.recipe_id = ?", (r_id,))
                    ingredients = [row[0] for row in cursor.fetchall()]
                    exported_data.append({
                        "title": title,
                        "cooking_time_min": time_min,
                        "instructions": inst,
                        "ingredients": ingredients
                    })
                conn.close()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename=exported_recipes.json')
                self.end_headers()
                self.wfile.write(json.dumps(exported_data, ensure_ascii=False, indent=4).encode('utf-8'))
                return
            except Exception as e:
                self.send_error(500, f"Ошибка при экспорте: {str(e)}")
                return
        if path == '/logout':
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        self.send_error(404, "Страница не найдена")

    def do_POST(self):
        if self.path == '/api/save_theme':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = parse_qs(post_data.decode('utf-8'))
            user = params.get('user', [''])[0]
            theme = params.get('theme', ['light'])[0]
            if user:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, theme) VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET theme = excluded.theme", (user, theme))
                conn.commit()
                conn.close()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            return
        if self.path == '/api/import_recipes':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                recipes_to_import = json.loads(post_data.decode('utf-8'))
                if not isinstance(recipes_to_import, list):
                    raise ValueError("Данные должны быть массивом JSON.")
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")
                imported_count = 0
                for item in recipes_to_import:
                    title = item.get('title')
                    cooking_time = item.get('cooking_time_min', 0)
                    instructions = item.get('instructions', '')
                    ingredients = item.get('ingredients', [])
                    if not title:
                        continue
                    cursor.execute("INSERT OR IGNORE INTO recipes (title, cooking_time_min, instructions) VALUES (?, ?, ?)", (title, cooking_time, instructions))
                    if cursor.rowcount > 0:
                        recipe_id = cursor.lastrowid
                        imported_count += 1
                        for ing_name in ingredients:
                            cursor.execute("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", (ing_name,))
                            cursor.execute("SELECT id FROM ingredients WHERE name = ?", (ing_name,))
                            row = cursor.fetchone()
                            if row:
                                ing_id = row[0]
                                cursor.execute("INSERT OR IGNORE INTO recipe_ingredients (recipe_id, ingredient_id) VALUES (?, ?)", (recipe_id, ing_id))
                conn.commit()
                conn.close()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'imported_recipes': imported_count}).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
                return

    def serve_html(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, f"Файл {filename} не найден")

def run_server():
    init_db()
    server_address = ('', 5000)
    httpd = HTTPServer(server_address, CustomHandler)
    print("Сервер запущен на http://localhost:5000")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("\nСервер остановлен.")

if __name__ == '__main__':
    run_server()

