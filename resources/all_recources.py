from flask import jsonify
from flask.views import MethodViewType
from data import db_session
from flask_restful import abort, Resource
from data.users import User
from data.items import Item
from data.countries import Country
from data.orders import Order
from data.favourite import FavouriteItems
from data.authors import Author
from parsers.user_parser import parser as user_parser
from parsers.item_parser import parser as item_parser
from parsers.order_parser import parser as order_parser
from parsers.favourite_parser import parser as favourite_parser
from parsers.country_parser import parser as country_parser
from parsers.author_parser import parser as author_parser
from werkzeug.security import check_password_hash

CONFIG_FILE = 'config.txt'
config_file = open(CONFIG_FILE, 'r', encoding='utf-8')
ADMINISTRATOR_PASSWORD_HASH = [line for line in config_file.readlines() if 'PASS' in line]
ADMINISTRATOR_PASSWORD_HASH = ''.join(ADMINISTRATOR_PASSWORD_HASH).split('==')[1].strip()
DICT_OF_ARGUMENTS_FOR_MODELS = {'User': ('id', 'surname', 'name', 'email',
                                         'phone_number', 'address', 'postal_code',
                                         'hashed_password', 'register_date', 'order_id',
                                         'favourite_id', 'account_type'),
                                'Item': ('id', 'title', 'description', 'images_links',
                                         'price', 'country_id', 'author_id'),
                                'Order': ('id', 'items_id', 'is_finished', 'status'),
                                'FavouriteItems': ('id', 'items_id'),
                                'Country': ('id', 'title'),
                                'Author': ('id', 'name')}
DICT_OF_PARSERS = {'User': user_parser,
                   'Item': item_parser,
                   'Order': order_parser,
                   'FavouriteItems': favourite_parser,
                   'Country': country_parser,
                   'Author': author_parser}

"""Классы должны быть созданы с помощью метакласса.
Создание объектов базовых классов не предусмотрено,
но от них могут наследоваться другие классы.
В данном случае должен быть объявлен метод __init__,
устанавливающий атрибуты class_of_object, parser, list_of_arguments
class_of_object - класс модели, для которой создается ресурс API
parser - парсер аргументов для json
list_of_arguments - список/кортеж, содержащий названия полей класса модели для базы данных 
"""


def check_api_key(api_key, get_request=False):
    """
    Проверяет ключ API по хэшу
    API-ключ нужен для любых запросов, кроме get
    и для любых запросов к моделям пользователей
    """
    if not get_request:
        if not api_key:
            return jsonify({'message': 'Not found api key'})
        elif not check_password_hash(ADMINISTRATOR_PASSWORD_HASH, api_key):
            return jsonify({'message': 'Wrong api key'})


class BaseResource(Resource):
    """
    Базовый класс ресурса для API, от которого наследуются классы для реальных моделей.
    Все методы универсальны для всех моделей, но могут быть переопределены при необходимости,
    так как используется наследование.
    """

    def abort_if_object_not_found(self, object_id):
        """Проверка на наличие объекта с нужным id в базе данных"""
        session = db_session.create_session()
        object_ = session.query(self.class_of_object).get(object_id)  # объект нужной модели
        if not object_:
            # сообщение вида: Cloth 785 not found
            abort(404, message=f"{self.class_of_object.__name__} {object_id} not found")

    def get(self, object_id):
        if 'user' in self.class_of_object.__name__.lower():
            args = self.parser.parse_args()
            try:
                api_key = args['api_key']
            except Exception as err:
                return jsonify({'message': f'Api_key required, {err}'})
            check_api_key(api_key)
        self.abort_if_object_not_found(object_id)
        session = db_session.create_session()
        object_ = session.query(self.class_of_object).filter(self.class_of_object.id == object_id).first()
        return jsonify(
            {
                f'{self.class_of_object.__name__}':  # пример: {'Cloth': {id: 78, ...}}
                    object_.to_dict(only=self.list_of_arguments)
            }
        )

    def delete(self, object_id):
        args = self.parser.parse_args()
        try:
            api_key = args['api_key']
        except Exception as err:
            return jsonify({'message': f'Api_key required, {err}'})
        check_api_key(api_key)
        self.abort_if_object_not_found(object_id)
        session = db_session.create_session()
        object_ = session.query(self.class_of_object).get(object_id)
        session.delete(object_)
        session.commit()
        return jsonify({'success': 'OK'})

    def put(self, object_id):
        args = self.parser.parse_args()
        try:
            api_key = args['api_key']
        except Exception as err:
            return jsonify({'message': f'Api_key required, {err}'})
        check_api_key(api_key)
        self.abort_if_object_not_found(object_id)
        session = db_session.create_session()
        object_ = session.query(self.class_of_object).filter(self.class_of_object.id == object_id).first()
        """установка значений аргументов для объекта модели self.class_of_object (эксперимент с setattr)"""
        for arg_name in self.list_of_arguments[1:]:  # [1:] т.к id не меняется
            setattr(object_, arg_name, args[arg_name])
        session.commit()
        return jsonify({'success': 'OK'})


