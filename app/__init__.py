from flask import Flask
from .auth import auth
from .event import event
from .test import test
import os
import json
import base64
import firebase_admin
from firebase_admin import credentials

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Decode the Base64 string
    encoded_service_account = os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')
    decoded_service_account = base64.b64decode(encoded_service_account)

    # Load it as JSON
    service_account_info = json.loads(decoded_service_account)

    # Initialize Firebase
    firebase_cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(firebase_cred, {
        'storageBucket': 'socialsync-35f38.appspot.com'
    })
    print("Firebase Initialized")  # Confirm initialization

    app.register_blueprint(auth)
    app.register_blueprint(event)
    app.register_blueprint(test)

    return app
