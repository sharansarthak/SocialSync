import datetime
from http.client import BAD_REQUEST
import logging
import traceback
from uuid import uuid4
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

        # Data Validation
        if not all([email, password, name, age, description]):
            return jsonify({'message': 'Error: Missing email, password, name, age, or description'}), 400

        # Email format, password strength, and age validation logic here

        user = pyrebase_auth.create_user_with_email_and_password(email, password)
        localID = user.get("localId")

        user_data = {
            'name': name,
            'email': email,
            'age': age,
            'description': description,
            'events_interested': [],
            'events_created': [],
            'events_enrolled': [],
            'rating': [5] 
        }

        db.child("users").child(localID).set(user_data)
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

# Add user rating
@api_app.route('/api/users/add/rating/', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def add_user_rating():
    try:
        data = request.json
        userID = data.get("userID")
        rating = data.get("rating")

        if not userID or rating is None:
            return jsonify({"message": 'Error: Missing userID or rating'}), 400

        user_ref = db.child('users').child(userID)
        user_data = user_ref.get().val()

        if user_data is None:
            return jsonify({"message": 'User not found'}), 404

        current_rating = user_data.get('rating', [])
        current_rating.append(rating)
        user_ref.update({'rating': current_rating})

        return jsonify({'message': 'Rating added successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to add rating', 'error': str(e)}), 500


#Api to get user Rating
@api_app.route('/api/users/rating/<userID>', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_user_rating(userID):
    try:
        user_data = db.child('users').child(userID).get().val()
        if user_data is None:
            return jsonify({"message": 'User not found'}), 404

        rating = user_data.get('rating', [])
        return jsonify({'rating': rating}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to get rating', 'error': str(e)}), 500


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
@api_app.route('/api/users/picture/<userID>', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def upload_picture(userID):
    try:
        # Check if 'image' is present in the request files
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

        # Secure the filename and construct the path for storage
        filename = secure_filename(file.filename)
        path = os.path.join("images", userID, filename)
        pb_storage.child(path).put(file)

        # Retrieve the public URL of the uploaded file
        url = pb_storage.child(path).get_url()

        # Update the user's document in Firestore with the picture URL
        db.child('users').child(userID).update({'picture_url': url})

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
        url = pb_storage.child("images/"+userID).get_url(None)
        # Update the user's document in Firestore with the picture URL
        if url is None:
            return jsonify({'message': 'Picture not found'})
        return jsonify({'message': 'Picture found successfully', 'url': url})
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
@api_app.route('/api/events/<event_id>', methods=['GET'])
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
@api_app.route('/api/events/eventIDs', methods=['POST'])
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
        userData = db.child("users").child(userID).get().val()
        if userData is None:
            return jsonify({'message': 'User not found'}), 404

        # Fetch events directly from the lists
        events_interested_ids = userData.get('events_interested', [])
        events_enrolled_ids = userData.get('events_enrolled', [])
        events_created_ids = userData.get('events_created', [])

        def fetch_events(event_ids):
            return [db.child("events").child(eid).get().val() for eid in event_ids if eid]

        all_events_id = set(events_interested_ids + events_enrolled_ids + events_created_ids)
        interested_events = fetch_events(events_interested_ids)
        enrolled_events = fetch_events(events_enrolled_ids)
        created_events = fetch_events(events_created_ids)
        all_events = fetch_events(all_events_id)

        all_categories = {
            'interested_events': interested_events, 
            'enrolled_events': enrolled_events, 
            'created_events': created_events, 
            'all_events': all_events
        }
        return jsonify(all_categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



#Api to get all the events the user is interested in
@api_app.route('/api/users/<userID>/events/interested', methods=['GET'])
@cross_origin(supports_credentials=True)
@check_token
def get_user_interested_events(userID):
    try:
        # Fetch the user's data
        user_data = db.child("users").child(userID).get().val()
        if user_data is None:
            return jsonify({'message': 'User not found'}), 404

        # Retrieve the list of interested event IDs
        interested_event_ids = user_data.get('events_interested', [])

        # Fetch details for each interested event
        interested_events = []
        for event_id in interested_event_ids:
            event_data = db.child("events").child(event_id).get().val()
            if event_data:
                interested_events.append(event_data)

        return jsonify({'interested_events': interested_events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


#Api to create an event
@api_app.route('/api/events/createEvent/<userID>', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def create_event(userID):
    try:
        data = request.json
        required_fields = ['event_name', 'event_type', 'event_date', 'event_time', 
                           'event_details', 'event_location', 'price', 'numOfParticipants', 
                           'event_target_audience']

        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in data or data.get(field) is None]
        if missing_fields:
            return jsonify({'message': f'Error: Missing fields - {", ".join(missing_fields)}'}), 400

        # Generate a unique ID for the new event using UUID
        uniqueID = str(uuid4())

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
        user_data.setdefault('events_created', []).append(uniqueID)
        db.child('users').child(userID).update(user_data)

        return jsonify({'message': 'Event created successfully', 'eventID': uniqueID}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
#Api to update the event data
@api_app.route('/api/events/<event_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
@check_token
def update_event(event_id):
    try:
        data = request.json
        event = db.child("events").child(event_id).get().val()

        if event is None:
            return jsonify({'message': 'Event not found'}), 404

        # Prepare the new event data
        updated_event_data = {
            "event_name": data.get('event_name', event.get('event_name')),
            "type": data.get('event_type', event.get('type')),
            "date": data.get('event_date', event.get('date')),
            "time": data.get('event_time', event.get('time')),
            "description": data.get('event_details', event.get('description')),
            "location": data.get('event_location', event.get('location')),
            "price": data.get('price', event.get('price')),
            "numOfParticipants": data.get('numOfParticipants', event.get('numOfParticipants')),
            "target_audience": data.get('event_target_audience', event.get('target_audience')),
            # Assuming 'images' is a field in your event data
            "images": data.get('images', event.get('images', []))
        }

        db.child("events").child(event_id).update(updated_event_data)
        return jsonify(updated_event_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Add events to interested for user
@api_app.route('/api/users/<userID>/interests/add', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def add_event_to_interested(userID):
    try:
        data = request.json
        event_id = data.get('event_id')
        
        if not event_id:
            return jsonify({'message': 'Error: Missing event_id'}), 400

        # Check if the event exists
        event_data = db.child("events").child(event_id).get().val()
        if event_data is None:
            return jsonify({'message': 'Event not found'}), 404

        # Fetch the user's current data
        user_data = db.child("users").child(userID).get().val()
        if user_data is None:
            return jsonify({'message': 'User not found'}), 404

        # Update user's events_interested and events_enrolled lists
        for list_name in ['events_interested', 'events_enrolled']:
            events_list = user_data.get(list_name, [])
            if event_id not in events_list:
                events_list.append(event_id)
                user_data[list_name] = events_list

        db.child('users').child(userID).update(user_data)

        # Add user to event's attendees list
        attendees = event_data.get('attendees', [])
        if userID not in attendees:
            attendees.append(userID)
            db.child("events").child(event_id).update({'attendees': attendees})

        return jsonify({'message': 'Event added to interested and enrolled lists'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#API to unenroll from an event
@api_app.route('/api/users/<userID>/events/unenroll', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def unenroll_from_event(userID):
    try:
        data = request.json
        event_id = data.get('event_id')
        
        if not event_id:
            return jsonify({'message': 'Error: Missing event_id'}), 400

        # Check if the event exists
        event_data = db.child("events").child(event_id).get().val()
        if event_data is None:
            return jsonify({'message': 'Event not found'}), 404

        # Fetch the user's current data
        user_data = db.child("users").child(userID).get().val()
        if user_data is None:
            return jsonify({'message': 'User not found'}), 404

        # Update logic for both events_enrolled and events_interested lists
        updated = False
        for list_name in ['events_enrolled', 'events_interested']:
            events_list = user_data.get(list_name, [])
            if event_id in events_list:
                events_list.remove(event_id)
                user_data[list_name] = events_list
                updated = True

        if updated:
            db.child('users').child(userID).update(user_data)

        # Optionally, remove the user from the event's attendees list
        if userID in event_data.get('attendees', []):
            attendees = event_data['attendees']
            attendees.remove(userID)
            db.child("events").child(event_id).update({'attendees': attendees})

        return jsonify({'message': 'Successfully unenrolled from and removed interest in the event'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_app.route('/api/event/<event_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
@check_token
def delete_event(event_id):
    try:
        # Check if the event exists
        event = db.child("events").child(event_id).get().val()
        if event is None:
            return jsonify({'message': 'Event not found'}), 404

        # Remove the event from the database
        db.child("events").child(event_id).remove()

        # Retrieve all users
        all_users = db.child("users").get().val()
        if all_users:
            for user_id, user_data in all_users.items():
                updated = False
                # Check and remove event ID from each user's lists
                for field in ['events_interested', 'events_enrolled', 'events_created']:
                    if event_id in user_data.get(field, []):
                        user_data[field].remove(event_id)
                        updated = True
                # Update the user data if any changes were made
                if updated:
                    db.child('users').child(user_id).update(user_data)

        return jsonify({'message': 'Event Deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_app.route('/api/event/picture/<eventID>', methods=['POST'])
@cross_origin(supports_credentials=True)
@check_token
def upload_picture_event(eventID):
    try:
        # Check if files are present in the request
        if 'images' not in request.files:
            return jsonify({'error': 'No files part'}), 400

        files = request.files.getlist('images')

        # Check if there are files selected
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No selected files'}), 400

        # Validate that the event ID is provided
        if not eventID:
            return jsonify({'error': 'Event ID is missing'}), 400

        # Check if the event exists in Firestore
        event_doc = db.child('events').child(eventID).get()
        if event_doc.val() is None:
            return jsonify({'error': 'Event not found'}), 404

        # Process each file
        urls = []
        for file in files:
            # Validate the file type
            if not allowed_file(file.filename):
                continue  # Skip invalid file types

            filename = secure_filename(file.filename)
            path = f"images/events/{eventID}/{filename}"
            pb_storage.child(path).put(file)
            url = pb_storage.child(path).get_url()  # Assuming public URL generation
            urls.append(url)

        if not urls:
            return jsonify({'error': 'No valid images were uploaded'}), 400

        # Update the event's document in Firestore with the picture URLs
        event_doc_dict = event_doc.val()
        event_doc_dict.setdefault('images', []).extend(urls)
        db.child('events').child(eventID).update(event_doc_dict)

        return jsonify({'message': 'Pictures uploaded successfully', 'urls': urls})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    # Function to check if the file is an allowed type (e.g., image)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#Api route to get event pictures
@api_app.route('/api/event/picture/<eventID>', methods=['GET'])
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

from datetime import datetime
from flask import jsonify, request


@cross_origin(supports_credentials=True)
@check_token
@api_app.route('/api/search', methods=['GET'])
def search():
    try:
        query = request.args.get('query', '').lower()
        current_date = datetime.now()

        # Fetch data from Firebase
        all_data = db.child("events").get().val()

        # Check if data is None
        if not all_data:
            return jsonify({'message': 'No events found'}), 404

        # Convert the values into a list of dictionaries
        event_list = list(all_data.values())

        # Extract and parse filter parameters from the request
        event_type_filter = request.args.get('type')
        target_audience_filter = request.args.get('target_audience')
        location_filter = request.args.get('location')
        price_min = request.args.get('price_min')
        price_max = request.args.get('price_max')

        # Function to safely parse dates in different formats
        def safe_parse_date(date_str):
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):  # Add more formats here if needed
                try:
                    return datetime.strptime(date_str, fmt)
                except (ValueError, TypeError):
                    continue
            return None

        date_min = safe_parse_date(request.args.get('date_min'))
        date_max = safe_parse_date(request.args.get('date_max'))

        # Apply filters
        filtered_results = []
        for item in event_list:
            # Text check in name, description, and location
            text_check = any(query in item.get(field, '').lower() for field in ['event_name', 'description', 'location'])

            # Exact match checks for type and target audience
            type_check = item.get('type') == event_type_filter if event_type_filter else True
            audience_check = item.get('target_audience') == target_audience_filter if target_audience_filter else True

            # Price range check
            price = float(item.get('price', 0))
            price_check = (price_min <= price if price_min else True) and (price <= price_max if price_max else True)

            # Date range check, ensuring event dates are in the future
            event_date = safe_parse_date(item.get('date'))
            date_check = event_date and event_date >= current_date
            if date_min:
                date_check = date_check and event_date >= date_min
            if date_max:
                date_check = date_check and event_date <= date_max

            if text_check and type_check and audience_check and price_check and date_check:
                filtered_results.append(item)

        return jsonify(filtered_results), 200

    except Exception as e:
        return jsonify({'message': 'An error occurred: ' + str(e)}), 500
