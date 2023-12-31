from flask import Flask
from flask_cors import CORS, cross_origin
from .api_app import api_app
import os
import base64
import firebase_admin
import pyrebase
import json
from firebase_admin import credentials, auth
from flask import Flask, request
from functools import wraps
from flask_cors import CORS, cross_origin


def create_app():
    app = Flask(__name__)
    CORS(app, support_credentials=True)

    app.register_blueprint(api_app)

    return app
