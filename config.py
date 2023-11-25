import os

class Config:
    DEBUG = True
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
