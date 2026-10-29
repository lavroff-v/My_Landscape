from flask import Blueprint, render_template
from repositories.products import get_all_products


# Создаем Blueprint для клиента
client = Blueprint('client', __name__)

# Главная страница (Лендинг: о магазине, акции, контакты)
@client.route('/')
def index():
    return render_template('client/index.html')

@client.route('/catalog')
def catalog():
    products = get_all_products()
#    return 'Страница пока в разработке'
    return render_template('client/catalog.html', products=products)

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