import sqlite3

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask_login import LoginManager
from flask_login import login_required
from flask_login import logout_user
from flask_login import login_user
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import create_engine
from sqlalchemy_find import SessionWithFind
from sqlalchemy_find import QueryWithFind
from sqlalchemy.orm import sessionmaker

from cloudipsp import Api
from cloudipsp import Checkout
from wtforms import StringField
from wtforms import PasswordField
from wtforms import BooleanField
from wtforms import SubmitField
from wtforms.validators import DataRequired

from data import db_session, users

# создаём приложение Flask:
app = Flask(__name__)
# подключаем базу данных:
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
# для корректной работы базы данных:
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ключ для Flask:
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
db = SQLAlchemy(app)
# подключаем менеджер логинов Flask для отслеживания действий пользователя (выйти или войти в аккаунт):
login_manager = LoginManager()
login_manager.init_app(app)
# инициализируем базу данных:
db_session.global_init("shop.db")

# создаём сессию базы данных:
engine = create_engine('sqlite:///shop.db')
Session = sessionmaker(bind=engine,
                       class_=SessionWithFind,
                       query_cls=QueryWithFind)

session = Session()


# создаём таблицу Item в базе данных
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    isActive = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return self.title


# создаём таблицу User в базе данных
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    address = db.Column(db.String, nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    role = db.Column(db.String, default='Пользователь', nullable=False)


# создаём форму Flask для входа в аккаунт
class LoginForm(FlaskForm):
    email = StringField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


# создаём форму Flask для регистрации
class RegisterForm(FlaskForm):
    login = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired()])
    name = StringField("Имя", validators=[DataRequired()])
    address = StringField("Адрес", validators=[DataRequired()])
    submit = SubmitField("Зарегистрироваться")


# создаём таблицу Favourites в базе данных
# эта таблица нужна для добавления товаров в корзину пользователя
class Favourites(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False)
    items = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)


# главная страница
@app.route('/')
def index():
    # выводятся все элементы из таблицы Items
    items = Item.query.all()
    return render_template('index.html', data=items, current_user=current_user)


# страница "О магазине"
@app.route('/about')
def about():
    # здесь просто возвращается html
    return render_template('about.html')


# покупка определённого товара
@app.route('/buy/<name>/<key>')
def item_buy(name, key):
    lst = key.split('_')
    table_name = f"{' '.join(lst).title()}"
    # подключаемся к базе даннных
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    # из таблицы с определённым именем выбираем только подходящую цену
    sqlite_select_query = f"""SELECT price FROM {name} WHERE {name}.item = '{table_name}'"""
    cursor.execute(sqlite_select_query)
    # получаем цену товара
    price = cursor.fetchall()[0][0]
    # платформа для оплаты товара
    # платёж тестовый
    api = Api(merchant_id=1396424,
              secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "RUB",
        "amount": str(price) + "00"
    }
    # чтобы попасть на эту платформу, используем переадресацию
    url = checkout.url(data).get('checkout_url')
    return redirect(url)


# страничка для добавления автора или группы
@app.route('/create', methods=['POST', 'GET'])
def create():
    if request.method == "POST":
        title = request.form['title']
        table_name = f'{title}'.lower()
        if ' ' in title:
            lst = table_name.split()
            table_name = '_'.join(lst)
        elif '/' in title:
            lst = table_name.split('/')
            table_name = '_'.join(lst)
        elif '-' in title:
            lst = table_name.split('-')
            table_name = '_'.join(lst)
        item = Item(title=title)

        # чтобы не возникала ошибка, используем try-except
        try:
            # добавляем эту группу в таблицу Item
            db.session.add(item)
            db.session.commit()
            # у каждого автора или группы есть товар
            # поэтому в базе данных создаём именную таблицу
            conn = sqlite3.connect("shop.db")
            cursor = conn.cursor()
            cursor.execute(f"""CREATE TABLE {table_name}
                              (id INTEGER PRIMARY KEY NOT NULL, 
                              item VARCHAR NOT NULL,
                              price INTEGER)
                           """)
            return redirect('/')
        except:
            return "Получилась ошибка"
    else:
        return render_template('create.html')


# подгружаем сессию пользователя
@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(users.User).get(user_id)


# страница для входа в профиль
@app.route("/login", methods=["GET", "POST"])
def login():
    # используем созданную раннее форму для входа в профиль
    form = LoginForm()
    if form.validate_on_submit():
        # создание сессии пользователя
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template("login.html", message="Неправильный логин или пароль", form=form)
    return render_template("login.html", form=form, current_user=current_user)


# разлогинивание пользователя
@app.route("/logout")
@login_required
def logout():
    # используется встроенная функция из flask_login
    logout_user()
    return redirect('/')


# страница регистрации пользователя
@app.route('/registration', methods=["GET", "POST"])
def register():
    # используем созданную раннее форму для регистрации
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            # проверка на совпадение паролей
            return render_template("registration.html", form=form, message="Пароли не совпадают")
        # создание сессии пользователя
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.login.data).first():
            # проверка на уникальность email
            return render_template("registration.html", form=form, message="Такой email уже зарегистрирован")
        # в таблицу User добавляем нового пользователя
        user = users.User(
            email=form.login.data,
            name=form.name.data,
            address=form.address.data
        )
        # пароль устанавливается отдельно
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        # после успешной регистрации переадресовываем пользователя на страницу входа
        return redirect('/login')
    # иначе повторно регистрируемся
    return render_template("registration.html", form=form)


# профиль пользователя
@app.route('/user_profile')
@login_required
def user_profile():
    # возвращаем html файл и параметр current_user
    # параметр необходим для дальнейшего взаимодействия с пользователем
    return render_template('user_profile.html', current_user=current_user)


