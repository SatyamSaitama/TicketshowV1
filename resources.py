from flask_restful import Resource, reqparse, Api, fields, marshal, abort

from model import *

api = Api()

venue_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'place': fields.String,
    'location': fields.String,
    'capacity': fields.Integer
}

show_booking_fields = {
    'id': fields.Integer,
    'show_name': fields.String,
    'rating': fields.String,
    'yt_link': fields.String,
    'timing': fields.DateTime,
    'tags': fields.String,
    'price': fields.Float,
}


class VenueResource(Resource):

    def get(self, id=None):
        if id:
            venue = Venue.query.get(id)
            if not venue:
                abort(404, message='Venue not found')
            return marshal(venue, venue_fields)
        else:
            venues = Venue.query.all()
            return [marshal(venue, venue_fields) for venue in venues]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True)
        parser.add_argument('place', required=True)
        parser.add_argument('location', required=True)
        parser.add_argument('capacity', required=True, type=int)
        data = parser.parse_args()
        venue = Venue(name=data['name'], place=data['place'], location=data['location'], capacity=data['capacity'])
        db.session.add(venue)
        db.session.commit()
        return marshal(venue, venue_fields), 201

    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('name')
        parser.add_argument('place')
        parser.add_argument('location')
        parser.add_argument('capacity', type=int)
        data = parser.parse_args()
        venue = Venue.query.get(id)
        if not venue:
            abort(404, message='Venue not found')
        if data['name']:
            venue.name = data['name']
        if data['place']:
            venue.place = data['place']
        if data['location']:
            venue.location = data['location']
        if data['capacity']:
            venue.capacity = data['capacity']
        db.session.commit()
        return marshal(venue, venue_fields)

    def delete(self, id):
        venue = Venue.query.get(id)
        if not venue:
            abort(404, message='Venue not found')
        for x in venue.shows:
            booking = Booking.query.filter_by(show_id=x.id).all()
            for y in booking:
                db.session.delete(y)

            db.session.delete(x.seat_available)
            db.session.delete(x)
        db.session.delete(venue)
        db.session.commit()
        return '', 204


class ShowBookingResource(Resource):
    def get(self, id=None):
        if id:
            show = ShowBooking.query.get(id)
            if not show:
                abort(404, message='Show not found')
            return marshal(show, show_booking_fields)
        else:
            shows = ShowBooking.query.all()
            return [marshal(show, show_booking_fields) for show in shows]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('show_name', required=True)
        parser.add_argument('rating', required=True)
        parser.add_argument('yt_link', required=True)
        parser.add_argument('timing', required=True, type=lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'))
        parser.add_argument('tags', required=True)
        parser.add_argument('price', required=True, type=float)
        parser.add_argument('id', required=True, type=int)
        data = parser.parse_args()
        venue = Venue.query.get(data['id'])
        if not venue:
            abort(404, message='Venue not found')
        show = ShowBooking(show_name=data['show_name'], rating=data['rating'], timing=data['timing'],
                           tags=data['tags'], price=data['price'], venue_id=data['id'], yt_link=data['yt_link'])
        seat_available = SeatAvailable(available_seats=100, date=data['timing'], show_booking=show,venue_id=id)
        db.session.add(show)
        db.session.add(seat_available)
        db.session.commit()
        return marshal(show, show_booking_fields), 201

    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('show_name')
        parser.add_argument('rating')
        parser.add_argument('yt_link')
        parser.add_argument('timing', type=lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'))
        parser.add_argument('tags')
        parser.add_argument('price', type=float)
        data = parser.parse_args()
        show = ShowBooking.query.get(id)
        if not show:
            abort(404, message='Show not found')
        if data['show_name']:
            show.show_name = data['show_name']
        if data['rating']:
            show.rating = data['rating']
        if data['timing']:
            show.timing = data['timing']
            show.seat_available.date = data['timing']
        if data['tags']:
            show.tags = data['tags']
        if data['price']:
            show.price = data['price']
        if data['yt_link']:
            show.yt_link = data['yt_link']
        db.session.commit()
        return marshal(show, show_booking_fields)

    def delete(self, id):
        show = ShowBooking.query.get(id)

        if not show:
            abort(404, message='Show not found')
        booking = Booking.query.filter_by(show_id=show.id).all()
        for x in booking:
            db.session.delete(x)
        db.session.delete(show.seat_available)
        db.session.delete(show)
        db.session.commit()
        return '', 204


api.add_resource(VenueResource, '/api/venues', '/api/venues/<int:id>')
api.add_resource(ShowBookingResource, '/api/shows', '/api/shows/<int:id>')
