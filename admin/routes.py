from flask import (Blueprint, render_template, session, redirect, url_for,
                   flash, request)
from repositories.products import (get_all_products, add_product_to_db)
import os
from werkzeug.utils import secure_filename
from flask import current_app # чтобы достать путь к папке загрузок


admin = Blueprint('admin', __name__)


@admin.before_request
def check_admin_access():
    """Срабатывает автоматически перед ЛЮБЫМ маршрутом внутри Blueprint admin."""
    if session.get('role') != 'admin':
        flash("Доступ запрещен. Требуются права администратора. Ха-ха",
              "danger")
        return redirect(url_for('auth.login'))

# Временный пароль для входа (позже заменим на проверку из БД)
#ADMIN_PASSWORD = "admin123"


# @admin.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         password = request.form.get('password')
#         if password == ADMIN_PASSWORD:
#             session['is_admin'] = True
#             flash('Вы успешно вошли в админку!', 'success')
#             return redirect(url_for('admin.dashboard'))
#         else:
#             flash('Неверный пароль', 'danger')
#     return render_template('admin/login.html')


@admin.route('/')
def dashboard():
    # # Проверяем, что пользователь вошел и его роль — 'admin'
    # if session.get('role') != 'admin':
    #     flash("Доступ запрещен. Требуются права администратора.", "danger")
    #     return redirect(url_for('auth.login'))

    return render_template('admin/dashboard.html')


@admin.route('/products')
def products_list():
    # Проверяем, авторизован ли пользователь
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    all_products = get_all_products()
    # Пока просто рендерим шаблон (он у вас уже есть в папке admin)
    return render_template('admin/products.html', products=all_products)


@admin.route('/add_product', methods=['GET', 'POST'])
def add_product_route():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))

    if request.method == 'POST':
        # 1. Получаем данные из формы
        name = request.form.get('name')
        brand = request.form.get('brand')
        category = request.form.get('category')
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        unit = request.form.get('unit')

        # 2. Обрабатываем картинку
        image = request.files.get('image')
        image_url = None

        if image and image.filename != '':
            filename = secure_filename(image.filename)
            filepath = os.path.join('static', 'uploads', filename)
            image.save(filepath)
            image_url = filename

        # 3. Вызываем функцию из репозитория!
        add_product_to_db(
            name=name, brand=brand, category=category, description=description,
            price=price, quantity=quantity, unit=unit, image_url=image_url
        )

        flash('Товар успешно добавлен!', 'success')
        return redirect(url_for('admin.products_list'))

    return render_template('admin/add_product.html')


#     *****  СТАРАЯ АДМИНКА  *****
# @admin.before_request
# def restrict_admin_access():
#     # Проверяем роль перед выполнением любого запроса в админке
#     if session.get('role') != 'admin':
#         flash("Доступ запрещен! Требуются права администратора.", "danger")
#         return redirect(url_for('auth.login'))
#
#
# @admin.route('/dashboard')
# def dashboard():
#     # Теперь здесь только чистая логика страницы
#     return render_template('admin/dashboard.html')

# @admin.route('/products')
# def products_list():
#     # Пока у нас нет функции получения всех товаров из БД,
#     # передаем пустой список, чтобы страница просто открылась.
#     products = []
#     return render_template('admin/products.html', products=products)

# @admin.route('/products/add', methods=['GET', 'POST'])
# def add_product_route():
#     if request.method == 'POST':
#         # Здесь мы будем забирать данные из полей формы
#         name = request.form.get('name')
#         brand = request.form.get('brand')
#         category = request.form.get('category')
#         description = request.form.get('description')
#         price = request.form.get('price')
#         quantity = request.form.get('quantity')
#         unit = request.form.get('unit')
#
#         # Работа с фото
#         file = request.files.get('image')
#         if file and file.filename != '':
#             # Делаем имя файла безопасным (убираем лишние точки, пробелы и т.д.)
#             filename = secure_filename(file.filename)
#             # Формируем путь для сохранения: static/uploads/имя_файла
#             file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
#                                      filename)
#             # Сохраняем файл на диск
#             file.save(file_path)
#             # В базу записываем только имя файла
#             image_url = filename
#         else:
#             # Если фото не выбрали — ставим заглушку
#             image_url = "default.jpg"
#
#         # Вызываем нашу функцию из db_scripts
#         result = add_product(name, brand, category, description, price,
#                              image_url, quantity, unit)
#
#         if result:
#             flash(f"Товар '{name}' успешно добавлен!", "success")
#             return redirect(url_for('admin.products_list'))
#         else:
#             flash("Ошибка при добавлении товара в базу.", "danger")
#
#     return render_template('admin/add_product.html')


# @admin.route('/logout')
# def logout():
#     session.pop('is_admin', None)
#     flash('Вы вышли из админки', 'info')
#     return redirect(url_for('client.index'))