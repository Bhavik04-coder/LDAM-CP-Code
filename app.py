from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import hashlib
import os
import random
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import secrets
import serial
import serial.tools.list_ports
import requests

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE"])

DATABASE = 'livestock_monitoring.db'

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'your-email@gmail.com',
    'password': 'your-app-password',
    'admin_email': 'admin@yourdomain.com'
}

# Enhanced authentication system
AUTH_TOKENS = {
    'admin': 'admin123'
}

USER_SESSIONS = {}

# Arduino configuration
ARDUINO_CONFIG = {
    'port': 'COM3',  # Change to your Arduino port (COM3, COM4, /dev/ttyUSB0, etc.)
    'baudrate': 9600,
    'timeout': 1
}

# Hardcoded sample data for testing
SAMPLE_DEVICES = [
    {'device_id': 'LSM_001', 'animal_id': 'COW_001', 'animal_type': 'Cow', 'status': 'active', 'battery': '85%'},
    {'device_id': 'LSM_002', 'animal_id': 'COW_002', 'animal_type': 'Bull', 'status': 'active', 'battery': '92%'},
    {'device_id': 'LSM_003', 'animal_id': 'COW_003', 'animal_type': 'Cow', 'status': 'active', 'battery': '78%'}
]

SAMPLE_READINGS = [
    {'device_id': 'LSM_001', 'animal_id': 'COW_001', 'temperature': 38.5, 'movement': 12.5, 'location': '40.7128,-74.0060'},
    {'device_id': 'LSM_002', 'animal_id': 'COW_002', 'temperature': 39.8, 'movement': 3.2, 'location': '34.0522,-118.2437'},
    {'device_id': 'LSM_003', 'animal_id': 'COW_003', 'temperature': 37.9, 'movement': 8.7, 'location': '41.8781,-87.6298'}
]

class ArduinoInterface:
    def __init__(self):
        self.serial_conn = None
        self.is_connected = False
        
    def connect(self):
        """Connect to Arduino"""
        try:
            self.serial_conn = serial.Serial(
                port=ARDUINO_CONFIG['port'],
                baudrate=ARDUINO_CONFIG['baudrate'],
                timeout=ARDUINO_CONFIG['timeout']
            )
            time.sleep(2)  # Wait for connection to establish
            self.is_connected = True
            print(f"Connected to Arduino on {ARDUINO_CONFIG['port']}")
            return True
        except Exception as e:
            print(f"Arduino connection failed: {e}")
            self.is_connected = False
            return False
    
    def read_sensor_data(self):
        """Read sensor data from Arduino"""
        if not self.is_connected:
            if not self.connect():
                return self.generate_mock_data()
        
        try:
            # Send request for data
            self.serial_conn.write(b'GET_DATA\n')
            time.sleep(1)
            
            # Read response
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line and 'TEMP:' in line and 'GPS:' in line:
                    return self.parse_arduino_data(line)
            
            # If no data or parsing fails, return mock data
            return self.generate_mock_data()
            
        except Exception as e:
            print(f"Error reading from Arduino: {e}")
            return self.generate_mock_data()
    
    def parse_arduino_data(self, data_line):
        """Parse data from Arduino format: TEMP:38.5,GPS:40.7128,-74.0060,MOV:12.5"""
        try:
            parts = data_line.split(',')
            temp = None
            gps = None
            movement = random.uniform(1.0, 15.0)  # Default movement
            
            for part in parts:
                if part.startswith('TEMP:'):
                    temp = float(part.replace('TEMP:', ''))
                elif part.startswith('GPS:'):
                    gps = part.replace('GPS:', '')
                elif part.startswith('MOV:'):
                    movement = float(part.replace('MOV:', ''))
            
            # Use default values if parsing failed
            if temp is None:
                temp = random.uniform(37.5, 40.5)
            if gps is None:
                gps = f"{random.uniform(40.0, 42.0):.4f},{random.uniform(-75.0, -73.0):.4f}"
            
            return {
                'temperature': temp,
                'location': gps,
                'movement': movement
            }
        except Exception as e:
            print(f"Error parsing Arduino data: {e}")
            return self.generate_mock_data()
    
    def generate_mock_data(self):
        """Generate realistic mock data when Arduino is not available"""
        return {
            'temperature': random.uniform(37.5, 41.0),
            'location': f"{random.uniform(40.0, 42.0):.4f},{random.uniform(-75.0, -73.0):.4f}",
            'movement': random.uniform(1.0, 15.0)
        }
    
    def close(self):
        """Close Arduino connection"""
        if self.serial_conn and self.is_connected:
            self.serial_conn.close()
            self.is_connected = False

# Initialize Arduino interface
arduino = ArduinoInterface()

