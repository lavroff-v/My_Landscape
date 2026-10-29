from flask import Flask
from db_config import Config
from client.routes import client
from auth.routes import auth  # Импортируем Blueprint
from admin.routes import admin

app = Flask(__name__)
app.config.from_object(Config)

# Теперь настройки доступны через app.config['DB_CONFIG']
# Регистрируем Blueprint
app.register_blueprint(client)
app.register_blueprint(auth, url_prefix='/auth') # Все ссылки auth будут начинаться с /auth/
app.register_blueprint(admin, url_prefix='/admin')

if __name__ == '__main__':
    app.run(debug=True)