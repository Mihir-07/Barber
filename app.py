# app.py
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bookings.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('date', 'time', name='_date_time_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'time': self.time,
            'name': self.name,
            'phone': self.phone,
            'service': self.service,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create tables
with app.app_context():
    db.create_all()

# API Routes

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Barber Shop API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; }
            .endpoint {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }
            code {
                background: #f0f0f0;
                padding: 2px 5px;
                border-radius: 3px;
            }
            .links {
                margin-top: 30px;
                padding: 20px;
                background: #e9ecef;
                border-radius: 5px;
            }
            .links a {
                display: inline-block;
                margin: 10px;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .links a:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <h1>🪒 Barber Shop Booking API</h1>
        <p>Backend is running successfully!</p>
        
        <div class="links">
            <h2>Access the Application:</h2>
            <a href="/book">Customer Booking Page</a>
            <a href="/admin">Admin Panel</a>
        </div>
        
        <h2>Available API Endpoints:</h2>
        
        <div class="endpoint">
            <strong>GET /api/bookings</strong><br>
            Get all bookings (optional query params: startDate, endDate)
        </div>
        
        <div class="endpoint">
            <strong>POST /api/bookings</strong><br>
            Create a new booking<br>
            Body: <code>{ date, time, name, phone, service }</code>
        </div>
        
        <div class="endpoint">
            <strong>DELETE /api/bookings/{id}</strong><br>
            Cancel a booking
        </div>
        
        <div class="endpoint">
            <strong>GET /api/bookings/check</strong><br>
            Check if a slot is available<br>
            Query: <code>?date=XXX&time=YYY</code>
        </div>
        
        <h2>WebSocket Events:</h2>
        <div class="endpoint">
            <strong>new_booking</strong> - Emitted when a new booking is created<br>
            <strong>booking_cancelled</strong> - Emitted when a booking is cancelled
        </div>
    </body>
    </html>
    '''

# Serve static files
@app.route('/book')
def serve_booking_page():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def serve_admin_page():
    return send_from_directory('.', 'admin.html')

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    try:
        # Get query parameters for date filtering
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        query = Booking.query
        
        if start_date and end_date:
            query = query.filter(Booking.date >= start_date, Booking.date <= end_date)
        
        bookings = query.all()
        return jsonify([booking.to_dict() for booking in bookings])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['date', 'time', 'name', 'phone', 'service']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if slot is already booked
        existing = Booking.query.filter_by(date=data['date'], time=data['time']).first()
        if existing:
            return jsonify({'error': 'This time slot is already booked'}), 409
        
        # Create new booking
        booking = Booking(
            date=data['date'],
            time=data['time'],
            name=data['name'],
            phone=data['phone'],
            service=data['service']
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # Emit real-time update to all connected clients
        socketio.emit('new_booking', booking.to_dict())
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        booking_data = booking.to_dict()
        db.session.delete(booking)
        db.session.commit()
        
        # Emit real-time update
        socketio.emit('booking_cancelled', booking_data)
        
        return jsonify({'message': 'Booking cancelled successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/check', methods=['GET'])
def check_availability():
    try:
        date = request.args.get('date')
        time = request.args.get('time')
        
        if not date or not time:
            return jsonify({'error': 'Date and time are required'}), 400
        
        booking = Booking.query.filter_by(date=date, time=time).first()
        
        return jsonify({
            'available': booking is None,
            'booking': booking.to_dict() if booking else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to booking system'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port)