def init_db():
    """Initialize the SQLite database with enhanced user system"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Users table for login/signup
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS livestock_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            animal_id TEXT NOT NULL,
            temperature REAL NOT NULL,
            movement REAL NOT NULL,
            timestamp TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            location TEXT NOT NULL,
            alert_triggered BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            animal_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            value REAL NOT NULL,
            threshold REAL NOT NULL,
            timestamp TEXT NOT NULL,
            resolved BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            animal_id TEXT NOT NULL,
            animal_type TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            last_seen TEXT,
            battery_level TEXT DEFAULT '100%',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_animal_time ON livestock_readings(animal_id, timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_temperature ON livestock_readings(temperature)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts ON alerts(animal_id, resolved, timestamp)')
    
    # Insert default admin user if not exists
    admin_password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, email, full_name, role) 
        VALUES (?, ?, ?, ?, ?)
    ''', ('admin', admin_password_hash, 'admin@livestock.com', 'System Administrator', 'admin'))
    
    # Insert sample devices
    for device in SAMPLE_DEVICES:
        cursor.execute('''
            INSERT OR IGNORE INTO devices (device_id, animal_id, animal_type, status, battery_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (device['device_id'], device['animal_id'], device['animal_type'], device['status'], device['battery']))
    
    # Insert some initial readings
    cursor.execute('SELECT COUNT(*) FROM livestock_readings')
    if cursor.fetchone()[0] == 0:
        for reading in SAMPLE_READINGS:
            lat, lng = reading['location'].split(',')
            cursor.execute('''
                INSERT INTO livestock_readings 
                (device_id, animal_id, temperature, movement, timestamp, latitude, longitude, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reading['device_id'], reading['animal_id'], reading['temperature'], 
                reading['movement'], datetime.now().isoformat(), lat, lng, reading['location']
            ))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    return hash_password(password) == password_hash

def create_session(username):
    session_id = secrets.token_hex(16)
    USER_SESSIONS[session_id] = {
        'username': username,
        'created_at': datetime.now().isoformat()
    }
    return session_id

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return user
    return None

def check_alerts(device_id, animal_id, temperature, movement, timestamp):
    """Check for alert conditions and create alerts"""
    alerts_triggered = []
    
    # Fever alert
    if temperature > 39.5:
        alert_data = {
            'device_id': device_id,
            'animal_id': animal_id,
            'alert_type': 'fever',
            'message': f'High temperature detected: {temperature}°C',
            'value': temperature,
            'threshold': 39.5,
            'timestamp': timestamp
        }
        alerts_triggered.append(alert_data)
    
    # Low movement alert
    if movement < 5.0:
        alert_data = {
            'device_id': device_id,
            'animal_id': animal_id,
            'alert_type': 'movement',
            'message': f'Low movement detected: {movement}',
            'value': movement,
            'threshold': 5.0,
            'timestamp': timestamp
        }
        alerts_triggered.append(alert_data)
    
    # Save alerts to database
    if alerts_triggered:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for alert in alerts_triggered:
            cursor.execute('''
                INSERT INTO alerts (device_id, animal_id, alert_type, message, value, threshold, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert['device_id'], alert['animal_id'], alert['alert_type'],
                alert['message'], alert['value'], alert['threshold'], alert['timestamp']
            ))
        
        conn.commit()
        conn.close()
        
        send_alert_notifications(alerts_triggered)
    
    return alerts_triggered

def send_alert_notifications(alerts):
    """Send email notifications for alerts"""
    try:
        subject = f"Livestock Health Alert - {len(alerts)} New Alert(s)"
        
        message = MIMEMultipart()
        message['From'] = EMAIL_CONFIG['email']
        message['To'] = EMAIL_CONFIG['admin_email']
        message['Subject'] = subject
        
        body = "Livestock Health Monitoring System - ALERTS\n\n"
        body += "The following alerts have been triggered:\n\n"
        
        for alert in alerts:
            body += f"Animal: {alert['animal_id']}\n"
            body += f"Alert Type: {alert['alert_type'].upper()}\n"
            body += f"Message: {alert['message']}\n"
            body += f"Time: {alert['timestamp']}\n"
            body += "="*50 + "\n"
        
        body += "\nPlease check the dashboard for more details."
        
        message.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(message)
        server.quit()
        
        print(f"Alert notifications sent for {len(alerts)} alerts")
        
    except Exception as e:
        print(f"Failed to send email alerts: {e}")

# Arduino Data Collection Thread
def arduino_data_collector():
    """Background thread to collect data from Arduino"""
    while True:
        try:
            # Read data from Arduino
            sensor_data = arduino.read_sensor_data()
            
            # Use a random device for simulation
            device = random.choice(SAMPLE_DEVICES)
            
            # Prepare data for storage
            reading_data = {
                'device_id': device['device_id'],
                'animal_id': device['animal_id'],
                'temperature': sensor_data['temperature'],
                'movement': sensor_data['movement'],
                'timestamp': datetime.now().isoformat(),
                'location': sensor_data['location']
            }
            
            # Store in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Parse location
            lat, lng = 0.0, 0.0
            if sensor_data['location'] and ',' in sensor_data['location']:
                try:
                    coords = sensor_data['location'].split(',')
                    if len(coords) >= 2:
                        lat, lng = float(coords[0].strip()), float(coords[1].strip())
                except:
                    pass
            
            cursor.execute('''
                INSERT INTO livestock_readings 
                (device_id, animal_id, temperature, movement, timestamp, latitude, longitude, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reading_data['device_id'], reading_data['animal_id'], 
                reading_data['temperature'], reading_data['movement'],
                reading_data['timestamp'], lat, lng, reading_data['location']
            ))
            
            # Update device last seen
            cursor.execute('''
                UPDATE devices SET last_seen = ? WHERE device_id = ?
            ''', (reading_data['timestamp'], reading_data['device_id']))
            
            conn.commit()
            conn.close()
            
            # Check for alerts
            check_alerts(
                reading_data['device_id'], reading_data['animal_id'],
                reading_data['temperature'], reading_data['movement'],
                reading_data['timestamp']
            )
            
            print(f"Collected data: {reading_data}")
            
        except Exception as e:
            print(f"Error in data collection: {e}")
        
        time.sleep(30)  # Collect data every 30 seconds

# Authentication middleware
def require_auth(f):
    def decorated(*args, **kwargs):
        session_id = request.headers.get('Authorization')
        if not session_id or session_id not in USER_SESSIONS:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# API Routes
@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User registration endpoint"""
    data = request.get_json()
    
    required_fields = ['username', 'password', 'email', 'full_name']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(data['password'])
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, full_name)
            VALUES (?, ?, ?, ?)
        ''', (data['username'], password_hash, data['email'], data['full_name']))
        
        conn.commit()
        session_id = create_session(data['username'])
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "session_id": session_id,
            "user": {
                "username": data['username'],
                "email": data['email'],
                "full_name": data['full_name'],
                "role": "user"
            }
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username already exists"}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = authenticate_user(username, password)
    if user:
        session_id = create_session(username)
        
        # Update last login
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE username = ?', 
                      (datetime.now().isoformat(), username))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "session_id": session_id,
            "user": {
                "username": user['username'],
                "email": user['email'],
                "full_name": user['full_name'],
                "role": user['role']
            }
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session_id = request.headers.get('Authorization')
    if session_id and session_id in USER_SESSIONS:
        del USER_SESSIONS[session_id]
    
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from Arduino devices"""
    device_id = request.headers.get('Device-ID')
    auth_token = request.headers.get('Authorization')
    
    if not device_id or not auth_token:
        return jsonify({"error": "Missing device headers"}), 401
    
    if device_id not in AUTH_TOKENS or AUTH_TOKENS[device_id] != auth_token:
        return jsonify({"error": "Invalid device credentials"}), 401
    
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    required_fields = ['animal_id', 'temperature', 'movement']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        animal_id = str(data['animal_id'])
        temperature = float(data['temperature'])
        movement = float(data['movement'])
        timestamp = data.get('timestamp', datetime.now().isoformat())
        location = data.get('location', 'Unknown Location')
        
        lat, lng = 0.0, 0.0
        if location and ',' in location:
            try:
                coords = location.split(',')
                if len(coords) >= 2:
                    lat, lng = float(coords[0].strip()), float(coords[1].strip())
            except:
                pass
        
        if temperature < 20 or temperature > 50:
            return jsonify({"error": "Temperature out of range"}), 400
        
        if movement < 0:
            return jsonify({"error": "Movement cannot be negative"}), 400
            
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data types: {str(e)}"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO livestock_readings 
            (device_id, animal_id, temperature, movement, timestamp, latitude, longitude, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (device_id, animal_id, temperature, movement, timestamp, lat, lng, location))
        
        cursor.execute('''
            UPDATE devices SET last_seen = ? WHERE device_id = ?
        ''', (datetime.now().isoformat(), device_id))
        
        conn.commit()
        reading_id = cursor.lastrowid
        
        alerts = check_alerts(device_id, animal_id, temperature, movement, timestamp)
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()
    
    response = {
        "message": "Data received successfully",
        "reading_id": reading_id,
        "alerts_triggered": len(alerts)
    }
    
    return jsonify(response), 201

@app.route('/api/readings', methods=['GET'])
@require_auth
def get_readings():
    """Get livestock readings with optional filtering"""
    animal_id = request.args.get('animal_id')
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT * FROM livestock_readings 
        WHERE timestamp >= datetime('now', ?)
    '''
    params = [f'-{hours} hours']
    
    if animal_id:
        query += ' AND animal_id = ?'
        params.append(animal_id)
    
    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    readings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(readings), 200

