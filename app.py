import csv
import os
from collections import OrderedDict
import numpy as np
import pytz
from flask import *
from flask import redirect, url_for
from flask_cors import CORS
from flask_login import *
from flask_login import current_user
from flask_swagger_ui import get_swaggerui_blueprint
from matplotlib import pyplot as plt
from model import *

app = Flask(__name__)
print(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///venue.sqlite3"
CORS(app)
db.init_app(app)
app.secret_key = '123'

SWAGGER_URL = '/api/docs'
API_URL = '/static/api.yml'

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "My API"
    }
)

app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

login_manager = LoginManager()
login_manager.init_app(app)
app.app_context().push()


# signup
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pswd']
        user_x = User.query.filter_by(email=email).first()
        if user_x and user_x.password == password:
            # login the user
            login_user(user_x)
            flash('You have been logged in!', 'success')
            return redirect('/location')
        else:
            return render_template('login.html', shaky_cat=True)

    return render_template('login.html')


# logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'success')
    return redirect(url_for('index'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        name = request.form['username']
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            ans = "Email already exists."
            return render_template('signup.html', ans=ans)

        password = request.form['password']
        c_password = request.form['confirm_password']
        if password != c_password:
            ans = "Password does not match"
            return render_template('signup.html', ans=ans)
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template('signup.html')


#############################################################user_x homepage
@app.route('/user/<int:id>', methods=['GET', 'POST'])
@login_required
def user(id):
    tz = pytz.timezone('Asia/Kolkata')
    india_time = datetime.now(tz)
    shows = ShowBooking.query.filter(ShowBooking.timing > india_time).all()
    venues = Venue.query.all()
    bookings = Booking.query.all()

    ratings = {}
    for booking in bookings:
        if booking.show_id not in ratings:
            ratings[booking.show_id] = []
        ratings[booking.show_id].append(booking.rating)

    for show_id in ratings:
        avg_rating = round(sum(ratings[show_id]) / len(ratings[show_id]), 1)

        ratings[show_id] = avg_rating

    if 'selected_venue' in session:
        selected_venue = session['selected_venue']
        selected_shows = [x for x in shows if x.venues.location == selected_venue]
        venues = Venue.query.filter_by(location=selected_venue).all()
    else:
        return render_template('profile.html', shows=shows, id=id, venues=venues, ratings=ratings, )
    return render_template('profile.html', shows=shows, id=id, location=selected_venue, venues=venues, ratings=ratings,
                           s=selected_shows)


###########################################################BOOKING
@app.route("/book/<int:id>", methods=['GET', 'POST'])
def book(id):
    bookings = Booking.query.all()
    ratings = {}
    for booking in bookings:
        if booking.show_id not in ratings:
            ratings[booking.show_id] = []
        ratings[booking.show_id].append(booking.rating)

    for show_id in ratings:
        avg_rating = round(sum(ratings[show_id]) / len(ratings[show_id]), 1)

        ratings[show_id] = avg_rating

    current_time = datetime.now()
    global booking_obj
    show = ShowBooking.query.get(id)
    timing_str = show.timing

    if (show.timing - current_time).seconds < 21600:

        top_5_bookings = Booking.query.order_by(Booking.seat_booked.desc()).limit(5).all()
        print(top_5_bookings)
        if top_5_bookings is not None:
            for x in top_5_bookings:
                obj = ShowBooking.query.get(x.show_id)
                if (obj.timing - current_time).seconds < 21600:
                    obj.price += 10

    seat_avail = SeatAvailable.query.filter_by(show_id=id, date=show.timing).first()
    print(show, seat_avail, id, show.timing)

    if current_user.is_authenticated:
        booking_obj = Booking.query.filter_by(user_id=current_user.id, show_id=show.id).first()
        if booking_obj is None:
            booking_obj = Booking(user_id=current_user.id, show_id=show.id, seat_booked=0)
            db.session.add(booking_obj)
            db.session.commit()

    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        if seat_avail is not None and seat_avail.available_seats > 0:
            seat_avail.available_seats -= int(request.form['quantity'])
            db.session.commit()

            booking_obj.seat_booked += int(request.form['quantity'])
            db.session.commit()
            print(request.form['quantity'])

            return render_template('payment.html', id=id, show=show, total=request.form['quantity'],
                                   total_value=int(request.form['quantity']) * show.price)
        else:

            new_seat_avail = SeatAvailable(show_id=show.id, date=show.timing, available_seats=show.venues.capacity - 1)
            db.session.add(new_seat_avail)
            db.session.commit()
            new_seat_avail.available_seats -= int(request.form['quantity'])
            db.session.commit()

            booking_obj.seat_booked += int(request.form['quantity'])
            db.session.commit()

            return render_template('payment.html', id=id, show=show, total=request.form['quantity'],
                                   total_value=int(request.form['quantity']) * show.price)

    return render_template('book.html', id=id, show=show, time=current_time, show_time=timing_str, ratings=ratings)


#######################################################


@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        if current_user.get_role() == 'user':
            return redirect(url_for('user', id=current_user.id))
        else:
            return redirect(url_for('admin', id=current_user.id))

    bookings = Booking.query.all()
    ratings = {}
    for booking in bookings:
        if booking.show_id not in ratings:
            ratings[booking.show_id] = []
        ratings[booking.show_id].append(booking.rating)

    for show_id in ratings:
        avg_rating = round(sum(ratings[show_id]) / len(ratings[show_id]), 1)
        ratings[show_id] = avg_rating

    tz = pytz.timezone('Asia/Kolkata')
    india_time = datetime.now(tz)
    shows = ShowBooking.query.filter(ShowBooking.timing > india_time).all()
    return render_template('home.html', shows=shows, ratings=ratings)


#################################################### admin
#################################################### login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pswd']
        user = User.query.filter_by(email=email).first()
        if user is not None:
            id = user.id

        if user and user.password == password:
            # login the user
            login_user(user)
            flash('You have been logged in!', 'success')
            return redirect(f'/admin/{id}')
        else:
            return render_template('Admin_Login.html', shaky_cat=True)

    return render_template('Admin_Login.html')


@app.route('/admin_logout')
@login_required
def admin_logout():
    if current_user.get_role() == 'admin':
        logout_user()
        flash('You have been logged out!', 'success')
        return redirect(url_for('index'))


####################################################signup
@app.route('/admin_signup', methods=['GET', 'POST'])
def Admin_signup():
    if request.method == "POST":
        name = request.form['username']
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            ans = "Email already exists."
            if user.get_role() == "user":
                password = request.form['password']
                c_password = request.form['confirm_password']
                if password != c_password:
                    ans = "Password does not match"
                    return render_template('admin_signup.html', ans=ans)
                user.name = name
                user.email = email
                user.password = password
                user.role = 'admin'
                db.session.commit()
                return redirect('/admin_login')
            return render_template('admin_signup.html', ans=ans)

        password = request.form['password']
        c_password = request.form['confirm_password']
        if password != c_password:
            ans = "Password does not match"
            return render_template('admin_signup.html', ans=ans)
        user = User(name=name, email=email, password=password, role='admin')
        db.session.add(user)
        db.session.commit()
        return redirect('/admin_login')

    return render_template('admin_signup.html')


@app.route('/admin/<int:id>', methods=['GET', 'POST'])
@login_required
def admin(id):
    if current_user.get_role() == 'admin':
        adm = User.query.get(current_user.id)
        venues = adm.arena
        return render_template('admin_profile.html', venues=venues, id=id)
    return render_template("false_login.html")


##########################################
@app.route("/venue", methods=['GET', 'POST'])
@login_required
def create_venue():
    if current_user.get_role() == 'admin':
        if request.method == 'POST':
            d1 = Venue(name=request.form['venue'], place=request.form['place'], location=request.form['location'],
                       capacity=int(request.form['capacity']))
            db.session.add(d1)

            db.session.commit()
            db.session.add(Association(venue_id=d1.id, admin_id=current_user.id))
            db.session.commit()
            return redirect('/set_venue')

        return render_template('create_venue.html')


@app.route('/set_venue', methods=['GET', 'POST'])
@login_required
def set_venue_data():
    if current_user.get_role() == 'admin':
        obj = User.query.get(current_user.id)
        rows = obj.arena
        return render_template('MY_Venues.html', rows=rows)


##############################
@app.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    if current_user.get_role() == 'admin':
        obj = db.session.query(Venue).filter_by(id=id).one()
        for x in obj.shows:
            booking = Booking.query.filter_by(show_id=x.id).all()
            for y in booking:
                db.session.delete(y)

            db.session.delete(x.seat_available)
            db.session.delete(x)
        admin_obj = Association.query.filter_by(venue_id=id).first()
        db.session.delete(admin_obj)

        db.session.delete(obj)
        db.session.commit()

        return redirect("/set_venue")


#########################
@app.route('/edit<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.get_role() == 'admin':
        obj = db.session.query(Venue).filter_by(id=id).one()
        if request.method == 'POST':
            obj.name = request.form['venue']
            obj.place = request.form['place']
            obj.location = request.form['location']
            obj.capacity = request.form['capacity']
            db.session.commit()
            return redirect('/set_venue')
        return render_template('edit.html', obj=obj)


#####################################################################################################
@app.route('/delete_show<int:id>', methods=['GET', 'POST'])
@login_required
def delete_show(id):
    if current_user.get_role() == 'admin':
        obj = db.session.query(ShowBooking).filter_by(id=id).one()
        booking = Booking.query.filter_by(show_id=obj.id).all()
        for x in booking:
            db.session.delete(x)
        db.session.delete(obj.seat_available)
        db.session.delete(obj)
        db.session.commit()
        return redirect(f"/manage_your_show{obj.venue_id}")


#############################################################
#####################################################################################################
@app.route('/delete_admin_show<int:id>', methods=['GET', 'POST'])
@login_required
def delete_admin_show(id):
    if current_user.get_role() == 'admin':
        obj = db.session.query(ShowBooking).filter_by(id=id).one()
        booking = Booking.query.filter_by(show_id=obj.id).all()
        for x in booking:
            db.session.delete(x)
        db.session.delete(obj.seat_available)
        db.session.delete(obj)
        db.session.commit()
        return redirect(f"admin/{current_user.id}")


#############################################################
@app.route("/manage_your_show<int:id>", methods=['GET', 'POST'])
@login_required
def manage_your_show(id):
    if current_user.get_role() == 'admin':
        rows = Venue.query.get(id).shows
        return render_template('show_manager.html', rows=rows, id=id)


@app.route('/book_show<int:id>', methods=['GET', 'POST'])
@login_required
def book_show(id):
    seat = SeatAvailable.query.filter_by(venue_id=id).all()
    total = 0
    for x in seat:
        total = total + x.available_seats

    if current_user.get_role() == 'admin':
        if request.method == 'POST':
            show_name = request.form.get('show_name')
            rating = request.form.get('rating')
            timing_str = request.form.get('timing')
            timing_str = datetime.strptime(timing_str, '%Y-%m-%dT%H:%M')
            tags = request.form.get('tags')
            price = request.form.get('price')
            venue_id = id
            yt_link = request.form.get('video_link')

            booking = ShowBooking(show_name=show_name, rating=rating, timing=timing_str, tags=tags, price=price,
                                  venue_id=venue_id, yt_link=yt_link)
            db.session.add(booking)
            db.session.commit()
            file = request.files['image']
            file.save(f"static/{id}.{show_name}.jpg")
            show_id = booking.id
            date = booking.timing
            available_seats = request.form['capacity']
            session['capacity'] = request.form['capacity']
            seat_available = SeatAvailable(show_id=show_id, date=date, available_seats=available_seats,
                                           venue_id=venue_id)
            db.session.add(seat_available)
            db.session.commit()
            return redirect(f"/manage_your_show{id}")

        return render_template('set_show.html', id=id, venue=Venue.query.get(id), total=total)


@app.route('/edit_show<int:show_id>', methods=['GET', 'POST'])
@login_required
def edit_show(show_id):
    if current_user.get_role() == 'admin':
        show = ShowBooking.query.get(show_id)
        if request.method == 'POST':
            show.show_name = request.form['show_name']
            show.rating = request.form['rating']
            timing_str = request.form.get('timing')
            timing_str = datetime.strptime(timing_str, '%Y-%m-%dT%H:%M')
            show.timing = timing_str
            show.tags = request.form['tags']
            show.price = request.form['price']
            show.yt_link = request.form['video_link']
            show.seat_available.date = timing_str
            show.seat_available.venue_id = show.venue_id

            db.session.commit()
            file = request.files['image']
            file.save(f"static/{show.venue_id}.{show.show_name}.jpg")
            return redirect(f"/manage_your_show{show.venue_id}")
        return render_template('edit_show.html', show=show)


@app.route('/edit_admin_show<int:show_id>', methods=['GET', 'POST'])
@login_required
def edit_admin_show(show_id):
    if current_user.get_role() == 'admin':
        show = ShowBooking.query.get(show_id)
        if request.method == 'POST':
            show.show_name = request.form['show_name']
            show.rating = request.form['rating']
            timing_str = request.form.get('timing')
            timing_str = datetime.strptime(timing_str, '%Y-%m-%dT%H:%M')
            show.timing = timing_str
            show.tags = request.form['tags']
            show.price = request.form['price']
            show.yt_link = request.form['video_link']
            show.seat_available.date = timing_str
            show.seat_available.venue_id = show.venue_id
            db.session.commit()
            file = request.files['image']
            file.save(f"static/{show.venue_id}.{show.show_name}.jpg")
            return redirect(f"admin/{current_user.id}")

        return render_template('edit_show.html', show=show)


@app.route('/search', methods=['Get', 'POST'])
def search():
    location_result = []
    venues = Venue.query.all()
    rating_result = []
    tag_result = []
    venue_result = []
    bookings = Booking.query.all()
    ratings = {}
    for booking in bookings:
        if booking.show_id not in ratings:
            ratings[booking.show_id] = []
        ratings[booking.show_id].append(booking.rating)

    for show_id in ratings:
        avg_rating = round(sum(ratings[show_id]) / len(ratings[show_id]), 1)

        ratings[show_id] = avg_rating

    if request.method == "POST":

        if 'search' in request.form:
            query = request.form['search']
            results = ShowBooking.query.filter(ShowBooking.show_name.ilike('%{}%'.format(query))).all()
            return render_template('search_results.html', ratings=ratings, results=results, venues=venues,
                                   v_location=list(set([v.location for v in venues])))

        tags = request.form.getlist('tags')
        location = request.form.getlist('location')
        # venue filtering
        venue = request.form.getlist('venue')
        rating = request.form.getlist('rating')
        if location:
            results = [ShowBooking.query.join(Venue).filter(Venue.location.ilike(x)).all() for x in location]
            location_result = [y for x in results for y in x]

        if tags:
            results = [ShowBooking.query.filter(ShowBooking.tags.ilike(x)).all() for x in tags]
            tag_result = [y for x in results for y in x]

        if venue:
            results = [ShowBooking.query.filter(ShowBooking.venue_id == x).all() for x in venue]
            venue_result = [y for x in results for y in x]

        # rating filtering
        if rating:
            results = [ShowBooking.query.filter(ShowBooking.rating.ilike(x)).all() for x in rating]
            rating_result = [y for x in results for y in x]

        if location and tags and rating and venue:
            results = list(
                set(location_result).intersection(tag_result).intersection(rating_result).intersection(venue_result))
        elif location and tags and venue:
            results = list(set(location_result).intersection(tag_result).intersection(venue_result))
        elif location and tags and rating:
            results = list(set(location_result).intersection(tag_result).intersection(rating_result))
        elif location and venue and rating:
            results = list(set(location_result).intersection(venue_result).intersection(rating_result))
        elif tags and rating and venue:
            results = list(set(tag_result).intersection(rating_result).intersection(venue_result))
        elif location and tags:
            results = list(set(location_result).intersection(tag_result))
        elif location and venue:
            results = list(set(location_result).intersection(venue_result))
        elif location and rating:
            results = list(set(location_result).intersection(rating_result))
        elif tags and rating:
            results = list(set(tag_result).intersection(rating_result))
        elif tags and venue:
            results = list(set(tag_result).intersection(venue_result))
        elif venue and rating:
            results = list(set(venue_result).intersection(rating_result))
        else:
            results = list(OrderedDict.fromkeys(location_result + tag_result + venue_result + rating_result))

        return render_template('search_results.html', results=results, venues=venues, ratings=ratings,
                               v_location=list(set([v.location for v in venues])))

    return render_template('search_results.html', venues=venues, ratings=ratings,
                           v_location=list(set([v.location for v in venues])),
                           results=ShowBooking.query.all())


@app.route('/location', methods=['GET', 'POST'])
def location():
    venues = Venue.query.all()
    venues = list(OrderedDict.fromkeys([x.location for x in venues]))
    if request.method == 'POST':

        venue = request.form.get('btn')
        if not venue:
            error = 'Please select a location'
            return render_template('location.html', venues=venues, error=error)
        session['selected_venue'] = venue

        if current_user.is_authenticated:
            return redirect(url_for('user', id=current_user.id))
        else:
            return redirect(url_for('index'))
    return render_template('location.html', venues=venues)


@app.route('/user_shows', methods=['GET', 'POST'])
@login_required
def user_bookings():
    bookings = Booking.query.filter((Booking.user_id == current_user.id) & (Booking.seat_booked != 0)).all()
    show_bookings = [ShowBooking.query.get(booking.show_id) for booking in bookings]
    time = datetime.now()
    return render_template('user_booking.html', shows=show_bookings, time=time)


@app.route('/delete_booking/<int:id>/<int:show_id>')
@login_required
def delete_booking(id, show_id):
    order = Booking.query.filter_by(user_id=id, show_id=show_id).first()
    show = ShowBooking.query.get(show_id)
    show.seat_available.available_seats = show.seat_available.available_seats + order.seat_booked
    db.session.delete(order)
    db.session.commit()
    return redirect("/user_shows")


@app.route('/popularity')
@login_required
def popularity():
    if current_user.get_role() == 'admin':
        # retrieve all the shows from the database
        bookings = Booking.query.order_by(Booking.seat_booked.desc()).all()
        shows_sorted = [ShowBooking.query.get(x.show_id) for x in bookings if
                        ShowBooking.query.get(x.show_id) is not None and x.seat_booked > 0]

        # count the number of occurrences of each venue
        venues = [Venue.query.get(x.venue_id).name for x in shows_sorted if x in shows_sorted is not None]
        venue_counts = {}
        for venue in venues:
            if venue in venue_counts:
                venue_counts[venue] += 1
            else:
                venue_counts[venue] = 1
        venues_sorted = sorted(venue_counts.keys())
        venue_popularity = [venue_counts[x] for x in venues_sorted]
        # combine the two lists into a list of tuples

        # create a bar chart of the venue popularity
        fig1, ax1 = plt.subplots()
        ax1.bar(venues_sorted, venue_popularity)
        ax1.set_xlabel('Venue')
        ax1.set_ylabel('Number of bookings')
        ax1.set_title('Venue Popularity')

        # count the number of occurrences of each show
        titles = [show.show_name[:10] for show in shows_sorted]
        show_counts = {}
        for title in titles:
            if title in show_counts:
                show_counts[title] += 1
            else:
                show_counts[title] = 1
        titles_sorted = sorted(show_counts.keys())
        show_popularity = [show_counts[x] for x in titles_sorted]
        # combine the two lists into a list of tuples
        data = list(zip(titles_sorted, show_popularity))
        show_name = [show.show_name for show in shows_sorted]
        show_counts = {}
        for title in show_name:
            if title in show_counts:
                show_counts[title] += 1
            else:
                show_counts[title] = 1
        shows_sorted = sorted(show_counts.keys())

        # create a colormap to map x-axis values to colors
        cmap = plt.get_cmap('coolwarm')
        colors = [cmap(i) for i in np.linspace(0, 1, len(titles_sorted))]

        # create a bar chart of the show popularity with colored bars
        fig2, ax2 = plt.subplots()
        bars = ax2.bar(titles_sorted, show_popularity, color=colors)

        # Add legend for the bars
        ax2.legend(bars, shows_sorted)

        ax2.set_xlabel('Show title')
        ax2.set_ylabel('Number of Users BOOKED')
        ax2.set_title('Show Popularity')

        # save the visualizations to the static folder
        static_folder = os.path.join(app.root_path, 'static')
        filename1 = f"venue_popularity.png"
        filepath1 = os.path.join(static_folder, filename1)
        fig1.savefig(filepath1)
        filename2 = f"show_popularity.png"
        filepath2 = os.path.join(static_folder, filename2)
        fig2.savefig(filepath2)
        static_folder = os.path.join(app.root_path, 'static')
        filepath = os.path.join(static_folder, 'venue_popularity.csv')

        # write the data to a CSV file in the static directory
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Venue', 'Popularity'])
            for i in range(len(venues_sorted)):
                writer.writerow([venues_sorted[i], venue_popularity[i]])
            # write the list to a CSV file
        filename = os.path.join(static_folder, 'show_popularity.csv')
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Popularity"])  # write header row
            writer.writerows(data)

        return render_template('popularity.html', filename1=filename1, filename2=filename2)


@app.route('/rating/<int:id>', methods=['POST', 'GET'])
def rating(id):
    if request.method == 'POST':
        show_id = id
        user_id = current_user.id
        booking = Booking.query.filter_by(user_id=user_id, show_id=show_id).first()
        booking.rating = request.form['rating']
        db.session.commit()
        return redirect('/user_shows')

    return redirect('/user_shows')


if __name__ == '__main__':
    app.run(debug=True,port=2023)
