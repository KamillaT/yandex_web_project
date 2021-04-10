from flask import Blueprint, Flask, jsonify, request
from data import db_session, users

blueprint = Blueprint("users_api", __name__, template_folder="templates")


@blueprint.route("/api/users")
def get_users():
    session = db_session.create_session()
    users_ = session.query(users.User).all()
    return jsonify(
        {
            'users':
                [item.to_dict(
                    only=('surname', 'name', 'age', 'address', 'email'))
                    for item in users_]
        }
    )


@blueprint.route("/api/users/<int:users_id>", methods=["GET"])
def get_one_user(users_id):
    session = db_session.create_session()
    user = session.query(users.User).get(users_id)
    if not user:
        return jsonify({"error": "Not found"})
    return jsonify(
        {
            'user':
                user.to_dict(only=('surname', 'name', 'age', 'address', 'email', 'city_from'))
        }
    )


@blueprint.route("/api/users", methods=["POST"])
def create_user():
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(key in request.json for key in
                 ["surname", "name", "age", "address", "email", "id", "password"]):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    ex_user = session.query(users.User).get(request.json["id"])
    if ex_user:
        return jsonify({"error": "id already exists"})
    user = users.User(
        id=request.json["id"],
        surname=request.json["surname"],
        name=request.json["name"],
        age=request.json["age"],
        address=request.json["address"],
        email=request.json["email"]
    )
    user.set_password(request.json["password"])
    session.add(user)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route("/api/users/<int:users_id>", methods=["DELETE"])
def delete_user(users_id):
    session = db_session.create_session()
    user = session.query(users.User).get(users_id)
    if not user:
        return jsonify({"error": "Not found"})
    session.delete(user)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route("/api/users/<int:users_id>", methods=["PUT"])
def edit_user(users_id):
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(
            key in request.json for key in
            ["surname", "name", "age", "address", "email", "password"]):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    user = session.query(users.User).get(users_id)
    if not user:
        return jsonify({"error": "Id doesn't exist"})
    user.surname = request.json["surname"]
    user.name = request.json["name"]
    user.age = request.json["age"]
    user.address = request.json["address"]
    user.email = request.json["email"]
    user.set_password(request.json["password"])
    session.commit()
    return jsonify({"success": "OK"})