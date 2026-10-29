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


def register_user(name, email, password):
    """
    Регистрирует нового пользователя.
    Всегда получает роль 'client' по умолчанию (защита).
    """
    # Хешируем пароль (обязательно!)
    hashed_pw = generate_password_hash(password)

    # Поле role не указываем в INSERT, оно само станет 'client' из DEFAULT в БД
    query = """
    INSERT INTO users (full_name, email, password_hash) 
    VALUES (%s, %s, %s) 
    RETURNING id;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (name, email, hashed_pw))
                result = cursor.fetchone()
                # Возвращаем только само число ID, а не кортеж (ID,)
                return result[0] if result else None
    except Exception as e:
        print(f"Ошибка регистрации пользователя {email}: {e}")
        return None


def add_product_to_db(name, brand, description, price, quantity, image_url,
                      unit, category):
    """Добавляет товар или пересчитывает среднюю цену и остаток (поддерживает дроби)."""
    # Теперь используем float для поддержки веса (например 0.500 кг)
    price_val = float(price)
    quantity_val = float(quantity)

    query = """
    INSERT INTO products (name, brand, description, price, quantity, 
    image_url, unit, category)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    -- ТЕПЕРЬ КОНФЛИКТ СМОТРИМ ПО ДВУМ ПОЛЯМ СРАЗУ
    ON CONFLICT (name, brand)

    DO UPDATE SET 
        price = ((products.price * products.quantity) + (EXCLUDED.price * EXCLUDED.quantity)) 
                / NULLIF(products.quantity + EXCLUDED.quantity, 0),
        quantity = products.quantity + EXCLUDED.quantity,
        unit = EXCLUDED.unit,
        description = EXCLUDED.description,
        image_url = EXCLUDED.image_url,
        category = EXCLUDED.category;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    name, brand, description, price_val, quantity_val,
                    image_url, unit, category))
                return True
    except Exception as e:
        print(f"Ошибка при сохранении: {e}")
        return False


def get_all_products(category_filter=None):
    """Возвращает товары. Если указана категория — только её, иначе — все."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            # RealDictCursor превращает строку БД в удобный словарь {'name': 'Яблоки', ...}
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:

                if category_filter and category_filter != "Все":
                    # Фильтруем: выбираем только те товары, где категория совпадает
                    query = "SELECT * FROM products WHERE category = %s ORDER BY id DESC;"
                    cursor.execute(query, (category_filter,))
                else:
                    # Забираем всё (старый вариант)
                    query = "SELECT * FROM products ORDER BY id DESC;"
                    cursor.execute(query)

                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка при получении товаров: {e}")
        return []


def delete_product_from_db(item_id):
    """Удаляет товар из базы данных по его ID."""
    query = "DELETE FROM products WHERE id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (item_id,))
                # Сообщение в консоль для контроля
                print(f"Товар с ID {item_id} успешно удален из БД.")
                return True
    except Exception as e:
        print(f"Ошибка при удалении товара: {e}")
        return False


def get_product_image(item_id):
    """
    Заглядывает в базу данных и возвращает путь к картинке товара.
    Нужна для 'чистого' удаления файла с диска.
    """
    query = "SELECT image_url FROM products WHERE id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (item_id,))
                result = cursor.fetchone()
                # result[0] — это и есть наш текст 'uploads/имя.jpg'
                return result[0] if result and result[0] else None
    except Exception as e:
        print(f"Ошибка при поиске пути к картинке: {e}")
        return None


def get_product_by_id(item_id):
    """Достает данные одного товара по его ID."""
    query = "SELECT * FROM products WHERE id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (item_id,))
                return cursor.fetchone()
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None


def update_product_in_db(item_id, name, brand, description, price, quantity,
                         image_url, unit, category):
    """Просто ЗАМЕНЯЕТ старые данные на новые по ID (без пересчета цены)."""
    query = """
    UPDATE products SET 
        name=%s, brand=%s, description=%s, price=%s, quantity=%s, 
        image_url=%s, unit=%s, category=%s
    WHERE id = %s;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (name, brand, description,
                                       float(price), float(quantity),
                                       image_url, unit, category, item_id))
                return True
    except Exception as e:
        print(f"Ошибка обновления: {e}")
        return False