class BaseListResource(Resource):
    """Класс, подобный предыдущему, для списка объектов моделей"""

    def post(self):
        args = self.parser.parse_args()
        try:
            api_key = args['api_key']
        except Exception as err:
            return jsonify({'message': f'Api_key required, {err}'})
        check_api_key(api_key)
        session = db_session.create_session()
        object_ = self.class_of_object()  # создание объекта модели
        # подстановка нужных полей и их значений. [1:] т.к. первый аргумент - id
        # не требуется указывать
        for arg_name in self.list_of_arguments[1:]:
            setattr(object_, arg_name, args[arg_name])  # после создания объекта
        session.add(object_)
        session.commit()
        return jsonify({'success': 'OK'})

    def get(self):
        if 'user' in self.class_of_object.__name__.lower():
            args = self.parser.parse_args()
            try:
                api_key = args['api_key']
            except Exception as err:
                return jsonify({'message': f'Api_key required, {err}'})
            check_api_key(api_key)
        session = db_session.create_session()
        objects = session.query(self.class_of_object).all()
        return jsonify(
            {  # пример: Cloths: [0: {id: 78, ...}, 1: {id: 79}...]
                f'{self.class_of_object.__name__}s':
                    [item.to_dict(only=self.list_of_arguments)
                     for item in objects]
            }
        )


class MetaClassForResources(MethodViewType):
    """
    Метакласс. Создаёт классы API по нужной модели на основе базовых
    см. BaseResource, BaseListResource
    """

    def __init__(cls, cls_obj, lst=False):
        """
        Переопределение метода __init__ класса MethodViewType
        Это нужно только ради отсутствия конфликта метаклассов, так как
        MethodViewType - метакласс
        """
        pass

    def __new__(mcs, class_of_object, lst_class=False):
        name = class_of_object.__name__
        base = BaseListResource if lst_class else BaseResource
        # Аргументы при инициализации базового класса
        # Зависят от нужной модели (класса) - class_of_object
        # вместо подстановки в __init__ они добавляются при создании
        dict_attrs = {'class_of_object': class_of_object,
                      'parser': DICT_OF_PARSERS[name],
                      'list_of_arguments': DICT_OF_ARGUMENTS_FOR_MODELS[name]}
        name += 'ListResource' if lst_class else 'Resource'  # имя будущего класса
        return type.__new__(mcs, name, (base,), dict_attrs)  # возвращает class-объект


def impossible_action(self, object_id):
    return jsonify({'message': 'Impossible'})


UserResource = MetaClassForResources(User)
setattr(UserResource, 'put', impossible_action)  # api не должно менять данные пользователя
setattr(UserResource, 'delete', impossible_action)  # api не должно удалять пользователей
UserListResource = MetaClassForResources(User, True)
setattr(UserListResource, 'post', impossible_action)  # api не должно регистрировать пользователей
ItemResource = MetaClassForResources(Item)
ItemListResource = MetaClassForResources(Item, True)
OrderResource = MetaClassForResources(Order)
OrderListResource = MetaClassForResources(Order, True)
FavouriteItemsResource = MetaClassForResources(FavouriteItems)
FavouriteItemsListResource = MetaClassForResources(FavouriteItems, True)
CountryResource = MetaClassForResources(Country)
CountryListResource = MetaClassForResources(Country, True)
AuthorResource = MetaClassForResources(Author)
AuthorListResource = MetaClassForResources(Author, True)
