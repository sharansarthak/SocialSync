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

@authentication.route('/users/<userID>', methods=['DELETE'])
def delete_user(userID):
    try:
        db.child('users').document(userID).delete()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @authentication.route('/users', methods=['POST'])
# def create_user():
#     try:
#         data = request.json
#         email = data.get('email')
#         password = data.get('password')
#         name = data.get('name')

#         if not (email and password and name):
#             return jsonify({'error': 'Missing fields'}), 400
#         if not is_valid_email(email):
#             return jsonify({'error': 'Invalid email'}), 400
#         if not is_strong_password(password):
#             return jsonify({'error': 'Password is not strong enough'}), 400

#         user_record = authentication.create_user(
#             email=email,
#             password=password,
#             display_name=name
#         )
#         user_data = {'name': name, 'email': email}
#         return jsonify({'message': 'User created successfully', 'userId': user_record.uid})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @authentication.route('/login', methods=['POST'])
# def login():
#     try:
#         data = request.json
#         id_token = data.get('idToken')

#         if not id_token:
#             return jsonify({'error': 'ID token is missing'}), 400

#         # Verify the ID token

#         # Optionally, retrieve additional user information from Firestore if needed
#         # user_data = db.collection('users').document(uid).get().to_dict()

#         return jsonify({'message': 'Login successful', 'uid': uid})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @authentication.route('/users/<userID>', methods=['PUT'])
# def update_user(userID):
#     try:
#         data = request.json
#         db.collection('users').document(userID).update(data)
#         return jsonify({'message': 'User updated successfully'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @authentication.route('/users/<userID>', methods=['DELETE'])
# def delete_user(userID):
#     try:
#         authentication.delete_user(userID)
#         db.collection('users').document(userID).delete()
#         return jsonify({'message': 'User deleted successfully'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @authentication.route('/users/picture', methods=['POST'])
# def upload_picture():
#     try:
#         # Check if 'picture' is present in the request files
#         if 'picture' not in request.files:
#             return jsonify({'error': 'No file part'}), 400

#         file = request.files['picture']

#         # Check if the filename is not empty
#         if file.filename == '':
#             return jsonify({'error': 'No selected file'}), 400

#         # Validate that the user ID is provided
#         user_id = request.form.get('userId')
#         if not user_id:
#             return jsonify({'error': 'User ID is missing'}), 400

#         # Check if the user exists in Firestore
#         user_doc = db.collection('users').document(user_id).get()
#         if not user_doc.exists:
#             return jsonify({'error': 'User not found'}), 404

#         filename = secure_filename(file.filename)

#         # Define the path where the file will be uploaded
#         blob = storage.bucket().blob(f'profile_pictures/{user_id}/{filename}')
#         blob.upload_from_file(file, content_type=file.content_type)

#         # Make the blob publicly accessible
#         blob.make_public()

#         # Update the user's document in Firestore with the picture URL
#         db.collection('users').document(user_id).update({'profile_picture_url': blob.public_url})

#         return jsonify({'message': 'Picture uploaded successfully', 'url': blob.public_url})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
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

