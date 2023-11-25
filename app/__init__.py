from flask import Flask
from .auth import auth
from .event import event

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    app.register_blueprint(auth)
    app.register_blueprint(event)

    return app
