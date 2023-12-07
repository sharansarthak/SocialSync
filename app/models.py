class Event:
    def __init__(self, event_id, event_name, date, time, description, location, type, target_audience, price, numOfParticipants, images, attendees):
        self.event_id = event_id
        self.event_name = event_name
        self.date = date
        self.time = time
        self.description = description
        self.location = location
        self.type = type
        self.target_audience = target_audience
        self.price = price
        self.numOfParticipants = numOfParticipants
        self.images = images
        self.attendees = attendees
class User:
    def __init__(self, user_id, name, email, picture_url, events_created, events_interested, events_enrolled):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.picture_url = picture_url
        self.events_created = events_created
        self.events_interested = events_interested
        self.events_enrolled = events_enrolled