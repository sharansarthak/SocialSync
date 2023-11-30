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
storage = pb.storage()

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
def upload_picture(userID):
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
        user_doc = db.child('users').child(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        filename = secure_filename(file.filename)

        # Define the path where the file will be uploaded
        storage.child("images/{userID}").put(file)


        # Make the blob publicly accessible
        url = storage.child("images/{userID}").get_url()

        # Update the user's document in Firestore with the picture URL
        db.child('users').child(user_id).push({'profile_picture_url': url})

        return jsonify({'message': 'Picture uploaded successfully', 'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# @authentication.route('/users/picture/<userID>', methods=['GET'])
# def get_picture(userID):
#     try:
#         user_doc = db.collection('users').document(userID).get()
#         if not user_doc.exists:
#             return jsonify({'error': 'User not found'}), 404

#         user_data = user_doc.to_dict()
#         picture_url = user_data.get('profile_picture_url', 'No picture URL set')
#         return jsonify({'message': 'Picture found successfully', 'url': picture_url})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

