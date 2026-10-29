from flask import (Blueprint, render_template, session, redirect, url_for,
                   flash, request)
import os
from werkzeug.utils import secure_filename
from flask import current_app # чтобы достать путь к папке загрузок
#from db_scripts import add_product

admin = Blueprint('admin', __name__)

@admin.before_request
def restrict_admin_access():
    # Проверяем роль перед выполнением любого запроса в админке
    if session.get('role') != 'admin':
        flash("Доступ запрещен! Требуются права администратора.", "danger")
        return redirect(url_for('auth.login'))


@admin.route('/dashboard')
def dashboard():
    # Теперь здесь только чистая логика страницы
    return render_template('admin/dashboard.html')


@admin.route('/products')
def products_list():
    # Пока у нас нет функции получения всех товаров из БД,
    # передаем пустой список, чтобы страница просто открылась.
    products = []
    return render_template('admin/products.html', products=products)


@admin.route('/products/add', methods=['GET', 'POST'])
def add_product_route():
    if request.method == 'POST':
        # Здесь мы будем забирать данные из полей формы
        name = request.form.get('name')
        brand = request.form.get('brand')
        category = request.form.get('category')
        description = request.form.get('description')
        price = request.form.get('price')
        quantity = request.form.get('quantity')
        unit = request.form.get('unit')

        # Работа с фото
        file = request.files.get('image')
        if file and file.filename != '':
            # Делаем имя файла безопасным (убираем лишние точки, пробелы и т.д.)
            filename = secure_filename(file.filename)
            # Формируем путь для сохранения: static/uploads/имя_файла
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                     filename)
            # Сохраняем файл на диск
            file.save(file_path)
            # В базу записываем только имя файла
            image_url = filename
        else:
            # Если фото не выбрали — ставим заглушку
            image_url = "default.jpg"

        # Вызываем нашу функцию из db_scripts
        result = add_product(name, brand, category, description, price,
                             image_url, quantity, unit)

        if result:
            flash(f"Товар '{name}' успешно добавлен!", "success")
            return redirect(url_for('admin.products_list'))
        else:
            flash("Ошибка при добавлении товара в базу.", "danger")

    return render_template('admin/add_product.html')