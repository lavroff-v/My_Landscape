import psycopg2
from psycopg2 import sql, extras
from db_config import Config
from werkzeug.security import generate_password_hash


# ======================================================================
#   Создание БД my_landscape
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


# ======================================================================
#   Создание таблицы пользователей.
# ======================================================================

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
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return "Таблица пользователей успешно создана/проверена."
    except Exception as e:
        return f"Ошибка при создании таблицы юзеров: {e}"


# ======================================================================
#   Создание таблицы товаров.
# ======================================================================

def create_table_products():
    """Создает таблицу товаров с учетом доступности, категорий и веса."""
    query = """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        brand VARCHAR(100) DEFAULT 'Без бренда',
        category VARCHAR(100) DEFAULT 'Разное',
        description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        image_url TEXT,
        quantity DECIMAL(10, 3) NOT NULL DEFAULT 0,
        unit VARCHAR(10) NOT NULL DEFAULT 'шт.',
        is_available BOOLEAN DEFAULT TRUE,  -- Тот самый переключатель доступности
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_name_brand UNIQUE (name, brand)
    );
    """
    try:
        # Используем ваш конфиг
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return "Таблица товаров (products) успешно создана или уже существует."
    except Exception as e:
        return f"Ошибка при создании таблицы товаров: {e}"


# ======================================================================
#   Добавляет нового пользователя в базу данных.
# ======================================================================

def add_user(full_name, email, phone, password_hash):
    """Добавляет нового пользователя в базу данных."""
    query = """
    INSERT INTO users (full_name, email, phone, password_hash)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    try:
        # Используем ваш DB_CONFIG из db_config.py
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (full_name, email, phone, password_hash))
                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id # Возвращаем ID нового юзера
    except psycopg2.errors.UniqueViolation:
        return "exists" # Специальный флаг, если email уже занят
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return None


# ======================================================================
#   Функция поиска пользователя в базе данных по Email.
# ======================================================================

def get_user_by_email(email):
    """Ищет пользователя в базе по Email."""
    query = "SELECT id, full_name, password_hash, role FROM users WHERE email = %s;"
    try:
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (email,))
                user = cursor.fetchone()
                return user  # Вернет кортеж (id, name, hash, role) или None, если не найден
    except Exception as e:
        print(f"Ошибка при поиске пользователя: {e}")
        return None

# # ======================================================================
# #   Добавление нового товара в базу данных
# # ======================================================================
#
# def add_product(name, brand, category, description, price, image_url, quantity, unit):
#     """Добавляет новый товар в таблицу products."""
#     query = """
#     INSERT INTO products (name, brand, category, description, price, image_url, quantity, unit)
#     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#     RETURNING id;
#     """
#     try:
#         with psycopg2.connect(**Config.DB_CONFIG) as conn:
#             with conn.cursor() as cursor:
#                 cursor.execute(query, (name, brand, category, description, price, image_url, quantity, unit))
#                 product_id = cursor.fetchone()[0]
#                 conn.commit()
#                 return product_id
#     except Exception as e:
#         print(f"Ошибка БД при добавлении товара: {e}")
#         return None

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def insert_test_products():
    """Добавляет тестовые товары (если их ещё нет)."""
    products = [
        # name, brand, category, description, price, image_url, quantity, unit
        ('Туя Западная "Smaragd"', 'Питомник Лесное', 'Растения',
         'Вечнозелёный хвойный кустарник, высота 1.5–2 м.',
         1200.00, None, 25.000, 'шт.'),
        ('Камень плитняк (Лемезит)', 'УралКамень', 'Материалы',
         'Натуральный камень для дорожек и альпийских горок.',
         450.00, None, 120.000, 'кв.м'),
        ('Рулонный газон "Премиум"', 'Газон-Юг', 'Растения',
         'Готовый рулонный газон, ширина 0.4 м, длина 2 м.',
         280.00, None, 300.000, 'рулон'),
        ('Проект альпийской горки', 'Студия Ландшафт', 'Дизайн',
         'Типовой проект с подбором растений и камня.',
         5000.00, None, 1.000, 'шт.'),
        ('Декоративная щепа (сосна)', 'ЭкоДекор', 'Материалы',
         'Мульча из сосновой коры, фракция 20–40 мм.',
         320.00, None, 80.000, 'мешок'),
    ]

    query = """
    INSERT INTO products (name, brand, category, description, price,
                          image_url, quantity, unit)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (name, brand) DO NOTHING;
    """

    try:
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                for p in products:
                    cursor.execute(query, p)
        return f"Тестовые товары добавлены (пропущены существующие)."
    except Exception as e:
        return f"Ошибка при добавлении тестовых товаров: {e}"

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


def create_admin():
    """Создает учетную запись главного администратора из настроек Config."""
    admin_email = Config.ADMIN_EMAIL
    admin_password = Config.ADMIN_PASSWORD
    admin_name = "Администратор"

    if not admin_email or not admin_password:
        print("ВНИМАНИЕ: ADMIN_EMAIL или ADMIN_PASSWORD не заданы в файле .env!")
        return

    hashed_pw = generate_password_hash(admin_password)

    query = """
    INSERT INTO users (full_name, email, password_hash, role)
    VALUES (%s, %s, %s, 'admin')
    ON CONFLICT (email) DO NOTHING;
    """
    try:
        with psycopg2.connect(**Config.DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (admin_name, admin_email, hashed_pw))
                conn.commit()
                print("Проверка/создание администратора успешно выполнены.")
    except Exception as e:
        print(f"Ошибка при создании администратора: {e}")



if __name__ == "__main__":


    # create_database("my_landscape", "postgres", "529529")
    # print(create_table_users())
    # print(create_table_products())
    # print(insert_test_products())
    print(create_admin())
