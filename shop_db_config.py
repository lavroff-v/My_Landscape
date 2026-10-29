import psycopg2
from psycopg2 import sql, extras
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import requests


# Параметры подключения
DB_CONFIG = {
    "host": "localhost",
    "database": "my_shop_1",
    "user": "postgres",
    "password": "529529",
    "port": "5432"
}


# ======================================================================
#   Телеграм бот
# ======================================================================

# Данные для уведомлений
TELEGRAM_TOKEN = "8618146856:AAGvz4z7Sipd-NUOSof_gbNvS2bF5lQ8YiM"
TELEGRAM_CHAT_ID = "984902293"

def send_telegram_notification(message):
    """Отправляет уведомление администратору в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")


# ======================================================================
#   Создание БД и таблиц
# ======================================================================

def create_database(db_name, user, password, host="127.0.0.1"):
    """Создает базу данных, если она еще не существует."""
    conn = psycopg2.connect(dbname="postgres", user=user, password=password,
                            host=host)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        print(f"База '{db_name}' создана.")
    except psycopg2.errors.DuplicateDatabase:
        print(f"База '{db_name}' уже существует.")
    finally:
        cur.close()
        conn.close()


def create_table_products():
    """Создает таблицу products и обновляет её до поддержки весового товара."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        brand VARCHAR(100),
        description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        image_url TEXT,
        quantity DECIMAL(10, 3) NOT NULL DEFAULT 0, -- Изменено на DECIMAL
        unit VARCHAR(10) NOT NULL DEFAULT 'шт.'     -- Новое поле
    );
    """

    # Команды для обновления существующей таблицы (на случай, если она уже создана как INTEGER)
    alter_queries = [
        # 1. Удаляем СТАРОЕ правило (только по имени), если оно еще осталось
        "ALTER TABLE products DROP CONSTRAINT IF EXISTS products_name_key CASCADE;",

        # 2. ПРОВЕРКА: удаляем старое НОВОЕ правило перед созданием, чтобы не было ошибки "уже существует"
        "ALTER TABLE products DROP CONSTRAINT IF EXISTS unique_name_brand CASCADE;",

        # 3. Теперь создаем его заново «на чистую»
        "ALTER TABLE products ADD CONSTRAINT unique_name_brand UNIQUE (name, brand);",

        "ALTER TABLE products ALTER COLUMN quantity TYPE DECIMAL(10, 3);",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit VARCHAR(10) DEFAULT 'шт.';",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(100);",
        # НОВАЯ КОЛОНКА: КАТЕГОРИЯ
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'Разное';"
    ]

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # 1. Сначала пробуем создать таблицу, если её нет
                cursor.execute(create_table_query)
                # 2. Затем прогоняем все обновления колонок
                for q in alter_queries:
                    cursor.execute(q)
                return ("Таблица товаров успешно актуализирована: поле "
                        "'brand' "
                        "добавлено.")
    except Exception as error:
        return f"Ошибка при обновлении таблицы: {error}"


def create_table_users():
    """Создает таблицу пользователей с поддержкой ролей."""
    query = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        full_name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        -- 'client' по умолчанию, 'staff' для персонала, 'admin' для тебя
        role VARCHAR(20) NOT NULL DEFAULT 'client', 
        phone VARCHAR(20),
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return "Таблица пользователей успешно создана/проверена."
    except Exception as e:
        return f"Ошибка при создании таблицы юзеров: {e}"


def create_table_cart():
    """Создает таблицу для хранения товаров в корзинах пользователей."""
    query = """
    CREATE TABLE IF NOT EXISTS cart (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity DECIMAL(10, 3) NOT NULL DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        -- Ограничение: один юзер может положить один товар в корзину только одной строкой
        UNIQUE(user_id, product_id)
    );
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return "Таблица корзины успешно создана/проверена."
    except Exception as e:
        return f"Ошибка при создании корзины: {e}"


def create_table_orders():
    """Создает таблицу истории заказов и обновляет её (добавляет статус)."""
    # 1. Запрос на создание (уже с колонкой status)
    query_create = """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_number VARCHAR(20) NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity DECIMAL(10, 3) NOT NULL,
        price_at_purchase DECIMAL(10, 2) NOT NULL,
        total_price DECIMAL(10, 2) NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'Новый'  -- Сразу добавляем сюда
    );
    """

    # 2. Запрос на обновление (на случай, если таблица уже была создана БЕЗ статуса)
    query_alter = "ALTER TABLE orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Новый';"

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query_create)  # Пытаемся создать
                cursor.execute(
                    query_alter)  # Пытаемся добавить колонку, если её нет
                return "Таблица заказов актуализирована (статус добавлен)!"
    except Exception as e:
        return f"Ошибка при работе с таблицей заказов: {e}"


if __name__ == "__main__":
#    create_database("my_shop_1", "postgres", "529529")
    print(create_table_products())
    print(create_table_users())
    print(create_table_cart())
    print(create_table_orders())