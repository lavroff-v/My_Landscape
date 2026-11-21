from flask import Blueprint, render_template, request, session, redirect, url_for
from repositories.products import get_all_products


# Создаем Blueprint для клиента
client = Blueprint('client', __name__)

# ** begin **  ** begin **  ** begin ** test-session

@client.route('/test-session', methods=['GET', 'POST'])
def test_session():
    # Если пользователь отправил форму (нажал кнопку)
    if request.method == 'POST':
        # Берем имя из поля формы и записываем в сессию
        session['user_id'] = 1  # Любое число для проверки условия if
        session['user_name'] = request.form.get('username')
        return redirect(url_for('client.index'))

    # Достаем имя из сессии (если его там еще нет, вернется None)
    name = session.get('guest_name')
    return render_template('client/test_session.html', name=name)

# **  end  **  **  end  **  **  end  **
# Главная страница (Лендинг: о магазине, акции, контакты)
@client.route('/')
def index():
    # Достаем имя из сессии на главной странице
    name = session.get('guest_name')
    # Передаем его в шаблон index.html
    return render_template('client/index.html', name=name)

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

@client.route('/gallery')
def gallery():
#    return 'Страница "Галерея" пока в разработке'
    return render_template('client/gallery.html')


@client.route('/contacts')
def contacts():
#    return 'Страница ** "Контакты" ** пока в разработке'
    return render_template('client/contacts.html')


@client.route('/graph')
def graph():
#    return 'Страница ** "Контакты" ** пока в разработке'
    return render_template('client/graph.html')