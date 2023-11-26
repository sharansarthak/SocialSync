from flask import Blueprint, jsonify, request
from firebase_admin import firestore

test = Blueprint('test', __name__)

@test.route('/')
def index():
    return 'Hello, World!'

@test.route('/add-test-item', methods=['POST'])
def add_test_item():
    data = request.json
    db = firestore.client()
    test_item_ref = db.collection('test_items').document()
    test_item_ref.set(data)
    return jsonify({"message": "Test item added", "id": test_item_ref.id}), 201

@test.route('/get-test-item/<id>', methods=['GET'])
def get_test_item(id):
    db = firestore.client()
    test_item_ref = db.collection('test_items').document(id)
    test_item = test_item_ref.get()
    if test_item.exists:
        return jsonify(test_item.to_dict()), 200
    else:
        return jsonify({"message": "Item not found"}), 404
