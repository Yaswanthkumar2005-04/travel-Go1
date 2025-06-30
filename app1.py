from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import boto3
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import json
import uuid

app = Flask(__name__)
app.secret_key = '1879a49b06ff9b4ef1efd9b63dbd911df26b566d1d0769dd5726607d63d0ce88'

# --- DynamoDB Connection for Local DynamoDB ---
# IMPORTANT: For local DynamoDB, specify the endpoint_url.
# You can use any dummy region_name, aws_access_key_id, and aws_secret_access_key
# as they are not used when connecting to a local endpoint.
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url="http://localhost:8000",  # Default port for DynamoDB Local
    region_name="us-east-1",                # Dummy region for local connection
    aws_access_key_id="dummy_access_key",   # Dummy access key for local connection
    aws_secret_access_key="dummy_secret_key" # Dummy secret key for local connection
)
dynamodb_client = boto3.client(
    'dynamodb',
    endpoint_url="http://localhost:8000",  # Default port for DynamoDB Local
    region_name="us-east-1",                # Dummy region for local connection
    aws_access_key_id="dummy_access_key",   # Dummy access key for local connection
    aws_secret_access_key="dummy_secret_key" # Dummy secret key for local connection
)

# Table names
USERS_TABLE_NAME = 'travel_booking_users'
FLIGHTS_TABLE_NAME = 'travel_booking_flights'
TRAINS_TABLE_NAME = 'travel_booking_trains'
BOOKINGS_TABLE_NAME = 'travel_booking_bookings'
HOTELS_TABLE_NAME = 'travel_booking_hotels'

# DynamoDB Table objects (will be initialized after table creation check)
users_table = dynamodb.Table(USERS_TABLE_NAME)
flights_table = dynamodb.Table(FLIGHTS_TABLE_NAME)
trains_table = dynamodb.Table(TRAINS_TABLE_NAME)
bookings_table = dynamodb.Table(BOOKINGS_TABLE_NAME)
hotels_table = dynamodb.Table(HOTELS_TABLE_NAME)