@app.route('/api/alerts', methods=['GET'])
@require_auth
def get_alerts():
    """Get alerts with optional filtering"""
    resolved = request.args.get('resolved', type=bool)
    hours = request.args.get('hours', 24, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT * FROM alerts 
        WHERE timestamp >= datetime('now', ?)
    '''
    params = [f'-{hours} hours']
    
    if resolved is not None:
        query += ' AND resolved = ?'
        params.append(resolved)
    
    query += ' ORDER BY timestamp DESC'
    
    cursor.execute(query, params)
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(alerts), 200

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
@require_auth
def resolve_alert(alert_id):
    """Mark an alert as resolved"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE alerts SET resolved = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Alert not found"}), 404
    
    conn.close()
    return jsonify({"message": "Alert resolved successfully"}), 200

@app.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Get dashboard statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total animals
    cursor.execute('SELECT COUNT(DISTINCT animal_id) FROM devices WHERE status = "active"')
    total_animals = cursor.fetchone()[0]
    
    # Active alerts
    cursor.execute('SELECT COUNT(*) FROM alerts WHERE resolved = 0 AND timestamp >= datetime("now", "-24 hours")')
    active_alerts = cursor.fetchone()[0]
    
    # Average temperature
    cursor.execute('SELECT AVG(temperature) FROM livestock_readings WHERE timestamp >= datetime("now", "-1 hour")')
    avg_temp = cursor.fetchone()[0] or 0
    
    # Recent readings count
    cursor.execute('SELECT COUNT(*) FROM livestock_readings WHERE timestamp >= datetime("now", "-1 hour")')
    recent_readings = cursor.fetchone()[0]
    
    # Device status
    cursor.execute('SELECT status, COUNT(*) FROM devices GROUP BY status')
    device_status = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        "total_animals": total_animals,
        "active_alerts": active_alerts,
        "average_temperature": round(avg_temp, 2),
        "recent_readings": recent_readings,
        "device_status": device_status
    }), 200

@app.route('/api/devices', methods=['GET'])
@require_auth
def get_devices():
    """Get all devices"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM devices ORDER BY created_at DESC')
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(devices), 200

@app.route('/api/devices', methods=['POST'])
@require_auth
def add_device():
    """Add a new device"""
    data = request.get_json()
    
    required_fields = ['device_id', 'animal_id', 'animal_type']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO devices (device_id, animal_id, animal_type, status, battery_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['device_id'], data['animal_id'], data['animal_type'],
            data.get('status', 'active'), data.get('battery_level', '100%')
        ))
        
        conn.commit()
        device_id = cursor.lastrowid
        
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "Device ID already exists"}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()
    
    return jsonify({"message": "Device added successfully", "id": device_id}), 201

@app.route('/api/devices/<string:device_id>', methods=['DELETE'])
@require_auth
def delete_device(device_id):
    """Delete a device"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
    conn.commit()
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Device not found"}), 404
    
    conn.close()
    return jsonify({"message": "Device deleted successfully"}), 200

@app.route('/api/arduino/status', methods=['GET'])
@require_auth
def get_arduino_status():
    """Get Arduino connection status"""
    return jsonify({
        "connected": arduino.is_connected,
        "port": ARDUINO_CONFIG['port'],
        "last_update": datetime.now().isoformat()
    }), 200

@app.route('/api/arduino/connect', methods=['POST'])
@require_auth
def connect_arduino():
    """Manually connect to Arduino"""
    success = arduino.connect()
    return jsonify({
        "success": success,
        "message": "Arduino connected successfully" if success else "Failed to connect to Arduino"
    }), 200 if success else 500

@app.route('/api/animals', methods=['GET'])
@require_auth
def get_animals():
    """Get all animals with their latest readings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT d.*, 
               lr.temperature as last_temperature,
               lr.movement as last_movement,
               lr.timestamp as last_reading_time,
               lr.location as last_location
        FROM devices d
        LEFT JOIN livestock_readings lr ON d.animal_id = lr.animal_id
        WHERE lr.timestamp = (SELECT MAX(timestamp) FROM livestock_readings WHERE animal_id = d.animal_id)
        OR lr.timestamp IS NULL
        ORDER BY d.animal_id
    ''')
    
    animals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(animals), 200

if __name__ == '__main__':
    init_db()
    
    # Start Arduino data collection thread
    data_thread = threading.Thread(target=arduino_data_collector, daemon=True)
    data_thread.start()
    
    print("Livestock Monitoring System Started")
    print("Database initialized with sample data")
    print("Access the dashboard at: http://localhost:5000")
    print("API endpoints available at: http://localhost:5000/api/")
    print("Arduino data collection started")
    
    app.run(debug=True, host='0.0.0.0', port=5000)