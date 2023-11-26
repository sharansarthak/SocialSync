# models.py

class User:
    def __init__(self, user_id, username, email, profile_picture=None, interests=None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.profile_picture = profile_picture
        self.interests = interests if interests is not None else []

    def to_dict(self):
        return vars(self)

class Event:
    def __init__(self, event_id, title, description, created_by, start_time, end_time, participants=None, tags=None):
        self.event_id = event_id
        self.title = title
        self.description = description
        self.created_by = created_by
        self.start_time = start_time
        self.end_time = end_time
        self.participants = participants if participants is not None else []
        self.tags = tags if tags is not None else []

    def to_dict(self):
        return vars(self)

class Message:
    def __init__(self, message_id, sender_id, event_id, timestamp, content):
        self.message_id = message_id
        self.sender_id = sender_id
        self.event_id = event_id
        self.timestamp = timestamp
        self.content = content

    def to_dict(self):
        return vars(self)
