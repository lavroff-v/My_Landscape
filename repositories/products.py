import psycopg2
from psycopg2 import extras
from db_config import Config

def get_db_connection():
    """Возвращает новое соединение с БД PostgreSQL."""
    return psycopg2.connect(**Config.DB_CONFIG)


def get_all_products(category_filter=None):
    """Возвращает товары. Если указана категория — только её, иначе — все.
    Каждая строка — словарь (RealDictCursor): product['name'], product['price'] и т.д.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                if category_filter and category_filter != "Все":
                    query = """
                        SELECT id, name, brand, category, description,
                               price, image_url, quantity, unit, is_available
                        FROM products
                        WHERE category = %s
                        ORDER BY id DESC;
                    """
                    cursor.execute(query, (category_filter,))
                else:
                    query = """
                        SELECT id, name, brand, category, description,
                               price, image_url, quantity, unit, is_available
                        FROM products
                        ORDER BY id DESC;
                    """
                    cursor.execute(query)
                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка при получении товаров: {e}")
        return []

def add_product_to_db(name, brand, category, description, price, quantity, unit, image_url=None):
    """Добавляет новый товар в базу данных."""
    query = """
        INSERT INTO products (name, brand, category, description, price, quantity, unit, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (name, brand, category, description, price, quantity, unit, image_url))
                new_id = cursor.fetchone()[0]
                conn.commit() # Фиксируем изменения в БД
                return new_id
    except Exception as e:
        print(f"Ошибка при добавлении товара: {e}")
        return None