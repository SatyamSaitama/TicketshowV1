from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    place = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    shows = db.relationship('ShowBooking', backref='venues')
    hosts = db.relationship('User', backref="arena", secondary="association")


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    bookings = db.relationship('Booking', backref='user')
    role = db.Column(db.String(50), default='user', nullable=False)

    def get_role(self):
        return self.role


class Association(db.Model):
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class ShowBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    show_name = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.String(10), nullable=False)
    timing = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tags = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    yt_link = db.Column(db.String(50), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=True)
    seat_available = db.relationship('SeatAvailable', backref='show_booking', uselist=False)


class SeatAvailable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('show_booking.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=True)
    available_seats = db.Column(db.Integer, nullable=False, default=0)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False,default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('show_booking.id'), nullable=False)
    seat_booked = db.Column(db.Integer, db.ForeignKey('seat_available.id'), nullable=False)


