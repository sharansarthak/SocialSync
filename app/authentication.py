import os
from flask import Blueprint, jsonify, request, current_app
import json
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth
from werkzeug.utils import secure_filename
from functools import wraps
from app.helpers import is_strong_password, is_valid_email
from flask_cors import CORS, cross_origin
import logging
from requests.exceptions import HTTPError  # Import HTTPError from requests module

authentication = Blueprint('authentication', __name__)

config = {
    "apiKey": os.environ.get("API_KEY"),
    "authDomain": os.environ.get("AUTH_DOMAIN"),
    "databaseURL": os.environ.get("DATABASE_URL"),
    "projectId": os.environ.get("PROJECT_ID"),
    "storageBucket": os.environ.get("STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("MESSAGING_SENDER_ID"),
    "appId": os.environ.get("APP_ID"),
    "measurementId": os.environ.get("MEASUREMENT_ID")
}

# Initialize Firebase Admin using environment variables
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.environ.get("PROJECT_ID"),
    "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
    "private_key": os.environ.get("PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.environ.get("CLIENT_EMAIL"),
    "client_id": os.environ.get("CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-krv15%40socialsync-35f38.iam.gserviceaccount.com"
})

pb = pyrebase.initialize_app(config)
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
@cross_origin(supports_credentials=True)
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
@authentication.route('/api/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    logging.debug("Login request received")

    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        logging.warning("Missing email or password in request")
        return jsonify({'message': 'Email and password are required'}), 400

    try:
        logging.debug(f"Attempting to authenticate user: {email}")
        user = pb.auth().sign_in_with_email_and_password(email, password)
        jwt = user['idToken']
        localID = user.get("localId")
        logging.info(f"User authenticated successfully: {email}")
        return jsonify({'token': jwt, 'userID': localID}), 200
    except HTTPError as httpErr:
        # Extracting the detailed error message from HTTPError
        error_message = json.loads(httpErr.args[1])['error']['message']
        logging.error(f"Authentication failed for user {email}: {error_message}")
        if error_message == "INVALID_LOGIN_CREDENTIALS":
            return jsonify({'message': 'Invalid credentials'}), 401
        else:
            return jsonify({'message': 'Authentication failed'}), 400
    except Exception as e:
        logging.exception("Unexpected error occurred during login")
        return jsonify({'message': 'There was an error logging in'}), 500


@authentication.route('/api/users/<userID>', methods=['PUT'])
@cross_origin(supports_credentials=True)
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
@cross_origin(supports_credentials=True)
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
@cross_origin(supports_credentials=True)
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

