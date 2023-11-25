from flask import Blueprint, jsonify, request

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    # Logic for user registration
    return jsonify({"message": "User registered successfully"}), 201
