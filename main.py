# -*- coding: utf8 -*-
import datetime
import logging

from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, redirect, render_template, request, abort, make_response, jsonify
from werkzeug.security import check_password_hash
from wtforms.fields.html5 import EmailField, SearchField
from data import db_session, users, favourite
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email
import users_api
from data.db_session import global_init, create_session
from data.users import User
from data.orders import Order
from data.favourite import FavouriteItems
from data.items import Item
from data.authors import Author
from data.countries import Country
import requests
from requests import get, put
import sys

LOG_FILE = 'Log.log'  # имя файла с логами сервера
CONFIG_FILE = 'config.txt'  # имя файла с настроками сайта
# разделитель между данными в одном поле модели в базе данных, един для всего,
# кроме разделения суммы/цены/количества тканей в оформленном заказе пользователя
DIVISOR = ';'
COUNT_ITEMS_BY_PAGE = 6  # количество товаров на страницу
DB_NAME = 'Main'
# запись логов сервера
logging.basicConfig(
    level=logging.ERROR,
    filename=LOG_FILE,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
config_file = open(CONFIG_FILE, 'r')
ADMINISTRATOR_PASSWORD_HASH = [line for line in config_file.readlines() if 'PASS' in line]
ADMINISTRATOR_PASSWORD_HASH = ''.join(ADMINISTRATOR_PASSWORD_HASH).split('==')[1].strip()
config_file.close()


class LoginForm(FlaskForm):
    email = EmailField('Электронная почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('Электронная почта', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона')
    address = StringField('Адрес')
    postal_code = StringField('Почтовый индекс')
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_repeat = PasswordField('Повторите пароль', validators=[DataRequired()])
    submit = SubmitField('Подтвердить')


class SearchForm(FlaskForm):
    DB_NAME = 'data_base'
    global_init(f'db/{DB_NAME}.sqlite')
    session = create_session()
    authors = [(0, 'Все')]
    countries = [(0, 'Все')]
    authors_length = session.query(Author).count()
    countries_length = session.query(Country).count()
    items_authors = {str(key_id): 0 for key_id in range(1, authors_length + 1)}
    items_countries = {str(key_id): 0 for key_id in range(1, countries_length + 1)}
    cloths = session.query(Item).all()
    for cloth in cloths:
        item_authors = cloth.author_id.split(';')
        items_country = cloth.country_id.split(';')
        for _author in item_authors:
            items_authors[_author] += 1
        for _country in items_country:
            items_countries[_country] += 1
    for author_ in session.query(Author).all():
        authors.append((author_.id, author_.title + f': {items_authors[str(author_.id)]}'))
    for country_ in session.query(Country).all():
        countries.append((country_.id, country_.title + f': {items_countries[str(country_.id)]}'))
    text = SearchField('Введите поисковый запрос')
    country = SelectField('Страна', choices=countries, coerce=int)
    author = SelectField('Автор', choices=authors, coerce=int)
    submit = SubmitField('Найти')


app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_secret_key"
db_session.global_init(f'db/{DB_NAME}.sqlite')
API_SERVER = "http://127.0.0.1:8080/"

login_manager = LoginManager()
login_manager.init_app(app)


def administrator_required(page_function):
    def wrapped(*args):
        if current_user.account_type != 'Администратор':
            return redirect('/')
        else:
            page_function(*args)

    return wrapped


def find_cloth_by_id(item_id):
    session = db_session.create_session()
    item = session.query(Item).filter(Item.id == item_id).first()
    return item


def find_cloths_by_id(items_id_str: list):
    session = db_session.create_session()
    items = []
    for index in items_id_str:
        item = session.query(Item).filter(Item.id == index).first()
        if item:
            items.append(item)
    return items


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(users.User).get(user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template("login.html", message="Неправильный логин или пароль", form=form,
                               current_user=current_user)
    return render_template("login.html", form=form, current_user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        order = Order(is_finished=False, status="подготовка", items_id='')
        favourite_items = FavouriteItems(items_id='')
        user = User(
            surname=form.surname.data,
            name=form.name.data,
            email=form.email.data,
            phone_number=form.phone_number.data,
            address=form.address.data,
            postal_code=form.postal_code.data,
            order=order,
            favourites=favourite_items)
        if form.password.data != form.password_repeat.data:
            if not check_password_hash(ADMINISTRATOR_PASSWORD_HASH, form.password_repeat.data):
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            else:
                user.set_administrator()
        user.set_password(form.password.data)
        time = datetime.datetime.now()
        user.set_date_time(time)
        session.add(favourite_items)
        session.add(order)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@login_required
@administrator_required
@app.route('/user_orders')
def view_user_orders():
    session = db_session.create_session()
    orders = session.query(Order).filter(Order.status.startswith('Ожидает отправки,')).all()
    user_data = {order.id: session.query(User).filter(User.id == order.status.split('==')[1]).first()
                 for order in orders}
    return render_template('view_user_orders.html', orders=orders, user_data=user_data)


@login_required
@administrator_required
@app.route('/order_finish/<int:order_id>')
def order_make_finish(order_id):
    order = get(API_SERVER + f'/orders/{order_id}').json()['Order']
    put(API_SERVER + f'/orders/{order_id}', json={'api_key': 'r651I45H5P3Za45s',
                                                  'items_id': order['items_id'],
                                                  'is_finished': True,
                                                  'status': order['status']})


@app.route('/user_profile')
def user_profile():
    return render_template("user_profile.html", current_user=current_user)


@app.route('/favourites')
def favourites():
    return render_template("favourites.html", current_user=current_user)


@app.route('/', methods=['GET', 'POST'])
def main_page(form_data=[]):
    session = db_session.create_session()
    search_form = SearchForm()
    page_number = int(request.args.get('page', 0))
    search, country_id, author_id = None, None, None
    if search_form.validate_on_submit():
        page_number = 0
        search = search_form.text.data
        country_id = search_form.country.data
        author_id = search_form.author.data
        form_data.append([search_form.text.data, search_form.author.data, search_form.country.data])
    else:
        if form_data:
            search, author_id, country_id = form_data[-1]
            search_form.text.data = search
            search_form.author.data = author_id
            search_form.country.data = country_id
    items = list(session.query(Item))
    items_id = [item.id for item in items]
    if search:
        items = list(session.query(Item).filter(Item.title.like(f'%{search}%')))
        items_id = [item.id for item in items]
    if country_id:
        temp = []
        for item in items:
            country_id = item.country_id.split(DIVISOR)
            if str(country_id) in country_id and item.id in items_id:
                temp.append(item)
        items = temp.copy()
        items_id = [item.id for item in items]
    if author_id:
        temp = []
        for item in items:
            item_author_id = item.author_id.split(DIVISOR)
            if str(author_id) in item_author_id and item.id in items_id:
                temp.append(item)
        items = temp.copy()
    max_page_number = len(items) // COUNT_ITEMS_BY_PAGE
    if len(items) % COUNT_ITEMS_BY_PAGE != 0:
        max_page_number += 1
    items = items[COUNT_ITEMS_BY_PAGE * page_number:COUNT_ITEMS_BY_PAGE * (page_number + 1)]
    administrator = session.query(User).filter(User.account_type == 'Администратор').first()
    administrator_email = administrator.email
    cash_data_for_country = {}
    for item in items:
        if item.country_id not in cash_data_for_country:
            country = get(API_SERVER + f'/countries/{item.country_id}').json()
            cash_data_for_country[item.country_id] = country['Country'].get('title', 'Неизвестно')
        item.country_id = cash_data_for_country[item.country_id]
    return render_template('main_page.html', items=items,
                           page_number=page_number, max_page_number=max_page_number,
                           form=search_form, email=administrator_email)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


if __name__ == "__main__":
    db_session.global_init("db/data_base.sqlite")
    app.register_blueprint(users_api.blueprint)
    app.run(port=8080, host="127.0.0.1")
