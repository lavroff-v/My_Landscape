from flask import Blueprint, render_template, request, redirect, url_for, \
    flash, session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash  # Импортируем проверку пароля
#from db_scripts import add_user, get_user_by_email

auth = Blueprint('auth', __name__)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        # Хешируем
        hashed_pw = generate_password_hash(password)

        # Пытаемся добавить
        result = add_user(full_name, email, phone, hashed_pw)

        if result == "exists":
            flash("Пользователь с таким Email уже зарегистрирован", "danger")
            return redirect(url_for('auth.register'))  # Возвращаем на форму

        elif result:
            flash("Регистрация завершена! Пожалуйста, войдите в свой аккаунт.", "success")
            return redirect(url_for('auth.login'))

        else:
            flash("Произошла ошибка базы данных. Попробуйте позже.", "warning")
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Ищем пользователя в базе
        user = get_user_by_email(email)

        # 2. Если пользователь найден (user не None)
        if user:
            # Распаковываем кортеж (id, name, hash, role)
            user_id, full_name, password_hash, role = user

            # 3. Проверяем пароль
            if check_password_hash(password_hash, password):
                # Если пароль верный — записываем данные в сессию
                session['user_id'] = user_id
                session['user_name'] = full_name
                session['role'] = role

                flash(f"Здравствуйте {full_name}! Рады видеть вас снова! ",
                      "success")
                return redirect(url_for('client.index'))
            else:
                # Пароль неверный
                flash("Неверный пароль. Попробуйте еще раз.", "danger")
        else:
            # Email не найден
            flash("Пользователь с таким Email не найден.", "danger")

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    # Полностью очищаем сессию (удаляем user_id, user_name и role)
    session.clear()

    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for('client.index'))