from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('id', required=False, type=int)
parser.add_argument('title', required=True)
parser.add_argument('description', required=True)
parser.add_argument('images_links', required=True)
parser.add_argument('price', required=True, type=int)
parser.add_argument('country_id', required=True)
parser.add_argument('author_id', required=True)
parser.add_argument('api_key', required=True, type=str)
