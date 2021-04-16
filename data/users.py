import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    age = sqlalchemy.Column(sqlalchemy.Integer)
    address = sqlalchemy.Column(sqlalchemy.String)
    postal_code = sqlalchemy.Column(sqlalchemy.String)
    phone_number = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    register_date = sqlalchemy.Column(sqlalchemy.Date)  # datetime.date()
    order_id = sqlalchemy.Column(sqlalchemy.ForeignKey('order.id'))
    order = orm.relation('Order')
    favourite_id = sqlalchemy.Column(sqlalchemy.ForeignKey('favourites.id'))
    favourites = orm.relation('FavouriteItems')
    account_type = sqlalchemy.Column(sqlalchemy.String(100), default='Участник')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def set_administrator(self):
        self.account_type = 'Администратор'

    def set_date_time(self, time):
        self.register_date = time
