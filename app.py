# app.py
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime
import os
from functools import wraps

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

# Admin credentials (change these!)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'barber123')

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

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Barber Shop</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #000;
                color: #fff;
            }
            .container {
                text-align: center;
            }
            h1 {
                font-size: 3rem;
                font-weight: 300;
                letter-spacing: 2px;
                margin-bottom: 3rem;
                text-transform: uppercase;
            }
            .btn {
                display: inline-block;
                margin: 1rem;
                padding: 1rem 3rem;
                background: transparent;
                color: #fff;
                text-decoration: none;
                border: 1px solid rgba(255,255,255,0.3);
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: all 0.3s ease;
            }
            .btn:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.5);
            }
            .btn-primary {
                background: #fff;
                color: #000;
            }
            .btn-primary:hover {
                background: rgba(255,255,255,0.9);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Barber Shop</h1>
            <a href="/book" class="btn btn-primary">Book Appointment</a>
            <a href="/login" class="btn">Admin Login</a>
        </div>
    </body>
    </html>
    '''

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('serve_admin_page'))
        else:
            error = "Invalid credentials"
    
    # Render login page with inline HTML
    error_html = f'<div class="error">{error}</div>' if error else ''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - Barber Shop</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #000;
            color: #fff;
        }}
        .login-form {{
            background: rgba(255,255,255,0.05);
            padding: 3rem;
            border: 1px solid rgba(255,255,255,0.1);
            width: 100%;
            max-width: 400px;
        }}
        h2 {{
            text-align: center;
            font-weight: 300;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 2rem;
        }}
        .form-group {{
            margin-bottom: 1.5rem;
        }}
        label {{
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.6);
        }}
        input {{
            width: 100%;
            padding: 0.75rem;
            background: transparent;
            border: none;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            color: #fff;
            font-size: 1rem;
        }}
        input:focus {{
            outline: none;
            border-bottom-color: rgba(255,255,255,0.5);
        }}
        button {{
            width: 100%;
            padding: 1rem;
            background: #fff;
            color: #000;
            border: none;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        button:hover {{
            background: rgba(255,255,255,0.9);
        }}
        .error {{
            color: #ff6b6b;
            text-align: center;
            margin-bottom: 1rem;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 2rem;
            color: rgba(255,255,255,0.6);
            text-decoration: none;
        }}
        .back-link:hover {{
            color: rgba(255,255,255,0.8);
        }}
    </style>
</head>
<body>
    <form class="login-form" method="POST">
        <h2>Admin Login</h2>
        {error_html}
        <div class="form-group">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" required>
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required>
        </div>
        <button type="submit">Login</button>
        <a href="/" class="back-link">← Back to Home</a>
    </form>
</body>
</html>
'''

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

# Serve static files
@app.route('/book')
def serve_booking_page():
    import os
    print(f"Current directory: {os.getcwd()}")
    print(f"Files in directory: {os.listdir('.')}")
    
    if os.path.exists('index.html'):
        print("index.html found!")
        return send_from_directory('.', 'index.html')
    else:
        print("index.html NOT found!")
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>index.html not found</h1>
            <p>Current directory: ''' + os.getcwd() + '''</p>
            <p>Files in directory:</p>
            <ul>
            ''' + ''.join([f'<li>{f}</li>' for f in os.listdir('.')]) + '''
            </ul>
            <p>Please ensure index.html is in the root directory of your GitHub repository.</p>
            <a href="/">Back to Home</a>
        </body>
        </html>
        ''', 404

@app.route('/admin')
@login_required
def serve_admin_page():
    import os
    if os.path.exists('admin.html'):
        return send_from_directory('.', 'admin.html')
    else:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>admin.html not found</h1>
            <p>Please ensure admin.html is in the root directory of your GitHub repository.</p>
            <a href="/">Back to Home</a>
        </body>
        </html>
        ''', 404

# API Routes
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