# страничка показывает товары каждого автора или группы
@app.route('/show_items/<int:id>')
def show_items(id):
    item = Item.query.get(id)
    table_name = f"{item}".lower()
    # из ссылки форматируем имя таблицы:
    if ' ' in table_name:
        lst = table_name.split()
        table_name = '_'.join(lst)
    elif '/' in table_name:
        lst = table_name.split('/')
        table_name = '_'.join(lst)
    elif '-' in table_name:
        lst = table_name.split('-')
        table_name = '_'.join(lst)
    # подключаемся к базе данных
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    # из нужной таблицы берём товар и его цену
    sqlite_select_query = f"""SELECT item, price from {table_name}"""
    cursor.execute(sqlite_select_query)
    records = cursor.fetchall()
    # словарь из товаров и их цен
    items = {}
    # словарь для ключей
    keys = {}
    for row in records:
        items[row[0]] = row[1]
        k = f'{row[0]}'.lower()
        if ' ' in k:
            lst = k.split()
            k = '_'.join(lst)
        elif '/' in k:
            lst = k.split('/')
            k = '_'.join(lst)
        elif '-' in k:
            lst = k.split('-')
            k = '_'.join(lst)
        keys[row[0]] = k
    return render_template('show_items.html', item=item, items=items, current_user=current_user, name=table_name,
                           keys=keys)


# страничка создания конкретного товара
# кнопка для перехода на эту страницу есть на странице товаров конкретного автора или группы
@app.route('/create_item/<name>', methods=['POST', 'GET'])
def create_item(name):
    if request.method == "POST":
        # из формы получаем имя товара
        item = f"{request.form['item']}"
        # а также цену
        price = request.form['price']

        # для обхода ошибок используем try-except
        try:
            # подключаемся к базе данных
            conn = sqlite3.connect("shop.db")
            cursor = conn.cursor()
            # считаем количество всех елементов в таблице базе данных
            # имя базы данных передано через name
            # cursor.execute(f"SELECT count(*) FROM {name}")
            cursor.execute(f"SELECT id FROM {name}")
            result = cursor.fetchall()
            ids = []
            for i in result:
                for y in i:
                    ids.append(int(y))
            id = max(ids) + 1
            # id увеличиваем на 1, так как в result передано количество id, то есть последний id
            # если id не увеличить, товар не добавится :(
            # кортеж нужен для добавления id товара, его имени и цены
            tup = (id, item, int(price),)
            #
            cursor.execute(f"INSERT INTO {name} VALUES {tup}")
            conn.commit()
            message = 'Успешно добавлено'
            return render_template('create_item.html', name=name, message=message)
        except:
            # если товар не добавлен, возвращаем пользователя на страницу создания товара
            message = 'Не добавлено'
            return render_template('create_item.html', name=name, message=message)
    return render_template('create_item.html', name=name)


# добавление товара в корзину
@app.route('/add_to_cart/<email>/<name>/<key>')
def add_to_cart(email, name, key):
    global id
    lst = key.split('_')
    table_name = f"{' '.join(lst).title()}"
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    sqlite_select_query = f"""SELECT item, price FROM {name} WHERE {name}.item = '{table_name}'"""
    cursor.execute(sqlite_select_query)
    res = cursor.fetchall()[0]
    lst = []
    for el in res:
        lst.append(el)
    cursor.execute(f"SELECT id FROM favourites")
    result = cursor.fetchall()
    ids = []
    for i in result:
        for y in i:
            ids.append(int(y))
    if len(ids) > 0:
        id = max(ids) + 1
    else:
        id = 1
    tup = tuple((id, email, lst[0], lst[1]))
    try:
        cursor.execute(f"INSERT INTO favourites VALUES {tup}")
        conn.commit()
        message = 'Успешно добавлено'
    except:
        message = 'Не удалось добавить'
    return render_template('success.html', res=tup,
                           message=message, ids=ids)


# корзина пользователя
@app.route('/cart/<email>')
def cart(email):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT price FROM favourites WHERE favourites.email = '{email}'"
    )
    result = cursor.fetchall()
    prices = []
    for el in result:
        for p in el:
            prices.append(p)
    total_price = 0
    for price in prices:
        total_price += int(price)
    cursor.execute(
        f"SELECT id, items, price FROM favourites WHERE favourites.email = '{email}'"
    )
    all_items = cursor.fetchall()
    prices = {}
    items = {}
    for item in all_items:
        prices[item[0]] = item[2]
        items[item[0]] = item[1]
    return render_template('cart.html', prices=prices, total_price=total_price,
                           current_user=current_user, items=items)


# удаление товара из корзины
@app.route('/cart/<email>/delete/<id>')
def cart_delete(email, id):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM favourites WHERE favourites.id = {int(id)}"
    )
    conn.commit()
    return redirect(f'/cart/{email}')


# оплата товаров из корзины
@app.route('/buy/<email>/<int:price>')
def buy_all_items(email, price):
    api = Api(merchant_id=1396424,
              secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "RUB",
        "amount": str(price) + "00"
    }
    url = checkout.url(data).get('checkout_url')
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM favourites WHERE favourites.email = '{email}'"
    )
    conn.commit()
    return redirect(url)


# удаление товара конкретного автора
@app.route('/delete_item/<name>/<key>')
def delete_item(name, key):
    lst = key.split('_')
    title = f"{' '.join(lst).title()}"
    try:
        conn = sqlite3.connect("shop.db")
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM {name} WHERE {name}.item = '{title}'"
        )
        conn.commit()
        message = 'Успешно удалено'
        return render_template('delete_item.html', message=message)
    except:
        message = 'Не удалось удалить'
        return render_template('delete_item.html', message=message)


if __name__ == "__main__":
    app.run(debug=True)
