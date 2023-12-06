import datetime
from http.client import BAD_REQUEST
import logging
import traceback
from venv import logger
from flask import Blueprint, jsonify, request, current_app
import json
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth
from requests.exceptions import HTTPError
import requests
from werkzeug.utils import secure_filename
from functools import wraps
from app.helpers import is_strong_password, is_valid_email
from random import randint, randrange
from collections import OrderedDict
from flask_cors import CORS, cross_origin
import os

api_app = Blueprint('api_app', __name__)

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

#Initialize apps for firebase and pyrebase
#Initialize authentication, database and storage 
pb = pyrebase.initialize_app(config)
firebase = firebase_admin.initialize_app(cred)
pyrebase_auth = pb.auth()
db = pb.database()
pb_storage = pb.storage()


#Check token function to validate user authenticity
def check_token(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if not request.headers.get('Authorization'):
            return {'message': 'No token provided'},400
        try:
            user = auth.verify_id_token(request.headers['Authorization'])
        except Exception as e:
            return {'message':'Invalid token provided.'},400
        return f(*args, **kwargs)
    return wrap



#Api route to sign up a new user, returns user data with token when successful, also adds the user in the database
@api_app.route('/api/signup', methods=['POST'])
@cross_origin(supports_credentials=True)
def signup():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        age = data.get('age')
        description = data.get('description')

        # Validating required fields
        if not all([email, password, name, age, description]):
            return jsonify({'message': 'Error: Missing email, password, name, age, description'}), 400

        # Creating a new user
        user = pyrebase_auth.create_user_with_email_and_password(email, password)
        localID = user.get("localId")

        # Setting additional default values
        user_data = {
            'name': name,
            'email': email,
            'age': age,
            'description': description,
            'events_interested': ['none'],
            'events_created': ['none'],
            'events_enrolled': ['none'],
            'description': "",
            'rating': [5]
        }

        # Save the user data in the database
        db.child("users").child(localID).set(user_data)
        # Create user in ChatEngine
        # create_chat_engine_user(name, email, localID)
        return jsonify({'message': 'User created successfully', 'user': user}), 200

    except HTTPError as http_err:
        # Log the HTTPError object for debugging
        try:
            # Parsing the string representation of HTTPError to JSON
            error_message_str = str(http_err)
            start = error_message_str.find('{')
            end = error_message_str.rfind('}') + 1
            error_json_str = error_message_str[start:end]
            error_details = json.loads(error_json_str)

            # Extracting the 'message' and 'code' from the error details
            error_message = error_details.get('error', {}).get('message', 'An unexpected error occurred')
            error_code = error_details.get('error', {}).get('code', 400)

            # Return a response with the extracted error message
            return jsonify({'message': error_message}), error_code

        except (json.JSONDecodeError, ValueError):
            # Fallback if parsing fails
            return jsonify({'message': 'An unexpected error occurred'}), 400

    except Exception as e:
        # Handle other exceptions
        return jsonify({'message': "Failed to create user"}), 500


def create_chat_engine_user(username, email, local_id):
    chat_engine_private_key = os.environ.get("CHAT_ENGINE_PRIVATE_KEY") 
    chat_user_data = {
        "username": username,
        "secret": local_id,  # Using Firebase localId as the secret
        "email": email
    }

    headers = {
        'PRIVATE-KEY': chat_engine_private_key
    }

    response = requests.post(
        'https://api.chatengine.io/users/',
        headers=headers,
        json=chat_user_data
    )

    if response.status_code != 201:
        print("Failed to create user in Chat Engine:", response.text)

#Api route to get a new token for a valid user, returns the token and userID
@api_app.route('/api/login', methods=['POST'])
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

#Api to update the user data, return a success message
@api_app.route('/api/users/<userID>', methods=['PUT'])
@cross_origin(supports_credentials=True)
@check_token
def update_user(userID):
    try:
        data = request.json
        db.child('users').child(userID).update(data)
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to Get the user data, return a success message
@api_app.route('/api/users/<userID>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_user(userID):
    try:
        userData = db.child('users').child(userID).get().val()
        if userData:
           userData.pop('password', None)
           return jsonify(userData), 200
        else:
            return jsonify({'message': 'User not found'}), 404
    except Exception as e:
        # Log the exception for debugging purposes
        logger.error(f'Error in get_user: {str(e)}')
        return jsonify({'error': 'An internal error occurred'}), 500

#Api to delete user account
@api_app.route('/api/users/<userID>', methods=['DELETE'])
@check_token
def delete_user(userID):
    try:
        db.child('users').document(userID).delete()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to upload a profile picture for the user, updates picture if already exists
@api_app.route('/api/users/picture/<userID>', methods=['POST'])
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
        if user_doc.val() is None:
            return jsonify({'error': 'User not found'}), 404

        filename = secure_filename(file.filename)

        # Define the path where the file will be uploaded
        path = "images/" + userID
        pb_storage.child(path).put(file)

        # Make the blob publicly accessible
        url = pb_storage.child(path).get_url(request.headers.get('Authorization'))
        # Update the user's document in Firestore with the picture URL
        user_doc_dict =  user_doc.val()
        user_doc_dict['picture_url'] = url
        db.child('users').child(userID).remove()
        db.child('users').child(userID).set(user_doc_dict)

        return jsonify({'message': 'Picture uploaded successfully', 'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
#Api to get the url for the picture from the user data
@api_app.route('/api/users/picture/<userID>', methods=['GET'])
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


#Api to get all the events that exist
@api_app.route('/api/events/all', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_all_events():
    try:
        events = db.child("events").get().val()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to get an event by event ID
@api_app.route('/api/events/<int:event_id>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_event(event_id):
    try:
        # Implement logic to retrieve a specific event
        event = db.child("events").child(event_id).get().val()
        if event is not None:
            return jsonify(event)
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


#Api to get an event by event ID List
@api_app.route('/api/events/eventIDs', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_event_with_IDs():
    try:
        events = {}
        eventIDList = request.json.get('eventIDList')
        for eventID in eventIDList:
        # Implement logic to retrieve a specific event
            
            event = db.child("events").child(eventID).get().val()
            if event is not None:
                events[eventID] = (event)
            else:
                continue
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to get all the user's events from all different categories
@api_app.route('/api/events/user/all/<userID>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_user_events(userID):
    try:
        # Implement logic to retrieve a specific event
        userData = db.child("users").child(userID).get().val()
        if userData is not None:
            userData['events_interested'].remove("none")
            userData['events_enrolled'].remove("none")
            userData['events_created'].remove("none")
            events_interested_ids = userData['events_interested']
            events_enrolled_ids = userData['events_enrolled']
            events_created_ids = userData['events_created']
            all_events_id_with_duplicates = events_interested_ids + events_enrolled_ids + events_created_ids
            all_events_id = []
            for event in all_events_id_with_duplicates:
                if event not in all_events_id:
                    all_events_id.append(event)
            interested_events = []
            enrolled_events = []
            created_events = []
            all_events = []
            for id in events_interested_ids:
                event = db.child("events").child(id).get().val()
                interested_events.append(event)
            for id in events_enrolled_ids:
                event = db.child("events").child(id).get().val()
                enrolled_events.append(event)
            for id in events_created_ids:
                event = db.child("events").child(id).get().val()
                created_events.append(event)
            for id in all_events_id:
                event = db.child("events").child(id).get().val()
                all_events.append(event)
            all_categories = {
                'interested_events' : interested_events, 'enrolled_events' : enrolled_events, 'created_events' : created_events, 'all_events' : all_events
            }
            return jsonify(all_categories)
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to get all the events the user is interested in
@api_app.route('/api/events/user/interested/<userID>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_interested_events(userID):
    try:
        # Implement logic to retrieve a specific event
        userData = db.child("users").child(userID).get().val()
        if userData is not None:
            events_interested_ids = userData['events_interested'].strip(",").split(",")
            interested_events = []
            for id in events_interested_ids:
                event = db.child("events").child(id).get().val()
                interested_events.append(event)
            return jsonify(interested_events)
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to create an event
@api_app.route('/api/events/createEvent/<userID>', methods=['POST'])
@check_token
@cross_origin(supports_credentials=True)
def create_event(userID):
    try:
        data = request.json
        required_fields = ['event_name', 'event_type', 'event_date', 'event_time', 'event_details', 'event_location', 'price', 'numOfParticipants', 'event_target_audience']
        if not all(data.get(field) for field in required_fields):
            return jsonify({'message': 'Error missing fields'}), 400

        # Generate a unique ID for the new event
        uniqueID = randint(10000, 99999)
        while db.child("events").child(uniqueID).get().val() is not None:
            uniqueID = randint(10000, 99999)

        # Prepare the new event data
        new_event_data = {
            "event_name": data.get('event_name'),
            "type": data.get('event_type'),
            "date": data.get('event_date'),
            "time": data.get('event_time'),
            "description": data.get('event_details'),
            "location": data.get('event_location'),
            "attendees": [userID],  # Assuming attendees is a list
            "price": data.get('price'),
            "numOfParticipants": data.get('numOfParticipants'),
            "target_audience": data.get('event_target_audience'),
            "images": []  # Assuming this will be handled later
        }

        # Save the new event
        db.child("events").child(uniqueID).set(new_event_data)

        # Update user data with the new event
        user_data = db.child("users").child(userID).get().val() or {}
        user_data['events_created'].append(uniqueID)
        user_data['events_interested'].append(uniqueID)
        user_data['events_enrolled'].append(uniqueID)


        db.child('users').child(userID).update(user_data)

        return jsonify({'message': 'Event created successfully', 'eventID': uniqueID}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
#Api to update the event data
@api_app.route('/api/events/<int:event_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
@check_token
def update_event(event_id):
    try:
        data = request.json
        event = db.child("events").child(event_id).get().val()
        newEventData = json.dumps({
          "event_name" : data.get('event_name'),
          "type" : data.get('event_type'),
          "date" : data.get('event_date'),
          "time" : data.get('event_time'),
          "description" : data.get('event_details'),
          "location" : data.get('event_location'),
          "attendees" : event.get("attendees"),
          "price" : data.get('price'),
          "numOfParticipants" : data.get('numOfParticipants'),
          "target_audience" : data.get('event_target_audience'),
          "images" : ""
        })
        if event is not None:
            db.child("events").child(event_id).update(data)
            return jsonify(event)
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to delete an event
@api_app.route('/api/events/<int:event_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
@check_token
def delete_event(event_id):
    try:
        data = request.json
        # add logic to remove deleted event from users 
        event = db.child("events").child(event_id).get().val()
        if event is not None:
            db.child("events").child(event_id).remove()
            return jsonify({'message': 'Event Deleted'})
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api to upload a picture for the event
@api_app.route('/api/picture/event/<eventID>', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def upload_picture_event(eventID):
    try:
        # Check if 'picture' is present in the request files
        if 'image' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['image']
        # Check if the filename is not empty
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Validate that the user ID is provided
        if not eventID:
            return jsonify({'error': 'Event ID is missing'}), 400

        # Check if the user exists in Firestore
        event_doc = db.child('users').child(eventID).get()
        if event_doc.val() is None:
            return jsonify({'error': 'Event not found'}), 404

        filename = secure_filename(file.filename)

        # Define the path where the file will be uploaded
        path = "images/" + eventID + "/" + filename
        pb_storage.child(path).put(file)

        # Make the blob publicly accessible
        url = pb_storage.child(path).get_url(request.headers.get('Authorization'))
        # Update the user's document in Firestore with the picture URL
        event_doc_dict =  event_doc.val()
        event_doc_dict['images'].append(url)
        db.child('events').child(eventID).remove()
        db.child('events').child(eventID).set(event_doc_dict)

        return jsonify({'message': 'Picture uploaded successfully', 'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api route to get event pictures
@api_app.route('/api/events/picture/<eventID>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_picture_event(eventID):
    try:
        event_doc = db.child('events').child(eventID).get()
        if event_doc.val() is None:
            return jsonify({'error': 'Event not found'}), 404

        event_data = event_doc.val()
        picture_url = event_data.get('images')
        return jsonify({'message': 'Picture found successfully', 'url': picture_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Api route to get search results
@cross_origin(supports_credentials=True)
@check_token
@api_app.route('/api/search', methods=['GET'])
def search():
    try:
        query = request.args.get('query', '').lower()

        # Fetch data from Firebase
        all_data = db.child("events").get().val()

        # Convert the values of the OrderedDict into a list of dictionaries
        event_list = list(all_data.values())

        # Extract filter parameters from the request
        event_type_filter = request.args.get('type')
        location_filter = request.args.get('location')
        price_min = request.args.get('price_min')
        price_max = request.args.get('price_max')

        # Apply filters to narrow down the search results
        filtered_results = event_list

        if event_type_filter:
            filtered_results = [item for item in filtered_results if item.get('type') == event_type_filter]

        if location_filter:
            filtered_results = [item for item in filtered_results if item.get('location') == location_filter]

        if price_min or price_max:
            filtered_results = [item for item in filtered_results if price_min <= float(item.get('price', 0)) <= price_max]

        # Apply text search query in "event_name" and "description" fields
        search_results = [item for item in filtered_results if query in item.get('event_name', '').lower() or query in item.get('description', '').lower()]

        return jsonify(search_results), 200

    except Exception as e:
        return jsonify({'message': 'An error occurred: ' + str(e)}), 500
