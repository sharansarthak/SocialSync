from flask import Blueprint, jsonify, request, current_app
import json
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth
from werkzeug.utils import secure_filename
from functools import wraps
from app.helpers import is_strong_password, is_valid_email
from random import randint, randrange
from collections import OrderedDict


api_app = Blueprint('api_app', __name__)

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
@api_app.route('/api/signup', methods=['POST'] )
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    data['events_interested'] = ""
    data['events_created'] = ""
    data['events_enrolled'] = ""
    data['description'] = ""
    age = data.get('age') 
    data['rating'] = "5"

    print(data)
    if email is None or password is None or name is None or age is None:
        return {'message': 'Error missing email or password'},400

    try:
        user = pyrebase_auth.create_user_with_email_and_password(
            email=email,
            password=password
        )

        localID = user.get("localId")
        db.child("users").child(localID).set(data)
        return {'{user}'},200
    except Exception as e:
        return {'message': str(e)},400
    
#Api route to get a new token for a valid user
@api_app.route('/api/login', methods=['GET'])
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

@api_app.route('/api/users/<userID>', methods=['PUT'])
@check_token
def update_user(userID):
    try:
        data = request.json
        print(data)
        db.child('users').child(userID).update(data)
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/users/<userID>', methods=['DELETE'])
@check_token
def delete_user(userID):
    try:
        db.child('users').document(userID).delete()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_app.route('/api/users/picture/<userID>', methods=['POST'])
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
    
@api_app.route('/api/users/picture/<userID>', methods=['GET'])
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


api_app.route('/api/events/all', methods=['GET'])
@check_token
def get_all_events():
    try:
        events = db.child("events").get().val()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

api_app.route('/api/events/<int:event_id>', methods=['GET'])
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

# api_app.route('/api/events/search/<search_term>', methods=['GET'])
# def search_events(search_term):
#     try:
#         # Implement logic to retrieve all events based on search
#         return jsonify(events)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

api_app.route('/api/events/user/all/<userID>', methods=['GET'])
def get_user_events(userID):
    try:
        # Implement logic to retrieve a specific event
        userData = db.child("users").child(userID).get().val()
        if userData is not None:
            events_interested_ids = userData['events_interested'].strip(",").split(",")
            events_enrolled_ids = userData['events_enrolled'].strip(",").split(",")
            events_created_ids = userData['events_created'].strip(",").split(",")
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

api_app.route('/api/events/user/interested/<userID>', methods=['GET'])
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

@api_app.route('/api/events/createEvent/<userID>', methods=['POST'])
@check_token
def create_event(userID):
    try:
        data = request.json
        event_name = data.get('event_name')
        type = data.get('event_type')
        date = data.get('event_date')
        time = data.get('event_time')
        description = data.get('event_details')
        location = data.get('event_location')
        attendees = userID
        price = data.get('price')
        numOfParticipants = data.get('numOfParticipants')
        target_audience = data.get('event_target_audience')
        images = ""

        newEventData = json.dumps({
          "event_name" : data.get('event_name'),
          "type" : data.get('event_type'),
          "date" : data.get('event_date'),
          "time" : data.get('event_time'),
          "description" : data.get('event_details'),
          "location" : data.get('event_location'),
          "attendees" : userID,
          "price" : data.get('price'),
          "numOfParticipants" : data.get('numOfParticipants'),
          "target_audience" : data.get('event_target_audience'),
          "images" : ""
        })

        if (event_name or type or date or time or description or location or attendees or target_audience or price or numOfParticipants) is (None or ""):
            return {'message': 'Error missing fields'},400

        print(newEventData)

        uniqueID = randint(10000, 99999)
        eventData = db.child("event").child(uniqueID).get()
        print(eventData.val())
        while eventData.val() is not None:
            eventData = db.child("event").child(uniqueID).get()
            uniqueID = randint(10000, 99999)
        db.child("events").child(uniqueID).set(data)
        print(userID)
        userData =db.child("users").child(userID).get().val()
        print(userData)
        userData['events_created'] = userData['events_created'] + str(uniqueID) + ","
        userData['events_interested'] = userData['events_interested'] + str(uniqueID) + ","
        userData['events_enrolled'] = userData['events_enrolled'] + str(uniqueID) + ","
        userDataJson = json.loads(json.dumps(userData))
        print(userData)
        print(userDataJson)
        db.child('users').child(userID).update(userDataJson)

        return jsonify({'message': 'Event created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@api_app.route('/api/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    try:
        data = request.json
        event = db.child("events").child(event_id).get().val()
        if event is not None:
            db.child("events").child(event_id).update(data)
            return jsonify(event)
        else:
            return jsonify({'message': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/events/<int:event_id>', methods=['DELETE'])
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
