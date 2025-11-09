# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install
```bash
pip install -r requirements.txt
```

### Step 2: Run
```bash
# Windows: Double-click start.bat
# Or manually:
python app.py
```

### Step 3: Open Browser
```
http://localhost:5000
```

## 🎯 Using the Dashboard

### Connect to Device
1. Select your COM port from dropdown
2. Click **"Connect"** button
3. Status indicator turns green when connected

### Change Theme
- Click the **moon/sun icon** in top-right corner
- Toggle between dark and light modes
- Theme preference is saved automatically

### Monitor Temperature
- **Circular Gauge**: Shows current temperature
- **Color Codes**:
  - 🟢 Green = Normal (< 39.0°C)
  - 🟠 Orange = Elevated (39.0-39.4°C)
  - 🔴 Red = Fever (≥ 39.5°C)

### View Charts
- Real-time temperature trend
- Click **1H**, **6H**, or **24H** for time range

### Track Location
- GPS coordinates displayed
- Click **"View on Google Maps"** to see location

### Check Statistics
- Total updates
- Normal/Warning/Fever counts
- System status

## 🔧 Troubleshooting

### Can't Find Port?
→ Click **"Refresh Ports"** button

### Connection Failed?
→ Close Arduino IDE Serial Monitor
→ Try different COM port

### No Data?
→ Check device sends JSON:
```json
{"temperature": 38.5, "latitude": 12.34, "longitude": 56.78}
```

## 📱 Mobile Access

Access from phone/tablet:
```
http://YOUR_IP_ADDRESS:5000
```

Find IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)

## 🖥️ Desktop App

For original Tkinter app:
```bash
python LDAM-Proto.py
```

## 💡 Tips

- Dashboard updates every second automatically
- Keep browser tab open for continuous monitoring
- All stats reset when you refresh the page
- Can't use both apps on same port simultaneously
