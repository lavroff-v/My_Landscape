from flask import Blueprint, render_template, request
from repositories.products import get_all_products


# Создаем Blueprint для клиента
client = Blueprint('client', __name__)

# Главная страница (Лендинг: о магазине, акции, контакты)
@client.route('/')
def index():
    return render_template('client/index.html')

#   *** @client.route('/catalog') БЕЗ КАТЕГОРИЙ ***
# @client.route('/catalog')
# def catalog():
#     products = get_all_products()
# #    return 'Страница пока в разработке'
#     return render_template('client/catalog.html', products=products)

#   *** @client.route('/catalog') С КАТЕГОРИЯМИ ***
@client.route('/catalog')
def catalog():
    # Получаем параметр 'cat' из адресной строки (если его нет, будет None)
    category = request.args.get('cat')

    # Передаем категорию в функцию получения товаров
    products = get_all_products(category_filter=category)

    # Передаем текущую категорию в шаблон, чтобы можно было подсветить активную кнопку
    return render_template('client/catalog.html', products=products,
                           current_category=category)

# @client.route('/gallery')
# def gallery():
#     return 'Страница "Галерея" пока в разработке'
# #     return render_template('client/rasteniya.html')
#
#
# @client.route('/contacts')
# def contacts():
#     return 'Страница ** "Контакты" ** пока в разработке'
# #     return render_template('client/materials.html')