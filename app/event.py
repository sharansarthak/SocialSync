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
event = Blueprint('event', __name__)

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

@event.route('/api/events/all', methods=['GET'])
@check_token
def get_all_events():
    try:
        events = db.child("events").get().val()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event.route('/api/events/<int:event_id>', methods=['GET'])
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

# @event.route('/api/events/search/<search_term>', methods=['GET'])
# def search_events(search_term):
#     try:
#         # Implement logic to retrieve all events based on search
#         return jsonify(events)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@event.route('/api/events/user/all/<userID>', methods=['GET'])
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

@event.route('/api/events/user/interested/<userID>', methods=['GET'])
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

@event.route('/api/events/createEvent/<userID>', methods=['POST'])
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
        target_audience = data.get('event_target_audience')

        if (event_name or type or date or time or description or location or attendees or target_audience) is (None or ""):
            return {'message': 'Error missing fields'},400

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
    

@event.route('/api/events/<int:event_id>', methods=['PUT'])
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

@event.route('/api/events/<int:event_id>', methods=['DELETE'])
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
