from flask_restful import reqparse

parser = reqparse.RequestParser()
parser.add_argument('api_key', required=True, type=str)
