import sqlite3
from datetime import date

DB_PATH = "insurancebot.db"

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER,
            type TEXT,
            text TEXT,
            file_paths TEXT,
            link TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            registration_date DATE,
            current_lesson INTEGER DEFAULT 1
        )
    """)
    con.commit()
    con.close()

def add_material(day_number, type, text, file_paths, link):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO materials (day_number, type, text, file_paths, link)
        VALUES (?, ?, ?, ?, ?)
    """, (day_number, type, text, file_paths, link))
    con.commit()
    con.close()

def get_material_by_day(day_number):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM materials WHERE day_number=?", (day_number,))
    lesson = cur.fetchone()
    con.close()
    return dict(lesson) if lesson else None

def add_user(telegram_id, name):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (telegram_id, name, registration_date)
        VALUES (?, ?, ?)
    """, (telegram_id, name, date.today()))
    con.commit()
    con.close()

def get_user(telegram_id):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = cur.fetchone()
    con.close()
    return dict(user) if user else None

def update_user_lesson(telegram_id, lesson):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE users SET current_lesson=? WHERE telegram_id=?", (lesson, telegram_id))
    con.commit()
    con.close()

def get_all_users():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    con.close()
    return [dict(u) for u in users]

def get_lessons_count():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM materials")
    count = cur.fetchone()[0]
    con.close()
    return count

if __name__ == '__main__':
    db_init()
    # Добавьте материалы один раз, если ещё не добавляли
    add_material(1, 'text', 'Урок 1. Введение в страхование: что это такое и зачем нужно?', None, None)
    add_material(2, 'text', 'Урок 2. Основные виды страхования. Подробнее по ссылке.', None, 'https://example.com/insurance')
    add_material(3, 'text', 'Урок 3. Основные виды страхования. Подробнее по ссылке.', None,'https://ru.wikisource.org/wiki/%D0%97%D0%B0%D0%BA%D0%BE%D0%BD_%D0%A0%D0%B5%D1%81%D0%BF%D1%83%D0%B1%D0%BB%D0%B8%D0%BA%D0%B8_%D0%A2%D0%B0%D0%B4%D0%B6%D0%B8%D0%BA%D0%B8%D1%81%D1%82%D0%B0%D0%BD_%22%D0%9E_%D1%81%D1%82%D1%80%D0%B0%D1%85%D0%BE%D0%B2%D0%BE%D0%B9_%D0%B4%D0%B5%D1%8F%D1%82%D0%B5%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D0%B8%22')
    print("Материалы добавлены!")
