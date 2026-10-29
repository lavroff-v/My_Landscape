import psycopg2

try:
    conn = psycopg2.connect(database="my_landscape", user="postgres",
                            password="529529", host="localhost")
    cursor = conn.cursor()

    # TRUNCATE полностью очищает таблицу.
    # RESTART IDENTITY сбросит счетчики ID (автоинкремент) в ноль.
    truncate_query = "TRUNCATE TABLE products RESTART IDENTITY CASCADE;"

    cursor.execute(truncate_query)
    conn.commit()

    print("Таблица полностью очищена, счетчики ID сброшены.")

except Exception as error:
    print(f"Ошибка: {error}")
finally:
    if conn:
        cursor.close()
        conn.close()