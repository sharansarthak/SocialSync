from flask import Blueprint, jsonify

event = Blueprint('event', __name__)

@event.route('/events', methods=['GET'])
def list_events():
    # Logic to list events
    return jsonify({"events": []}), 200
