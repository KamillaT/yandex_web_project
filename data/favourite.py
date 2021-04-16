import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase


class FavouriteItems(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'favourites'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user = orm.relation('User', back_populates='favourites')
    items_id = sqlalchemy.Column(sqlalchemy.String)
