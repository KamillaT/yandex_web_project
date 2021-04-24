# -*- coding: utf8 -*-
import datetime
import json
import logging

from PIL import Image
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, redirect, render_template, request, abort, make_response, jsonify
from flask_restful import Api
from werkzeug.security import check_password_hash
from wtforms.fields.html5 import EmailField, SearchField
from data import db_session, users, favourite
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField, FieldList, \
    TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Email
import users_api
from data.db_session import global_init, create_session
from data.users import User
from data.orders import Order
from data.favourite import FavouriteItems
from data.items import Item
from data.authors import Author
from data.countries import Country
from requests import get, put, delete
from data.validators import CheckStringFieldByDigit
from resources import all_recources

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
    items = session.query(Item).all()
    for item in items:
        item_authors = item.author_id
        items_country = item.country_id
    for author_ in session.query(Author).all():
        authors.append((author_.id, author_.name + f': {items_authors[str(author_.id)]}'))
    for country_ in session.query(Country).all():
        countries.append((country_.id, country_.title + f': {items_countries[str(country_.id)]}'))
    text = SearchField('Введите поисковый запрос')
    country = SelectField('Страна', choices=countries, coerce=int)
    author = SelectField('Автор', choices=authors, coerce=int)
    submit = SubmitField('Найти')


class OrderForm(FlaskForm):
    count_list = FieldList(IntegerField('Количество (шт.)',
                                        validators=[DataRequired(), CheckStringFieldByDigit()]))
    submit = SubmitField('Перейте к оформлению заказа')


class OrderRegistrationForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('Электронная почта', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    postal_code = StringField('Почтовый индекс', validators=[DataRequired()])
    submit = SubmitField('Подтвердить')


class AddItemForm(FlaskForm):
    DB_NAME = 'Main'
    global_init(f'db/{DB_NAME}.sqlite')
    session = create_session()
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    images = MultipleFileField('Фотографии')
    price = IntegerField('Цена товара (за 1 шт.)', validators=[DataRequired()])
    country = StringField('Страна', validators=[DataRequired()])
    author = StringField('Автор', validators=[DataRequired()])
    submit = SubmitField('Подтвердить')


app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_secret_key"
db_session.global_init(f'db/{DB_NAME}.sqlite')
login_manager = LoginManager()
login_manager.init_app(app)
# api = Api(app)
# api.add_resource(all_recources.UserListResource, '/api/users')
# api.add_resource(all_recources.UserResource, '/api/users/<int:object_id>')
# api.add_resource(all_recources.FavouriteItemsListResource, '/api/favourites')
# api.add_resource(all_recources.FavouriteItemsResource, '/api/favourites/<int:object_id>')
# api.add_resource(all_recources.ItemListResource, '/api/cloths')
# api.add_resource(all_recources.ItemResource, '/api/cloths/<int:object_id>')
# api.add_resource(all_recources.CountryListResource, '/api/countries')
# api.add_resource(all_recources.CountryResource, '/api/countries/<int:object_id>')
# api.add_resource(all_recources.OrderListResource, '/api/orders')
# api.add_resource(all_recources.OrderResource, '/api/orders/<int:object_id>')
# api.add_resource(all_recources.AuthorListResource, '/api/author')
# api.add_resource(all_recources.AuthorResource, '/api/author/<int:object_id>')
API_SERVER = 'https://127.0.0.1:8080'


def administrator_required(page_function):
    def wrapped(*args):
        if current_user.account_type != 'Администратор':
            return redirect('/')
        else:
            page_function(*args)

    return wrapped


def find_item_by_id(item_id):
    session = db_session.create_session()
    item = session.query(Item).filter(Item.id == item_id).first()
    return item


def find_items_by_id(items_id_str: list):
    session = db_session.create_session()
    items = []
    for index in items_id_str:
        item = session.query(Item).filter(Item.id == index).first()
        if item:
            items.append(item)
    return items


def save_images(images: list):
    try:
        config_file = open(CONFIG_FILE, 'r', encoding='utf-8')
        """Индекс последнего изображения в config-файле"""
        index_data, other_data = list(), list()
        for line in config_file.readlines():
            if 'IMAGES_INDEX' in line:
                index_data.append(line)
            else:
                other_data.append(line)
        image_index = int(index_data[0].split('==')[1])
        config_file.close()
        for index, image in enumerate(images):
            file = open(f'./static/img/item/image_{image_index}.png', 'wb')
            file.write(image.stream.read())
            file.close()
            image = Image.open(f'./static/img/item/image_{image_index}.png')
            image = image.resize((1024, 1024), Image.LANCZOS)
            if index == 0:
                image.save(f'./static/img/item/image_{image_index + 1}.png')
                image = image.resize((256, 256), Image.LANCZOS)
                image.save(f'./static/img/item/image_{image_index}.png')
                image_index += 2
            else:
                image_index += 1
        config_file = open(CONFIG_FILE, 'w', encoding='utf-8')
        other_data.append(f'IMAGES_INDEX=={image_index}')
        config_file.writelines(other_data)
        config_file.close()
        file_names = [f'/static/img/item/image_{image_index - i - 1}.png' for i in range(len(images) + 1)]
    except Exception as error:
        logging.error(error)
        file_names = ['']
    return list(reversed(file_names))


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
            if country_id in country_id and item.id in items_id:
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


@login_required
@app.route('/order', methods=['GET', 'POST'])
def view_order(form_data=[]):
    form = OrderForm()
    order_registration_form = OrderRegistrationForm()
    need_count = request.args.get('count', default=False, type=bool)
    confirm_order = request.args.get('confirm', default=False, type=bool)
    session = db_session.create_session()
    order = session.query(Order).filter(Order.id == current_user.order_id).first()
    items_id_in_order = order.items_id.split(DIVISOR)
    items = []
    for index in items_id_in_order:
        item = session.query(Item).filter(Item.id == index).first()
        if item:
            items.append(item)
    length = list(range(len(items)))
    if not form.count_list:
        for i in length:
            form.count_list.append_entry()
    order_summ = 0
    if need_count:
        for index in range(len(items)):
            if form.count_list[index].data:
                order_summ += form.count_list[index].data * items[index].price
    if form.validate_on_submit() and confirm_order:
        form_data.append([entry.data for entry in form.count_list])
        user = session.query(User).filter(User.id == current_user.id).first()
        order_registration_form.surname.data = user.surname
        order_registration_form.name.data = user.name
        order_registration_form.email.data = user.email
        order_registration_form.phone_number.data = user.phone_number
        order_registration_form.address.data = user.address
        order_registration_form.postal_code.data = user.postal_code
        return render_template('order_registration.html', items=items, err=False,
                               length=length, form=order_registration_form)
    elif order_registration_form.is_submitted() and confirm_order:
        if order_registration_form.validate_on_submit():
            for index in range(len(items)):
                items[index].length -= form_data[0][index]
            order.status = f'Ожидает отправки, id пользователя=={current_user.id}'
            new_data_for_items_id = []
            items_id = order.items_id.split(DIVISOR)
            summ = 0
            for index in range(len(items_id)):
                price = session.query(Item).filter(Item.id == items_id[index]).first().price
                new_data_for_items_id.append(
                    f'{items_id[index]}/{form_data[0][index]}/{price}/{form_data[0][index] * price}')
                summ += form_data[0][index] * price
            new_data_for_items_id.append(str(summ))
            order.items_id = DIVISOR.join(new_data_for_items_id)
            user = session.query(User).filter(User.id == current_user.id).first()
            order = Order(items_id='', status='подготовка', is_finished=False)
            session.add(order)
            session.commit()
            user.order_id = order.id
            user.surname = order_registration_form.surname.data
            user.name = order_registration_form.name.data
            user.email = order_registration_form.email.data
            user.phone_number = order_registration_form.phone_number.data
            user.address = order_registration_form.address.data
            user.postal_code = order_registration_form.postal_code.data
            session.commit()
            return render_template('success_order_registration.html')
        else:
            user = session.query(User).filter(User.id == current_user.id).first()
            order_registration_form.surname.data = user.surname
            order_registration_form.name.data = user.name
            order_registration_form.email.data = user.email
            order_registration_form.phone_number.data = user.phone_number
            order_registration_form.address.data = user.address
            order_registration_form.postal_code.data = user.postal_code
            return render_template('order_registration.html', items=items, err=True,
                                   length=length, form=order_registration_form)
    return render_template('view_items_in_order.html', items=items, form=form,
                           length=length, count=need_count, summ=order_summ)


@login_required
@app.route('/order/delete/<item_id>')
def delete_item_from_order(item_id):
    session = db_session.create_session()
    order = session.query(Order).filter(
        Order.id == current_user.order_id).first()
    items = order.items_id.split(DIVISOR)
    new_items = []
    for item in items:
        if item != item_id:
            new_items.append(item)
    items = DIVISOR.join(new_items)
    order.items_id = items
    session.commit()
    return '<script>document.location.href = document.referrer</script>'


@login_required
@app.route('/order/<item_id>')
def add_item_to_order(item_id):
    session = db_session.create_session()
    item = find_item_by_id(item_id)
    if item:
        order = session.query(Order).filter(
            Order.id == current_user.order_id).first()
        if order.items_id:
            items = order.items_id.split(DIVISOR)
            if item_id not in items:
                items.append(item_id)
                items = DIVISOR.join(items)
                order.items_id = items
                session.commit()
        else:
            order.items_id = item_id
            session.commit()
    return '<script>document.location.href = document.referrer</script>'


@app.route('/view/<int:item_id>')
def view_item(item_id):
    item = find_item_by_id(item_id)
    country = get(API_SERVER + f'/countries/{item.country_id}').json()
    if country:
        item.country_id = country['Country'].get('title', 'Неизвестно')
    authors_id = [int(author_id) for author_id in item.author_id.split(DIVISOR)]
    authors_titles = []
    for author_id in authors_id:
        author_of_item = get(API_SERVER + f'/types/{author_id}').json()
        if 'error' not in author_of_item:
            authors_titles.append(author_of_item['Authors'].get('title', 'Неизвестно'))
    item.author_id = ', '.join(authors_titles)
    return render_template('view_item.html', item=item)


@app.route('/view/image')
def view_image():
    link = request.args.get('img', default=None)
    return render_template('view_image.html', link=link)


@login_required
@app.route('/favourites/<item_id>')
def add_item_to_favourites(item_id):
    session = db_session.create_session()
    item = find_item_by_id(item_id)
    if item:
        favourite_items = session.query(FavouriteItems).filter(
            FavouriteItems.id == current_user.favourite_id).first()
        current_user.favourite_id = favourite_items.id
        if favourite_items.items_id:
            items = favourite_items.items_id.split(DIVISOR)
            if item_id not in items:
                items.append(item_id)
                items = DIVISOR.join(items)
                favourite_items.items_id = items
                session.commit()
        else:
            favourite_items.items_id = item_id
            session.commit()
    return '<script>document.location.href = document.referrer</script>'


@login_required
@app.route('/favourites/delete/<item_id>')
def delete_item_from_favourites(item_id):
    session = db_session.create_session()
    favourite_items = session.query(FavouriteItems).filter(
        FavouriteItems.id == current_user.favourite_id).first()
    items = favourite_items.items_id.split(DIVISOR)
    new_items = []
    for item in items:
        if item != item_id:
            new_items.append(item)
    items = DIVISOR.join(new_items)
    favourite_items.items_id = items
    session.commit()
    return '<script>document.location.href = document.referrer</script>'


@login_required
@app.route('/favourites')
def view_favourites():
    session = db_session.create_session()
    favourites = session.query(FavouriteItems).filter(
        FavouriteItems.id == current_user.favourite_id).first()
    items_id_in_favourites = favourites.items_id.split(';')
    items = find_items_by_id(items_id_in_favourites)
    return render_template('view_items_in_favourites.html', items=items)


@login_required
@administrator_required
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    form = AddItemForm()
    if form.errors:
        print(form.errors)
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(Item).filter(Item.title == form.title.data).first():
            return render_template('add_item.html', title='Добавление товара',
                                   form=form, message='Такой товар уже есть')
        country = session.query(Country).filter(Country.title == form.country.data).first()
        if country is None:
            country = Country(title=form.country.data)
            session.add(country)
            session.commit()
            country = session.query(Country).filter(
                Country.title == form.country.data).first()
        author = session.query(Author).filter(Author.name == form.author.data).first()
        if author is None:
            author = Author(title=form.country.data)
            session.add(author)
            session.commit()
            author = session.query(Author).filter(
                Author.name == form.author.data).first()
        country_id = country.id
        author_id = author.id
        images = request.files.getlist('images')
        file_names = ';'.join(save_images(images))
        item = Item(
            title=form.title.data,
            description=form.description.data,
            images_links=file_names,
            price=form.price.data,
            country_id=country_id,
            author_id=author_id,
        )
        session.add(item)
        session.commit()
        return redirect('/')
    return render_template('add_item.html', title='Добавление товара', form=form)


@login_required
@administrator_required
@app.route('/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    form = AddItemForm()
    if request.method == "GET":
        session = db_session.create_session()
        item = session.query(Item).filter(Item.id == item_id).first()
        if item:
            form.title.data = item.title
            form.description.data = item.description
            form.price.data = item.price
            country = session.query(Country).filter(Country.title == item.country_id).first()
            form.country.data = country
            author = session.query(Author).filter(Author.name == item.author_id).first()
            form.author.data = author
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        item = session.query(Item).filter(Item.id == item_id).first()
        if item:
            country = session.query(Country).filter(Country.title == form.country.data).first()
            if country is None:
                country = Country(title=form.country.data)
                session.add(country)
                session.commit()
                country = session.query(Country).filter(Country.title == form.country.data).first()
            country_id = country.id
            author = session.query(Author).filter(Author.name == item.author_id).first()
            if author is None:
                author = Author(title=form.author.data)
                session.add(author)
                session.commit()
                author = session.query(Author).filter(Author.name == item.author_id).first()
            author_id = author.id
            images = request.files.getlist('images')
            file_names = ';'.join(save_images(images))
            item.title = form.title.data
            item.images_links = file_names
            item.description = form.description.data
            item.images_links = file_names
            item.price = form.price.data
            item.country = country_id
            item.author = author_id
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('add_item.html', title='Редактирование ткани', form=form)


@login_required
@administrator_required
@app.route('/delete/<int:item_id>', methods=['GET', 'POST'])
def delete_item(item_id):
    delete(API_SERVER + f'/items/{item_id}', json={'api_key': 'r651I45H5P3Za45s'})
    return redirect('/')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


if __name__ == "__main__":
    db_session.global_init("db/data_base.sqlite")
    app.register_blueprint(users_api.blueprint)
    app.run(port=8080, host="127.0.0.1")
