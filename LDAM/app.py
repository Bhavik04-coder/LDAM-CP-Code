from flask import Flask, render_template, jsonify, request
import serial
import serial.tools.list_ports
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Global sensor data storage
sensor_data = {
    'temperature': None,
    'latitude': None,
    'longitude': None,
    'timestamp': None,
    'fever_status': 'NO DATA',
    'fever_alert': False,
    'connected': False,
    'error': None,
    'gps_available': False,
    'update_count': 0
}

FEVER_THRESHOLD = 39.5
ser = None
serial_lock = threading.Lock()

def check_fever_status(temperature):
    try:
        if temperature is None:
            return 'NO DATA', False
        if temperature >= FEVER_THRESHOLD:
            return 'FEVER DETECTED!', True
        if temperature >= FEVER_THRESHOLD - 0.5:
            return 'ELEVATED TEMP', False
        return 'NORMAL', False
    except Exception:
        return 'ERROR', False

def read_serial_data():
    global ser, sensor_data
    while True:
        try:
            if ser is None or not getattr(ser, 'is_open', False):
                time.sleep(0.5)
                continue

            if ser.in_waiting <= 0:
                time.sleep(0.1)
                continue

            raw = ser.readline()
            if not raw:
                continue

            try:
                line = raw.decode('utf-8', errors='replace').strip()
            except Exception:
                line = str(raw)

            if not line:
                continue

            print(f"Raw data received: {line}")

            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                with serial_lock:
                    sensor_data['error'] = 'Invalid data format (JSON expected)'
                continue

            with serial_lock:
                if 'temperature' in parsed:
                    sensor_data['temperature'] = parsed.get('temperature')
                    sensor_data['latitude'] = parsed.get('latitude')
                    sensor_data['longitude'] = parsed.get('longitude')
                    sensor_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    sensor_data['connected'] = True
                    sensor_data['error'] = None
                    sensor_data['update_count'] += 1

                    sensor_data['gps_available'] = (
                        sensor_data['latitude'] is not None and
                        sensor_data['longitude'] is not None
                    )

                    status, alert = check_fever_status(sensor_data['temperature'])
                    sensor_data['fever_status'] = status
                    sensor_data['fever_alert'] = alert

        except Exception as e:
            print(f"Serial communication error: {e}")
            with serial_lock:
                sensor_data['connected'] = False
                sensor_data['error'] = str(e)
            try:
                if ser and getattr(ser, 'is_open', False):
                    ser.close()
            except Exception:
                pass
            ser = None
            time.sleep(2)

# Start serial reading thread
serial_thread = threading.Thread(target=read_serial_data, daemon=True)
serial_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    with serial_lock:
        data = sensor_data.copy()
    return jsonify(data)

@app.route('/api/ports')
def get_ports():
    ports = [{'device': p.device, 'description': p.description} 
             for p in serial.tools.list_ports.comports()]
    return jsonify(ports)

@app.route('/api/connect', methods=['POST'])
def connect():
    global ser
    port = request.json.get('port', 'COM5')
    
    try:
        if ser and getattr(ser, 'is_open', False):
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(0.5)

        ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(1.5)

        with serial_lock:
            sensor_data['connected'] = True
            sensor_data['error'] = None

        return jsonify({'success': True, 'message': f'Connected to {port}'})

    except serial.SerialException as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    global ser
    try:
        if ser and getattr(ser, 'is_open', False):
            try:
                ser.close()
            except Exception:
                pass
        ser = None

        with serial_lock:
            sensor_data['connected'] = False
            sensor_data['error'] = 'Manually disconnected'

        return jsonify({'success': True, 'message': 'Disconnected'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
