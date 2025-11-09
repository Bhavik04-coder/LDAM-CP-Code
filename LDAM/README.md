# Livestock Health Monitor Pro

Real-time livestock health monitoring system with temperature and GPS tracking.

## 🚀 Quick Start

### Windows
```bash
# Double-click start.bat
# Or run manually:
pip install -r requirements.txt
python app.py
```

### Linux/Mac
```bash
pip install -r requirements.txt
python app.py
```

Then open: **http://localhost:5000**

## ✨ Features

- 🌡️ **Real-time Temperature Monitoring** - Circular gauge with color-coded alerts
- 📊 **Interactive Charts** - Temperature trend visualization
- 📍 **GPS Tracking** - Location display with Google Maps integration
- 🔔 **Fever Detection** - Automatic alerts at 39.5°C threshold
- 📱 **Mobile Responsive** - Works on all devices
- 🎨 **Modern UI** - Dark & Light theme with smooth animations
- 🌓 **Theme Toggle** - Switch between dark and light modes

## 📋 Requirements

- Python 3.7+
- Arduino/ESP32 device with temperature sensor and GPS module
- USB cable for serial connection

## 🔧 Configuration

### Device Data Format
Your Arduino/ESP32 should send JSON via serial (115200 baud):

```json
{
  "temperature": 38.5,
  "latitude": 12.345678,
  "longitude": 98.765432
}
```

### Thresholds
Edit `app.py` to change:
```python
FEVER_THRESHOLD = 39.5  # Fever alert threshold
```

## 🎯 Two Applications Available

### 1. Web Application (Recommended)
- **File**: `app.py`
- **Features**: Full-featured with charts, animations, remote access
- **Start**: `python app.py` → Open `http://localhost:5000`

### 2. Desktop Application (Original)
- **File**: `LDAM-Proto.py`
- **Features**: Basic monitoring, local only
- **Start**: `python LDAM-Proto.py`

## 🆘 Troubleshooting

**Can't connect to device?**
- Close Arduino IDE Serial Monitor
- Click "Refresh Ports" button
- Try a different COM port
- Check USB cable

**No data showing?**
- Verify device sends JSON format
- Check baud rate is 115200
- Look at System Status card for errors

**Port access denied?**
- Close any program using the port
- Run as administrator (Windows)
- Check device permissions

## 📱 Mobile Access

Access from any device on your network:
```
http://YOUR_IP_ADDRESS:5000
```

Find your IP:
- Windows: `ipconfig`
- Linux/Mac: `ifconfig`
