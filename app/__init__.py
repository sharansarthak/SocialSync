from flask import Flask
from flask_cors import CORS, cross_origin
from .authentication import authentication
from .event import event
from .test import test
import os
import base64
import firebase_admin
import pyrebase
import json
from firebase_admin import credentials, auth
from flask import Flask, request
from functools import wraps


def create_app():
    app = Flask(__name__)
    CORS(app, support_credentials=True)
    app.register_blueprint(authentication)
    app.register_blueprint(event)
    app.register_blueprint(test)

    return app