def get_unique_categories():
    """Возвращает список всех уникальных категорий, которые есть в базе."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # SELECT DISTINCT выберет только уникальные значения
                cursor.execute(
                    "SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category;")
                # fetchall вернет список кортежей [('Электроника',), ('Одежда',)],
                # поэтому превращаем его в плоский список строк
                categories = [row[0] for row in cursor.fetchall()]
                return categories
    except Exception as e:
        print(f"Ошибка при получении категорий: {e}")
        return []


# ======================================================================
#   Функции users
# ======================================================================
def get_user_by_email(email):
    """Ищет пользователя в базе по Email. Возвращает словарь с данными."""
    query = "SELECT id, full_name, email, password_hash, role FROM users WHERE email = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            # Используем RealDictCursor, чтобы сразу получить удобный словарь
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (email,))
                return cursor.fetchone()
    except Exception as e:
        print(f"Ошибка при поиске пользователя: {e}")
        return None


def verify_user(email, password):
    """
    Проверяет: существует ли пользователь и верен ли пароль.
    Возвращает данные пользователя, если всё ок, иначе — None.
    """
    user = get_user_by_email(email)

    if user:
        # Сравниваем введенный пароль с хешем из базы
        if check_password_hash(user['password_hash'], password):
            # Пароль верный! Убираем хеш из словаря для безопасности и возвращаем юзера
            del user['password_hash']
            return user

    return None  # Если почта не найдена или пароль не совпал


# ======================================================================
#   Функции корзины
# ======================================================================

def add_to_cart_db(user_id, product_id, quantity=1, mode='add'):
    """Добавляет товар, проверяя остатки на складе."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                # 1. Узнаем, сколько на складе и сколько УЖЕ в корзине у юзера
                query_check = """
                SELECT 
                    p.quantity as stock, 
                    COALESCE(c.quantity, 0) as in_cart 
                FROM products p
                LEFT JOIN cart c ON p.id = c.product_id AND c.user_id = %s
                WHERE p.id = %s;
                """
                cursor.execute(query_check, (user_id, product_id))
                res = cursor.fetchone()

                if not res:
                    return False, "Товар не найден"

                stock = float(res['stock'])
                already_in_cart = float(res['in_cart'])
                new_total = float(quantity)
                if mode == 'add':
                    new_total += already_in_cart

                # 2. Главная ПРОВЕРКА ОСТАТКОВ
                if new_total > stock:
                    # Вот тут рождаются False и Message
                    return False, f"Недостаточно товара. На складе: {stock}, в корзине уже: {already_in_cart}"

                # 3. Если всё ок — делаем запись
                if mode == 'set':
                    # Режим ПЕРЕЗАПИСИ (для редактирования)
                    query_upsert = """
                        INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, product_id) DO UPDATE SET quantity = EXCLUDED.quantity;
                        """
                else:
                    # Режим ПРИБАВЛЕНИЯ (из каталога)
                    query_upsert = """
                        INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, product_id) DO UPDATE SET quantity = cart.quantity + EXCLUDED.quantity;
                        """
                cursor.execute(query_upsert,
                               (user_id, product_id, float(quantity)))
                return True, "Корзина обновлена"

    except Exception as e:
        print(f"Ошибка базы: {e}")
        return False, "Системная ошибка"


def get_cart_count(user_id):
    """Считает общее количество товаров в корзине пользователя."""
    if not user_id:
        return 0

    query = "SELECT SUM(quantity) FROM cart WHERE user_id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                # Если в корзине пусто, SUM вернет None, поэтому превращаем в 0
                count = result[0] if result[0] is not None else 0
                # Возвращаем целое число (для штук) или float (для кг)
                return int(count) if count == int(count) else float(count)
    except Exception as e:
        print(f"Ошибка при подсчете корзины: {e}")
        return 0


