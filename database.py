# database.py
import sqlite3
import os
from config import DB_PATH, IMAGE_DIR
"""Инициализация базы данных"""
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Создаем таблицы в базе данных."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Очищаем и заполняем таблицу новостей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        image_path TEXT,
        date TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    # Таблица документов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        file_path TEXT NOT NULL
    )
    ''')

    # Таблица новостей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        date TEXT DEFAULT (datetime('now', 'localtime'))
    )
    ''')

    # Таблица контактов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT
    )
    ''')

    conn.commit()
    conn.close()

def seed_db():
    """Заполняем базу тестовыми данными."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Очищаем таблицы перед заполнением (для тестов)
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM news")
    cursor.execute("DELETE FROM contacts")

    # Добавляем документы
    cursor.executemany(
        "INSERT INTO documents (name, type, file_path) VALUES (?, ?, ?)",
        [
            ("Заявление на отпуск", "application", "docs/application_1.docx"),
            ("Шаблон договора", "template", "docs/template_1.docx")
        ]
    )

    # Добавляем новости
    cursor.executemany(
        "INSERT INTO news (title, content, image_path) VALUES (?, ?, ?)",
        [
            ("Новая модель BELAZ", "Представлена модель 75710.", "news_images/belaz_new.jpg"),
            ("Выставка в Минске", "Приглашаем 15-20 октября.", "news_images/expo.jpg")
        ]
    )

    # Добавляем контакты
    cursor.executemany(
        "INSERT INTO contacts (department, phone, email) VALUES (?, ?, ?)",
        [
            ("Отдел кадров", "+375 (17) 123-45-67", "hr@belaz.by"),
            ("Техподдержка", "+375 (17) 765-43-21", "support@belaz.by")
        ]
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()  # Создаем таблицы
    seed_db()  # Заполняем данными
    print("✅ База данных готова!")