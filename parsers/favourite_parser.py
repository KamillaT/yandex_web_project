from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('id', required=True, type=int)
parser.add_argument('items_id', required=True, type=str)
parser.add_argument('api_key', required=True, type=str)