def get_user_cart(user_id):
    """Выводит список товаров в корзине с их названиями, ценами и фото."""
    if not user_id:
        return []

    query = """
    SELECT 
        c.id as cart_id, 
        p.id as product_id, 
        p.name, p.brand, p.price, p.image_url, p.unit,
        p.quantity as stock,
        c.quantity, 
        (p.price * c.quantity) as row_total
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = %s
    ORDER BY c.added_at DESC;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (user_id,))
                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка при получении корзины: {e}")
        return []


def remove_cart_item_db(cart_id):
    """Удаляет одну позицию из корзины по её ID."""
    query = "DELETE FROM cart WHERE id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (cart_id,))
                return True
    except Exception as e:
        print(f"Ошибка удаления: {e}")
        return False


def clear_cart_db(user_id):
    query = "DELETE FROM cart WHERE user_id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id,))
                return True
    except:
        return False


# ======================================================================
#   Кнопка "Оформить заказ"
# ======================================================================

def process_checkout(user_id):
    """Списывает товары со склада, сохраняет в историю, очищает корзину и шлет ПОДРОБНОЕ уведомление."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                # 1. Получаем корзину
                query_cart = "SELECT c.product_id, c.quantity, p.price, p.name, p.unit, p.quantity as stock FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = %s;"
                cursor.execute(query_cart, (user_id,))
                items = cursor.fetchall()

                if not items:
                    return False, "Корзина пуста"

                order_num = f"ORD-{datetime.now().strftime('%Y%m%d%H%M')}-{user_id}"
                grand_total = 0
                # --- НОВОЕ: Переменная для списка товаров ---
                order_content = ""

                for item in items:
                    qty = float(item['quantity'])
                    stock = float(item['stock'])

                    if qty > stock:
                        conn.rollback()
                        return False, f"Товара '{item['name']}' недостаточно!"

                    cursor.execute(
                        "UPDATE products SET quantity = quantity - %s WHERE id = %s",
                        (qty, item['product_id']))

                    total = qty * float(item['price'])
                    grand_total += total

                    # --- ЗАПОЛНЯЕМ СПИСОК ДЛЯ TELEGRAM ---
                    order_content += f"• {item['name']} - {qty} {item['unit']}\n"

                    insert_order = "INSERT INTO orders (order_number, user_id, product_id, quantity, price_at_purchase, total_price) VALUES (%s, %s, %s, %s, %s, %s);"
                    cursor.execute(insert_order, (
                        order_num, user_id, item['product_id'], qty,
                        float(item['price']), total))

                cursor.execute("DELETE FROM cart WHERE user_id = %s",
                               (user_id,))
                conn.commit()

                # --- ФОРМИРУЕМ ПОДРОБНОЕ СООБЩЕНИЕ ---
                msg = f"🛍 <b>Новый заказ: {order_num}</b>\n\n"
                msg += f"<b>Состав:</b>\n{order_content}\n"  # Тот самый список товаров
                msg += f"💰 <b>ИТОГО: {grand_total:.2f} руб.</b>"

                send_telegram_notification(msg)

                return True, f"Заказ {order_num} успешно оформлен!"
    except Exception as e:
        print(f"Ошибка заказа: {e}")
        return False, "Ошибка при сохранении заказа."


# ======================================================================
#   "Личный кабинет"
# ======================================================================

def get_user_orders_db(user_id):
    """Вытаскивает из базы историю покупок конкретного пользователя."""
    query = """
    SELECT 
        o.order_date, 
        o.order_number, 
        p.brand, 
        p.name as product_name, 
        o.quantity, 
        o.price_at_purchase, 
        o.total_price 
    FROM orders o
    JOIN products p ON o.product_id = p.id
    WHERE o.user_id = %s
    ORDER BY o.order_date DESC;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (user_id,))
                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка получения истории заказов: {e}")
        return []


def get_user_data_db(user_id):
    """Достает полную информацию о пользователе из базы."""
    query = "SELECT full_name, email, phone, address, role FROM users WHERE id = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (user_id,))
                return cursor.fetchone()
    except Exception as e:
        print(f"Ошибка получения данных юзера: {e}")
        return None


def update_user_profile_db(user_id, phone, address):
    """Обновляет контактные данные пользователя в базе."""
    query = """
    UPDATE users 
    SET phone = %s, address = %s 
    WHERE id = %s;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (phone, address, user_id))
                return True
    except Exception as e:
        print(f"Ошибка обновления профиля: {e}")
        return False


