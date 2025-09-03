# app.py - FINAL CORRECTED VERSION

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing
CORS(app)

# --- CORRECTED: Database Configuration with Absolute Path ---
# This gets the absolute path of the directory where app.py is located
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
# Create the directory if it doesn't exist
os.makedirs(instance_path, exist_ok=True)

# Use the new absolute path for the database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "restaurant.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- CORRECTED: Database Models (with proper indentation) ---
class RestaurantTable(db.Model):
    # These lines MUST be indented
    id = db.Column(db.Integer, primary_key=True)
    capacity = db.Column(db.Integer, nullable=False)

class Booking(db.Model):
    # These lines MUST be indented
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_table.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    booking_date = db.Column(db.String(20), nullable=False)
    booking_time = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint('table_id', 'booking_date', 'booking_time', name='_table_date_time_uc'),)

# --- Your Existing Email Configuration & Function (No Changes) ---
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
RECIPIENT_EMAIL = 'donsavio1one@gmail.com'

def send_email(subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("Error: Email credentials not set in .env file.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"Email sent successfully: '{subject}'")
        return True
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return False

# --- /book_table Route with Database Logic ---
@app.route('/book_table', methods=['POST'])
def book_table():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    try:
        name = data.get('name')
        guests = int(data.get('guests'))
        date = data.get('date')
        time = data.get('time')
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid input format."}), 400

    booked_table_ids = [b.table_id for b in Booking.query.filter_by(booking_date=date, booking_time=time).all()]
    available_table = RestaurantTable.query.filter(RestaurantTable.capacity >= guests, RestaurantTable.id.notin_(booked_table_ids)).order_by(RestaurantTable.capacity).first()

    if not available_table:
        return jsonify({"message": "Sorry, no tables are available for that time and party size."}), 409

    try:
        new_booking = Booking(table_id=available_table.id, customer_name=name, guests=guests, booking_date=date, booking_time=time)
        db.session.add(new_booking)
        db.session.commit()
        subject = f"New Table Booking from {name}"
        body = f"""A new reservation has been confirmed and saved to the database:
        Name: {name}
        Number of Guests: {guests}
        Date: {date}
        Time: {time}
        Assigned Table ID: {available_table.id}
        """
        send_email(subject, body)
        return jsonify({"message": f"Table for {guests} booked successfully for {name}!"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Database or Email error: {e}")
        return jsonify({"message": "Could not process booking due to a server error."}), 500

# --- Your Existing /place_order Route (No Changes) ---
@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    subject = f"New Food Order from {data.get('name')}"
    body = f"""
    You have a new food order from your website:

    Customer Details:
    -----------------
    Name: {data.get('name')}
    Phone: {data.get('phone')}
    Address: {data.get('address')}

    Order Details:
    --------------
    {data.get('orderDetails')}

    -----------------
    Total Price: ${data.get('totalPrice')}
    """
    if send_email(subject, body):
        return jsonify({"message": "Order received and email sent."}), 200
    else:
        return jsonify({"error": "Failed to send notification email."}), 500

# --- Main execution block ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
