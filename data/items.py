import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase


class Item(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'items'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    """Ссылки на изображения на сервере, разделены ';'"""
    images_links = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    country_id = sqlalchemy.Column(sqlalchemy.ForeignKey('countries.id'))
    author_id = sqlalchemy.Column(sqlalchemy.ForeignKey('authors.id'))

    def get_images(self, all_images=False):
        if all_images:
            return self.images_links.split(';')
        else:
            return self.images_links.split(';')[0]

    def get_url(self):
        return f'/{self.id}'