# --- Helper function to check if table exists and create if not ---
def create_dynamodb_table(table_name, primary_key, attribute_type='S'):
    try:
        dynamodb_client.describe_table(TableName=table_name)
        print(f"Table '{table_name}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Table '{table_name}' not found. Creating...")
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{'AttributeName': primary_key, 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': primary_key, 'AttributeType': attribute_type}],
                # ProvisionedThroughput is required even for local, but values don't heavily impact performance
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            # Wait until the table exists before proceeding
            dynamodb.Table(table_name).wait_until_exists()
            print(f"Table '{table_name}' created successfully.")
        else:
            # Re-raise other ClientErrors
            raise e

# --- Sample Data Insertion Functions ---
def insert_sample_train_data():
    # Ensure the table exists before inserting data
    create_dynamodb_table(TRAINS_TABLE_NAME, 'train_number')
    response = trains_table.scan(Select='COUNT')
    if response['Count'] == 0:
        sample_trains = [
            {"train_id": str(uuid.uuid4()), "name": "Duronto Express", "train_number": "12285", "source": "Hyderabad", "destination": "Delhi", "departure_time": "07:00 AM", "arrival_time": "05:00 AM (next day)", "price": 1800, "date": "2025-07-10"},
            {"train_id": str(uuid.uuid4()), "name": "AP Express", "train_number": "12723", "source": "Hyderabad", "destination": "Vijayawada", "departure_time": "09:00 AM", "arrival_time": "03:00 PM", "price": 450, "date": "2025-07-10"},
            {"train_id": str(uuid.uuid4()), "name": "Gouthami Express", "train_number": "12737", "source": "Guntur", "destination": "Hyderabad", "departure_time": "08:00 PM", "arrival_time": "06:00 AM (next day)", "price": 600, "date": "2025-07-10"},
            {"train_id": str(uuid.uuid4()), "name": "Chennai Express", "train_number": "12839", "source": "Bengaluru", "destination": "Chennai", "departure_time": "10:30 AM", "arrival_time": "05:30 PM", "price": 750, "date": "2025-07-11"},
            {"train_id": str(uuid.uuid4()), "name": "Mumbai Mail", "train_number": "12101", "source": "Hyderabad", "destination": "Mumbai", "departure_time": "06:00 PM", "arrival_time": "09:00 AM (next day)", "price": 1200, "date": "2025-07-10"},
            {"train_id": str(uuid.uuid4()), "name": "Godavari Express", "train_number": "12720", "source": "Vijayawada", "destination": "Hyderabad", "departure_time": "05:00 PM", "arrival_time": "11:00 PM", "price": 400, "date": "2025-07-10"},
        ]
        with trains_table.batch_writer() as batch:
            for train in sample_trains:
                batch.put_item(Item=train)
        print("Sample train data inserted into DynamoDB.")
    else:
        print("Train data already exists. Skipping insertion.")


def insert_sample_flight_data():
    # Ensure the table exists before inserting data
    create_dynamodb_table(FLIGHTS_TABLE_NAME, 'flight_number')
    response = flights_table.scan(Select='COUNT')
    if response['Count'] == 0:
        sample_flights = [
            {"flight_id": str(uuid.uuid4()), "airline": "IndiGo", "flight_number": "6E 2345", "source": "Delhi", "destination": "Mumbai", "departure_time": "10:00 AM", "arrival_time": "12:00 PM", "price": 5000, "date": "2025-07-15"},
            {"flight_id": str(uuid.uuid4()), "airline": "Air India", "flight_number": "AI 400", "source": "Mumbai", "destination": "Bengaluru", "departure_time": "03:00 PM", "arrival_time": "05:00 PM", "price": 6500, "date": "2025-07-15"},
            {"flight_id": str(uuid.uuid4()), "airline": "SpiceJet", "flight_number": "SG 876", "source": "Bengaluru", "destination": "Chennai", "departure_time": "08:00 AM", "arrival_time": "09:00 AM", "price": 3000, "date": "2025-07-16"},
            {"flight_id": str(uuid.uuid4()), "airline": "Vistara", "flight_number": "UK 990", "source": "Chennai", "destination": "Hyderabad", "departure_time": "11:00 AM", "arrival_time": "12:30 PM", "price": 4500, "date": "2025-07-16"},
        ]
        with flights_table.batch_writer() as batch:
            for flight in sample_flights:
                batch.put_item(Item=flight)
        print("Sample flight data inserted into DynamoDB.")
    else:
        print("Flight data already exists. Skipping insertion.")


def insert_sample_hotel_data():
    # Ensure the table exists before inserting data
    create_dynamodb_table(HOTELS_TABLE_NAME, 'hotel_id') # Changed PK to hotel_id for uniqueness
    response = hotels_table.scan(Select='COUNT')
    if response['Count'] == 0:
        sample_hotels = [
            {"hotel_id": str(uuid.uuid4()), "name": "The Grand Hotel", "location": "Mumbai", "price_per_night": 4000},
            {"hotel_id": str(uuid.uuid4()), "name": "City Centre Inn", "location": "Delhi", "price_per_night": 2500},
            {"hotel_id": str(uuid.uuid4()), "name": "Royal Residency", "location": "Bengaluru", "price_per_night": 3500},
            {"hotel_id": str(uuid.uuid4()), "name": "Seaside Resort", "location": "Chennai", "price_per_night": 5000},
        ]
        with hotels_table.batch_writer() as batch:
            for hotel in sample_hotels:
                batch.put_item(Item=hotel)
        print("Sample hotel data inserted into DynamoDB.")
    else:
        print("Hotel data already exists. Skipping insertion.")

def insert_default_user():
    # Ensure the table exists before inserting data
    create_dynamodb_table(USERS_TABLE_NAME, 'email')
    default_email = "ronankiyaswanth@gmail.com"
    default_password = "123r"
    default_fullname = "yaswanth kumar ronanki"

    response = users_table.get_item(Key={'email': default_email})
    user = response.get('Item')

    if not user:
        hashed_password = generate_password_hash(default_password)
        users_table.put_item(Item={'fullname': default_fullname, 'email': default_email, 'password': hashed_password})
        print("Default user inserted.")
    elif user.get('fullname') != default_fullname:
        # Update fullname if it's different
        users_table.update_item(
            Key={'email': default_email},
            UpdateExpression='SET fullname = :val1',
            ExpressionAttributeValues={':val1': default_fullname}
        )
        print(f"Default user '{default_email}' fullname updated to '{default_fullname}'.")
    else:
        print("Default user already exists and is up-to-date. Skipping insertion.")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match!')

        response = users_table.get_item(Key={'email': email})
        if response.get('Item'):
            return render_template('register.html', error='Email already exists!')

        hashed_password = generate_password_hash(password)
        users_table.put_item(Item={'fullname': fullname, 'email': email, 'password': hashed_password})
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            session['fullname'] = user.get('fullname', email)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', message='Invalid email or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('fullname', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    user_email = session['email']
    user_fullname = session.get('fullname', user_email)

    # Fetch bookings for the current user, excluding those with 'Cancelled' status
    # DynamoDB doesn't have a direct 'sort' on scan/query unless it's a sort key.
    # We'll fetch and then sort in Python.
    try:
        response = bookings_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('user_email').eq(user_email) & \
                             boto3.dynamodb.conditions.Attr('status').ne('Cancelled')
        )
        user_bookings = response.get('Items', [])
        # Sort bookings by booking_date in descending order (most recent first)
        user_bookings.sort(key=lambda x: x.get('booking_date', ''), reverse=True)

    except ClientError as e:
        print(f"Error fetching bookings: {e.response['Error']['Message']}")
        user_bookings = []

    for booking in user_bookings:
        # 'booking_id' is already a string in DynamoDB
        booking['booking_id'] = booking.get('booking_id')

        # Ensure 'status' field exists, default to 'Confirmed' if not present for older bookings
        if 'status' not in booking:
            booking['status'] = 'Confirmed'
            # Optional: Update the document in DB to set this default if you want persistence
            # bookings_table.update_item(
            #     Key={'booking_id': booking['booking_id']},
            #     UpdateExpression='SET #s = :val',
            #     ExpressionAttributeNames={'#s': 'status'},
            #     ExpressionAttributeValues={':val': 'Confirmed'}
            # )

        # Populate display fields based on booking type
        booking_type_lower = booking.get('booking_type', '').lower()
        booking['booking_type'] = booking_type_lower.capitalize() # For display: e.g., 'Bus', 'Hotel'

        if booking_type_lower == 'flight':
            booking['airline'] = booking.get('airline', 'N/A')
            booking['flight_number'] = booking.get('flight_number', 'N/A')
            booking['origin'] = booking.get('source', 'N/A') # Renamed for clarity in HTML
            booking['destination'] = booking.get('destination', 'N/A')
            booking['departure_time'] = booking.get('departure_time', 'N/A')
            booking['arrival_time'] = booking.get('arrival_time', 'N/A')
            booking['num_persons'] = booking.get('num_persons', 'N/A')
            booking['selected_seats'] = booking.get('selected_seats', [])
        elif booking_type_lower == 'hotel':
            booking['hotel_name'] = booking.get('hotel_name', 'N/A')
            booking['location'] = booking.get('location', 'N/A')
            booking['check_in_date'] = booking.get('check_in_date', 'N/A')
            booking['check_out_date'] = booking.get('check_out_date', 'N/A')
            booking['num_nights'] = booking.get('num_nights', 'N/A')
            booking['num_rooms'] = booking.get('num_rooms', 'N/A')
            booking['num_guests'] = booking.get('num_guests', 'N/A')
            booking['selected_rooms'] = booking.get('selected_rooms', [])
        elif booking_type_lower == 'bus':
            booking['name'] = booking.get('name', 'N/A')
            booking['source'] = booking.get('source', 'N/A')
            booking['destination'] = booking.get('destination', 'N/A')
            booking['time'] = booking.get('time', 'N/A')
            booking['num_persons'] = booking.get('num_persons', 'N/A')
            booking['selected_seats'] = booking.get('selected_seats', [])
            booking['travel_date'] = booking.get('travel_date', 'N/A')
        elif booking_type_lower == 'train':
            booking['name'] = booking.get('name', 'N/A')
            booking['train_number'] = booking.get('train_number', 'N/A')
            booking['source'] = booking.get('source', 'N/A')
            booking['destination'] = booking.get('destination', 'N/A')
            booking['departure_time'] = booking.get('departure_time', 'N/A')
            booking['arrival_time'] = booking.get('arrival_time', 'N/A')
            booking['num_persons'] = booking.get('num_persons', 'N/A')
            booking['selected_seats'] = booking.get('selected_seats', [])
            booking['travel_date'] = booking.get('travel_date', 'N/A')

    return render_template('dashboard.html', name=user_fullname, bookings=user_bookings)

# --- Bus Search and Booking Flow ---
@app.route('/bus')
def bus():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('bus.html')

@app.route('/confirm_bus_booking', methods=['POST'])
def confirm_bus_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    name = request.form.get('name')
    source = request.form.get('source')
    destination = request.form.get('destination')
    time = request.form.get('time')
    bus_type = request.form.get('type')
    travel_date = request.form.get('date')
    try:
        price_per_person = float(request.form.get('price'))
        num_persons = int(request.form.get('persons'))
    except (TypeError, ValueError):
        return redirect(url_for('bus'))
    total_price = price_per_person * num_persons
    booking_details = {
        'name': name,
        'source': source,
        'destination': destination,
        'time': time,
        'type': bus_type,
        'price_per_person': price_per_person,
        'travel_date': travel_date,
        'num_persons': num_persons,
        'total_price': total_price,
        'booking_type': 'bus',
        'user_email': session['email'],
        'status': 'Confirmed'
    }
    session['pending_booking'] = booking_details
    return redirect(url_for('select_seats'))

# --- Train Search and Booking Flow ---
@app.route('/train')
def train():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('train.html')

@app.route('/confirm_train_booking', methods=['POST'])
def confirm_train_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    name = request.form.get('name')
    train_number = request.form.get('trainNumber')
    source = request.form.get('source')
    destination = request.form.get('destination')
    departure_time = request.form.get('departureTime')
    arrival_time = request.form.get('arrivalTime')
    travel_date = request.form.get('date')
    try:
        price_per_person = float(request.form.get('price'))
        num_persons = int(request.form.get('persons'))
    except (TypeError, ValueError):
        return redirect(url_for('train'))
    total_price = price_per_person * num_persons
    booking_details = {
        'name': name,
        'train_number': train_number,
        'source': source,
        'destination': destination,
        'departure_time': departure_time,
        'arrival_time': arrival_time,
        'price_per_person': price_per_person,
        'travel_date': travel_date,
        'num_persons': num_persons,
        'total_price': total_price,
        'booking_type': 'train',
        'user_email': session['email'],
        'status': 'Confirmed'
    }
    session['pending_booking'] = booking_details
    return redirect(url_for('select_seats'))

# --- Flight Search and Booking Flow ---
@app.route('/flight', methods=['GET', 'POST'])
def flight():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('flight.html')

@app.route('/confirm_flight_booking', methods=['POST'])
def confirm_flight_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    airline = request.form.get('airline')
    flight_number = request.form.get('flightNumber')
    source = request.form.get('source')
    destination = request.form.get('destination')
    departure_time = request.form.get('departureTime')
    arrival_time = request.form.get('arrivalTime')
    travel_date = request.form.get('date')
    try:
        price_per_person = float(request.form.get('price'))
        num_persons = int(request.form.get('persons'))
    except (TypeError, ValueError):
        return redirect(url_for('flight'))
    total_price = price_per_person * num_persons
    booking_details = {
        'airline': airline,
        'flight_number': flight_number,
        'source': source,
        'destination': destination,
        'departure_time': departure_time,
        'arrival_time': arrival_time,
        'price_per_person': price_per_person,
        'travel_date': travel_date,
        'num_persons': num_persons,
        'total_price': total_price,
        'booking_type': 'flight',
        'user_email': session['email'],
        'status': 'Confirmed'
    }
    session['pending_booking'] = booking_details
    return redirect(url_for('select_seats'))

# --- Seat Selection and Confirmation Step ---
@app.route('/select_seats', methods=['GET'])
def select_seats():
    if 'email' not in session:
        return redirect(url_for('login'))
    booking_details = session.get('pending_booking')
    if not booking_details:
        return redirect(url_for('dashboard'))
    all_seats = [f"{row}{num}" for row in ['A', 'B', 'C', 'D', 'E'] for num in range(1, 7)]
    dummy_booked_seats = random.sample(all_seats, k=random.randint(5, 10))
    vehicle_type = "N/A"
    if booking_details.get('booking_type') == 'bus':
        vehicle_type = booking_details.get('type', 'Bus')
    elif booking_details.get('booking_type') == 'train':
        vehicle_type = "Train"
    elif booking_details.get('booking_type') == 'flight':
        vehicle_type = "Flight"
    time_display = booking_details.get('time')
    if booking_details.get('departure_time') and booking_details.get('arrival_time'):
        time_display = f"{booking_details.get('departure_time')} - {booking_details.get('arrival_time')}"
    return render_template(
        'seat.html',
        name=booking_details.get('name', booking_details.get('airline')),
        booking_type=booking_details.get('booking_type'),
        source=booking_details.get('source'),
        destination=booking_details.get('destination'),
        time=time_display,
        vehicle_type=vehicle_type, # Corrected from vehicle_details
        price_per_person=booking_details.get('price_per_person'),
        travel_date=booking_details.get('travel_date'),
        num_persons=booking_details.get('num_persons'),
        booked_seats=dummy_booked_seats
    )

@app.route('/book_selected_seats', methods=['POST'])
def book_selected_seats():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in', 'redirect': url_for('login')}), 401
    data = request.get_json()
    booking_data = session.pop('pending_booking', None)
    if not booking_data:
        return jsonify({'success': False, 'message': 'No pending booking found for seat selection.'}), 400
    if not data or 'selectedSeats' not in data:
        return jsonify({'success': False, 'message': 'No seats selected.'}), 400
    selected_seats = data.get('selectedSeats', [])
    booking_data['selected_seats'] = selected_seats
    booking_data['total_price'] = booking_data['price_per_person'] * booking_data['num_persons']
    session['final_booking'] = booking_data

    if booking_data['booking_type'] == 'bus':
        redirect_url = url_for('confirm_seat_booking')
    elif booking_data['booking_type'] == 'train':
        redirect_url = url_for('confirm_train_seat_booking')
    elif booking_data['booking_type'] == 'flight':
        redirect_url = url_for('confirm_flight_seat_booking')
    else:
        redirect_url = url_for('dashboard')

    return jsonify({
        'success': True,
        'message': 'Seats selected! Redirecting to confirmation...',
        'redirect': redirect_url
    })

# --- Confirmation Pages for Seat Bookings ---
@app.route('/confirm_seat_booking')
def confirm_seat_booking():
    booking = session.get('final_booking')
    if not booking:
        return redirect(url_for('dashboard'))
    return render_template('confirm.html', booking=booking)

@app.route('/confirm_train_seat_booking')
def confirm_train_seat_booking():
    booking = session.get('final_booking')
    if not booking:
        return redirect(url_for('dashboard'))
    return render_template('confirmtrain.html', booking=booking)

@app.route('/confirm_flight_seat_booking')
def confirm_flight_seat_booking():
    booking = session.get('final_booking')
    if not booking:
        return redirect(url_for('dashboard'))
    return render_template('confirmflight.html', booking=booking)

# --- Final Confirmation Endpoints ---
@app.route('/final_confirm_seat_booking', methods=['POST'])
def final_confirm_seat_booking():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in', 'redirect': url_for('login')}), 401
    booking_data = session.pop('final_booking', None)
    if not booking_data:
        return jsonify({'success': False, 'message': 'No booking to confirm.', 'redirect': url_for('dashboard')}), 400
    try:
        booking_data['booking_id'] = str(uuid.uuid4()) # Generate a unique ID for DynamoDB
        booking_data['booking_date'] = datetime.now().isoformat()
        bookings_table.put_item(Item=booking_data)
        return jsonify({'success': True, 'message': 'Booking confirmed!', 'redirect': url_for('dashboard')})
    except ClientError as e:
        return jsonify({'success': False, 'message': f'Failed to confirm booking: {e.response["Error"]["Message"]}', 'redirect': url_for('dashboard')}), 500

@app.route('/final_confirm_train_seat_booking', methods=['POST'])
def final_confirm_train_seat_booking():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in', 'redirect': url_for('login')}), 401
    booking_data = session.pop('final_booking', None)
    if not booking_data:
        return jsonify({'success': False, 'message': 'No booking to confirm.', 'redirect': url_for('dashboard')}), 400
    try:
        booking_data['booking_id'] = str(uuid.uuid4()) # Generate a unique ID for DynamoDB
        booking_data['booking_date'] = datetime.now().isoformat()
        bookings_table.put_item(Item=booking_data)
        return jsonify({'success': True, 'message': 'Train booking confirmed!', 'redirect': url_for('dashboard')})
    except ClientError as e:
        return jsonify({'success': False, 'message': f'Failed to confirm booking: {e.response["Error"]["Message"]}', 'redirect': url_for('dashboard')}), 500

@app.route('/final_confirm_flight_seat_booking', methods=['POST'])
def final_confirm_flight_seat_booking():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in', 'redirect': url_for('login')}), 401
    booking_data = session.pop('final_booking', None)
    if not booking_data:
        return jsonify({'success': False, 'message': 'No booking to confirm.', 'redirect': url_for('dashboard')}), 400
    try:
        booking_data['booking_id'] = str(uuid.uuid4()) # Generate a unique ID for DynamoDB
        booking_data['booking_date'] = datetime.now().isoformat()
        bookings_table.put_item(Item=booking_data)
        return jsonify({'success': True, 'message': 'Flight booking confirmed!', 'redirect': url_for('dashboard')})
    except ClientError as e:
        return jsonify({'success': False, 'message': f'Failed to confirm booking: {e.response["Error"]["Message"]}', 'redirect': url_for('dashboard')}), 500

# --- Hotel Search and Booking Flow ---
@app.route('/hotel')
def hotel():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('hotel.html')

@app.route('/confirm_hotel_booking', methods=['POST'])
def confirm_hotel_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    hotel_name = request.form.get('hotelName')
    location = request.form.get('location')
    check_in_date = request.form.get('checkInDate')
    check_out_date = request.form.get('checkOutDate')
    try:
        num_rooms = int(request.form.get('numRooms'))
        num_guests = int(request.form.get('numGuests'))
        price_per_night = float(request.form.get('pricePerNight'))
        num_nights = int(request.form.get('numNights'))
    except (TypeError, ValueError):
        return redirect(url_for('hotel'))
    total_price = price_per_night * num_rooms * num_nights
    booking_details = {
        'hotel_name': hotel_name,
        'location': location,
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'num_rooms': num_rooms,
        'num_guests': num_guests,
        'price_per_night': price_per_night,
        'num_nights': num_nights,
        'total_price': total_price,
        'booking_type': 'hotel',
        'user_email': session['email'],
        'status': 'Confirmed'
    }
    session['pending_booking'] = booking_details
    return render_template('confirmhotel.html', booking=booking_details)

@app.route('/final_confirm_hotel_booking', methods=['POST'])
def final_confirm_hotel_booking():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in', 'redirect': url_for('login')}), 401
    booking_data = session.pop('pending_booking', None)
    if not booking_data:
        return jsonify({'success': False, 'message': 'No pending booking to confirm.', 'redirect': url_for('dashboard')}), 400
    try:
        booking_data['booking_id'] = str(uuid.uuid4()) # Generate a unique ID for DynamoDB
        booking_data['booking_date'] = datetime.now().isoformat()
        bookings_table.put_item(Item=booking_data)
        return jsonify({
            'success': True,
            'message': 'Hotel booking confirmed successfully!',
            'redirect': url_for('dashboard')
        })
    except ClientError as e:
        return jsonify({'success': False, 'message': f'Failed to confirm hotel booking: {e.response["Error"]["Message"]}', 'redirect': url_for('dashboard')}), 500

# --- Cancel Booking Route ---
@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'email' not in session:
        return redirect(url_for('login'))

    booking_id_str = request.form.get('booking_id')
    user_email = session['email']

    if not booking_id_str:
        return redirect(url_for('dashboard'))

    try:
        response = bookings_table.update_item(
            Key={'booking_id': booking_id_str},
            UpdateExpression='SET #s = :status_val',
            ConditionExpression='user_email = :user_email_val', # Ensure only owner can cancel
            ExpressionAttributeNames={
                '#s': 'status'
            },
            ExpressionAttributeValues={
                ':status_val': 'Cancelled',
                ':user_email_val': user_email
            },
            ReturnValues='UPDATED_NEW'
        )

        if response.get('Attributes'):
            print(f"Booking {booking_id_str} status updated to 'Cancelled'.")
        else:
            print(f"Booking {booking_id_str} not found, not owned by user {user_email}, or already cancelled.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print(f"Booking {booking_id_str} could not be cancelled because it's not owned by {user_email} or it doesn't exist.")
        else:
            print(f"An error occurred during cancellation: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"An unexpected error occurred during cancellation: {e}")

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    # Initialize DynamoDB tables (creates them if they don't exist)
    # Ensure all tables are created before data insertion or app run
    create_dynamodb_table(USERS_TABLE_NAME, 'email')
    create_dynamodb_table(BOOKINGS_TABLE_NAME, 'booking_id')
    create_dynamodb_table(FLIGHTS_TABLE_NAME, 'flight_number')
    create_dynamodb_table(TRAINS_TABLE_NAME, 'train_number')
    create_dynamodb_table(HOTELS_TABLE_NAME, 'hotel_id')

    # Insert sample data and default user
    insert_sample_train_data()
    insert_sample_flight_data()
    insert_sample_hotel_data()
    insert_default_user()
    
    app.run(debug=True)
