from flask import Blueprint, jsonify, request
from firebase_admin import firestore, storage
from werkzeug.utils import secure_filename

from app.helpers import is_strong_password, is_valid_email

auth = Blueprint('auth', __name__)
def get_firestore_client():
    return firestore.client()

@auth.route('/users', methods=['POST'])
def create_user():
    db = get_firestore_client()    
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not (email and password and name):
            return jsonify({'error': 'Missing fields'}), 400
        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email'}), 400
        if not is_strong_password(password):
            return jsonify({'error': 'Password is not strong enough'}), 400

        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        user_data = {'name': name, 'email': email}
        db.collection('users').document(user_record.uid).set(user_data)
        return jsonify({'message': 'User created successfully', 'userId': user_record.uid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        id_token = data.get('idToken')

        if not id_token:
            return jsonify({'error': 'ID token is missing'}), 400

        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        # Optionally, retrieve additional user information from Firestore if needed
        # user_data = db.collection('users').document(uid).get().to_dict()

        return jsonify({'message': 'Login successful', 'uid': uid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth.route('/users/<userID>', methods=['PUT'])
def update_user(userID):
    db = get_firestore_client()
    try:
        data = request.json
        db.collection('users').document(userID).update(data)
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth.route('/users/<userID>', methods=['DELETE'])
def delete_user(userID):
    db = get_firestore_client()
    try:
        auth.delete_user(userID)
        db.collection('users').document(userID).delete()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth.route('/users/picture', methods=['POST'])
def upload_picture():
    db = get_firestore_client()
    try:
        # Check if 'picture' is present in the request files
        if 'picture' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['picture']

        # Check if the filename is not empty
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Validate that the user ID is provided
        user_id = request.form.get('userId')
        if not user_id:
            return jsonify({'error': 'User ID is missing'}), 400

        # Check if the user exists in Firestore
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        filename = secure_filename(file.filename)

        # Define the path where the file will be uploaded
        blob = storage.bucket().blob(f'profile_pictures/{user_id}/{filename}')
        blob.upload_from_file(file, content_type=file.content_type)

        # Make the blob publicly accessible
        blob.make_public()

        # Update the user's document in Firestore with the picture URL
        db.collection('users').document(user_id).update({'profile_picture_url': blob.public_url})

        return jsonify({'message': 'Picture uploaded successfully', 'url': blob.public_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@auth.route('/users/picture/<userID>', methods=['GET'])
def get_picture(userID):
    db = get_firestore_client()
    try:
        user_doc = db.collection('users').document(userID).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()
        picture_url = user_data.get('profile_picture_url', 'No picture URL set')
        return jsonify({'message': 'Picture found successfully', 'url': picture_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