# ======================================================================
#   " Админ. Управление заказами. Панель заказов."
# ======================================================================

def get_all_orders_admin(search_query=None, status_filter=None):
    """Возвращает список заказов с возможностью поиска и фильтрации."""
    # Базовая часть запроса
    query = """
    SELECT 
        o.order_number, o.user_id, u.full_name, u.email, 
        SUM(o.total_price) as total_sum, 
        MAX(o.order_date) as date, 
        MAX(o.status) as status
    FROM orders o
    JOIN users u ON o.user_id = u.id
    WHERE 1=1
    """
    params = []

    # 1. Если передан поиск (по номеру заказа или имени клиента)
    if search_query:
        query += " AND (o.order_number ILIKE %s OR u.full_name ILIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    # 2. Если выбран конкретный статус (кроме "Все")
    if status_filter and status_filter != 'Все':
        query += " AND o.status = %s"
        params.append(status_filter)

    # Завершаем группировкой и сортировкой
    query += " GROUP BY o.order_number, o.user_id, u.full_name, u.email ORDER BY date DESC;"

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка поиска заказов: {e}")
        return []


def update_order_status_db(order_number, new_status):
    """Обновляет статус для всех строк конкретного заказа (по его номеру)."""
    query = "UPDATE orders SET status = %s WHERE order_number = %s;"
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (new_status, order_number))
                return True
    except Exception as e:
        print(f"Ошибка при обновлении статуса заказа {order_number}: {e}")
        return False


# ======================================================================
#   " Для чека. Список товаров по номеру заказа. "
# ======================================================================

def get_order_details_db(order_number):
    """Возвращает список всех товаров в конкретном заказе по его номеру."""
    query = """
    SELECT 
        o.product_id, 
        p.name as product_name, 
        p.unit,
        o.quantity, 
        o.price_at_purchase as price, 
        o.total_price as row_total,
        o.order_date,
        o.status,
        u.full_name as customer_name,
        u.email as customer_email,
        u.phone as customer_phone,
        u.address as customer_address
    FROM orders o
    JOIN products p ON o.product_id = p.id
    JOIN users u ON o.user_id = u.id
    WHERE o.order_number = %s;
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, (order_number,))
                return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка при получении состава заказа {order_number}: {e}")
        return []


# ======================================================================
#   " Карточка покупателя. "
# ======================================================================

def get_customer_full_info(user_id):
    """Возвращает профиль клиента и всю историю его заказов."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                # 1. Данные профиля
                cursor.execute(
                    "SELECT id, full_name, email, phone, address, created_at FROM users WHERE id = %s",
                    (user_id,))
                profile = cursor.fetchone()

                if not profile:
                    return None, [], 0

                # 2. История заказов (группируем по номеру, чтобы не было дублей товаров)
                query_orders = """
                SELECT order_number, SUM(total_price) as order_total, 
                       MAX(order_date) as date, MAX(status) as status
                FROM orders
                WHERE user_id = %s
                GROUP BY order_number
                ORDER BY date DESC;
                """
                cursor.execute(query_orders, (user_id,))
                orders = cursor.fetchall()

                # 3. Общая сумма трат за всё время
                total_spent = sum(
                    float(order['order_total']) for order in orders)

                return profile, orders, total_spent
    except Exception as e:
        print(f"Ошибка при получении данных клиента {user_id}: {e}")
        return None, [], 0


if __name__ == "__main__":
    #    create_database("my_shop_1", "postgres", "529529")
    print(create_table_products())
    print(create_table_users())
    print(create_table_cart())
    print(create_table_orders())