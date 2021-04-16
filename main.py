# -*- coding: utf8 -*-
import datetime
import logging

from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, redirect, render_template, request, abort, make_response, jsonify
from werkzeug.security import check_password_hash
from wtforms.fields.html5 import EmailField
from data import db_session, users, favourite
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email
import users_api
from data.users import User
from data.orders import Order
from data.favourite import FavouriteItems
import requests
from requests import get
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


app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_secret_key"

login_manager = LoginManager()
login_manager.init_app(app)


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


@app.route('/user_profile')
def user_profile():
    return render_template("user_profile.html", current_user=current_user)


@app.route('/favourites')
def favourites():
    return render_template("favourites.html", current_user=current_user)


@app.route('/')
def base():
    return render_template("base.html", current_user=current_user)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


if __name__ == "__main__":
    db_session.global_init("db/data_base.sqlite")
    app.register_blueprint(users_api.blueprint)
    app.run(port=8080, host="127.0.0.1")
