from flask import Blueprint, jsonify, request, current_app
import json
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth
from werkzeug.utils import secure_filename
from functools import wraps
from app.helpers import is_strong_password, is_valid_email

authentication = Blueprint('authentication', __name__)

cred = credentials.Certificate('fbAdminConfig.json')
pb = pyrebase.initialize_app(json.load(open('fbconfig.json')))
firebase = firebase_admin.initialize_app(cred)
pyrebase_auth = pb.auth()
db = pb.database()
pb_storage = pb.storage()

def check_token(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if not request.headers.get('authorization'):
            return {'message': 'No token provided'},400
        try:
            user = auth.verify_id_token(request.headers['authorization'])
        except Exception as e:
            return {'message':'Invalid token provided.'},400
        return f(*args, **kwargs)
    return wrap



#Api route to sign up a new user, returns user data with token when successful, also adds the user in the database
@authentication.route('/api/signup', methods=['POST'] )
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    data['events'] = ""
    print(data)
    if email is None or password is None:
        return {'message': 'Error missing email or password'},400
    # if not (email and password and name):
    #     return jsonify({'error': 'Missing fields'}), 400
    # if not is_valid_email(email):
    #     return jsonify({'error': 'Invalid email'}), 400
    # if not is_strong_password(password):
    #     return jsonify({'error': 'Password is not strong enough'}), 400
    try:
        user = pyrebase_auth.create_user_with_email_and_password(
            email=email,
            password=password
        )
        localID = user.get("localId")
        db.child("users").child(localID).set(data)
        return {'message': f'Successfully created user {user}'},200
    except:
        return {'message': 'Error creating user'},400
    
#Api route to get a new token for a valid user
@authentication.route('/api/login', methods=['GET'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    try:
        user = pb.auth().sign_in_with_email_and_password(email, password)
        jwt = user['idToken']
        localID = user.get("localId")
        return {'token': jwt, 'userID': localID}, 200
    except:
        return {'message': 'There was an error logging in'},400

@authentication.route('/api/users/<userID>', methods=['PUT'])
@check_token
def update_user(userID):
    try:
        data = request.json
        print(data)
        db.child('users').child(userID).update(data)
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@authentication.route('/api/users/<userID>', methods=['DELETE'])
@check_token
def delete_user(userID):
    try:
        db.child('users').document(userID).delete()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@authentication.route('/api/users/picture/<userID>', methods=['POST'])
@check_token
def upload_picture(userID):
    try:
        # Check if 'picture' is present in the request files
        if 'image' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['image']
        # Check if the filename is not empty
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Validate that the user ID is provided
        if not userID:
            return jsonify({'error': 'User ID is missing'}), 400

        # Check if the user exists in Firestore
        user_doc = db.child('users').child(userID).get()
        print(user_doc.val(), type(user_doc))
        if user_doc.val() is None:
            return jsonify({'error': 'User not found'}), 404

        filename = secure_filename(file.filename)

        # Define the path where the file will be uploaded
        path = "images/" + userID
        print(path)
        pb_storage.child(path).put(file)
        print(filename)

        # Make the blob publicly accessible
        url = pb_storage.child(path).get_url()
        print(url)
        # Update the user's document in Firestore with the picture URL
        user_doc_dict =  user_doc.val()
        user_doc_dict['picture_url'] = url
        print(str((json.dumps(user_doc_dict))))
        db.child('users').child(userID).remove()
        db.child('users').child(userID).set(user_doc_dict)

        return jsonify({'message': 'Picture uploaded successfully', 'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@authentication.route('/api/users/picture/<userID>', methods=['GET'])
@check_token
def get_picture(userID):
    try:
        user_doc = db.child('users').child(userID).get()
        if user_doc.val() is None:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.val()
        picture_url = user_data.get('picture_url')
        return jsonify({'message': 'Picture found successfully', 'url': picture_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

