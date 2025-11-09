import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import threading
import time
from datetime import datetime
import webbrowser

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg_color='#3498db', fg_color='white', width=120, height=40):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = self._adjust_color(bg_color, 1.15)
        self.fg_color = fg_color
        self.text = text

        self.rect = self.create_rounded_rect(0, 0, width, height, radius=8, fill=bg_color)
        self.text_id = self.create_text(width/2, height/2, text=text, fill=fg_color,
                                       font=('Segoe UI', 10, 'bold'))

        self.bind('<Button-1>', lambda e: self.command())
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2-radius,
            x1, y1+radius
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _adjust_color(self, color, factor):
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c * factor)) for c in rgb)
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

    def on_enter(self, e):
        self.itemconfig(self.rect, fill=self.hover_color)

    def on_leave(self, e):
        self.itemconfig(self.rect, fill=self.bg_color)

    def config_state(self, state):
        if state == 'disabled':
            self.itemconfig(self.rect, fill='#95a5a6')
            self.unbind('<Button-1>')
        else:
            self.itemconfig(self.rect, fill=self.bg_color)
            self.bind('<Button-1>', lambda e: self.command())


class LivestockMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Livestock Health Monitor Pro")
        self.root.geometry("1000x700")
        self.root.configure(bg='#1a1a2e')

        self.ser = None
        self.serial_lock = threading.Lock()
        self.read_thread = None

        self.sensor_data = {
            'temperature': None,
            'latitude': None,
            'longitude': None,
            'timestamp': None,
            'fever_status': 'NO DATA',
            'fever_alert': False,
            'connected': False,
            'error': None,
            'gps_available': False
        }

        self.FEVER_THRESHOLD = 39.5

        self.setup_ui()

        self.update_count = 0
        self._last_timestamp = None

        self.start_serial_thread()

    def setup_ui(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        main_container = tk.Frame(self.root, bg='#1a1a2e')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.create_header(main_container)
        self.create_connection_bar(main_container)

        content_frame = tk.Frame(main_container, bg='#1a1a2e')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        left_column = tk.Frame(content_frame, bg='#1a1a2e')
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        right_column = tk.Frame(content_frame, bg='#1a1a2e')
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.create_temperature_card(left_column)
        self.create_stats_card(left_column)
        self.create_location_card(right_column)
        self.create_system_info_card(right_column)

    def create_header(self, parent):
        header = tk.Frame(parent, bg='#1a1a2e')
        header.pack(fill=tk.X, pady=(0, 20))

        title_frame = tk.Frame(header, bg='#1a1a2e')
        title_frame.pack(side=tk.LEFT)

        icon_label = tk.Label(title_frame, text="🐄", font=('Segoe UI', 32), bg='#1a1a2e')
        icon_label.pack(side=tk.LEFT, padx=(0, 15))

        text_frame = tk.Frame(title_frame, bg='#1a1a2e')
        text_frame.pack(side=tk.LEFT)

        title = tk.Label(text_frame, text="Livestock Health Monitor",
                         font=('Segoe UI', 24, 'bold'), fg='#ffffff', bg='#1a1a2e')
        title.pack(anchor=tk.W)

        subtitle = tk.Label(text_frame, text="Real-time monitoring with AI-powered insights",
                            font=('Segoe UI', 11), fg='#7d8b99', bg='#1a1a2e')
        subtitle.pack(anchor=tk.W)

        self.status_dot = tk.Canvas(header, width=16, height=16, bg='#1a1a2e', highlightthickness=0)
        self.status_dot.pack(side=tk.RIGHT, padx=10)
        self.status_circle = self.status_dot.create_oval(2, 2, 14, 14, fill='#e74c3c', outline='')

    def create_connection_bar(self, parent):
        conn_frame = tk.Frame(parent, bg='#16213e', relief='flat', bd=0)
        conn_frame.pack(fill=tk.X, pady=(0, 15))

        inner_frame = tk.Frame(conn_frame, bg='#16213e')
        inner_frame.pack(fill=tk.X, padx=20, pady=15)

        left_side = tk.Frame(inner_frame, bg='#16213e')
        left_side.pack(side=tk.LEFT)
        tk.Label(left_side, text="Status:", font=('Segoe UI', 10, 'bold'),
                 fg='#7d8b99', bg='#16213e').pack(side=tk.LEFT, padx=(0, 10))
        self.connection_label = tk.Label(left_side, text="● Disconnected",
                                         font=('Segoe UI', 11, 'bold'),
                                         fg='#e74c3c', bg='#16213e')
        self.connection_label.pack(side=tk.LEFT)

        button_frame = tk.Frame(inner_frame, bg='#16213e')
        button_frame.pack(side=tk.RIGHT)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(button_frame, textvariable=self.port_var, width=12)
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.port_combo['values'] = self.list_serial_ports_devices()
        if self.port_combo['values']:
            self.port_var.set(self.port_combo['values'][0])
        else:
            self.port_var.set('COM5')

        self.connect_btn = ModernButton(button_frame, "Connect", self.connect_serial, bg_color='#27ae60')
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        self.disconnect_btn = ModernButton(button_frame, "Disconnect", self.disconnect_serial, bg_color='#e74c3c')
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        self.disconnect_btn.config_state('disabled')

        self.refresh_btn = ModernButton(button_frame, "Refresh", self.refresh_ports, bg_color='#3498db', width=100)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

    def create_temperature_card(self, parent):
        card = tk.Frame(parent, bg='#16213e', relief='flat', bd=0)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        header = tk.Frame(card, bg='#16213e')
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(header, text="🌡️", font=('Segoe UI', 20), bg='#16213e').pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(header, text="Temperature Monitor", font=('Segoe UI', 14, 'bold'),
                 fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)

        temp_container = tk.Frame(card, bg='#16213e')
        temp_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.temp_value = tk.Label(temp_container, text="--.-",
                                   font=('Segoe UI', 64, 'bold'),
                                   fg='#3498db', bg='#16213e')
        self.temp_value.pack()

        tk.Label(temp_container, text="degrees celsius",
                 font=('Segoe UI', 12), fg='#7d8b99', bg='#16213e').pack()

        badge_container = tk.Frame(card, bg='#16213e')
        badge_container.pack(pady=(10, 20))

        self.fever_status = tk.Label(badge_container, text="NO DATA",
                                    font=('Segoe UI', 12, 'bold'),
                                    fg='white', bg='#7f8c8d',
                                    padx=30, pady=12, relief='flat')
        self.fever_status.pack()

        self.last_update = tk.Label(card, text="Last update: Never",
                                   font=('Segoe UI', 9), fg='#7d8b99', bg='#16213e')
        self.last_update.pack(pady=(0, 15))

    def create_location_card(self, parent):
        card = tk.Frame(parent, bg='#16213e', relief='flat', bd=0)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        header = tk.Frame(card, bg='#16213e')
        header.pack(fill=tk.X, padx=20, pady=(20, 15))
        tk.Label(header, text="📍", font=('Segoe UI', 20), bg='#16213e').pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(header, text="Location Tracking", font=('Segoe UI', 14, 'bold'),
                 fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)

        self.location_type = tk.Label(header, text="", font=('Segoe UI', 9),
                                     fg='#7d8b99', bg='#16213e')
        self.location_type.pack(side=tk.RIGHT)

        gps_frame = tk.Frame(card, bg='#16213e')
        gps_frame.pack(fill=tk.X, padx=20, pady=10)

        lat_container = tk.Frame(gps_frame, bg='#1a1a2e')
        lat_container.pack(fill=tk.X, pady=5)
        tk.Label(lat_container, text="Latitude", font=('Segoe UI', 9, 'bold'),
                 fg='#7d8b99', bg='#1a1a2e').pack(anchor=tk.W, padx=15, pady=(10, 5))
        self.lat_value = tk.Label(lat_container, text="--",
                                 font=('Segoe UI', 12, 'bold'),
                                 fg='#ffffff', bg='#1a1a2e')
        self.lat_value.pack(anchor=tk.W, padx=15, pady=(0, 10))

        lon_container = tk.Frame(gps_frame, bg='#1a1a2e')
        lon_container.pack(fill=tk.X, pady=5)
        tk.Label(lon_container, text="Longitude", font=('Segoe UI', 9, 'bold'),
                 fg='#7d8b99', bg='#1a1a2e').pack(anchor=tk.W, padx=15, pady=(10, 5))
        self.lon_value = tk.Label(lon_container, text="--",
                                 font=('Segoe UI', 12, 'bold'),
                                 fg='#ffffff', bg='#1a1a2e')
        self.lon_value.pack(anchor=tk.W, padx=15, pady=(0, 10))

        map_btn_frame = tk.Frame(card, bg='#16213e')
        map_btn_frame.pack(pady=(10, 15))
        self.map_btn = ModernButton(map_btn_frame, "View on Map 🗺️", self.open_map, bg_color='#9b59b6', width=200)
        self.map_btn.pack()

    def create_stats_card(self, parent):
        card = tk.Frame(parent, bg='#16213e', relief='flat', bd=0)
        card.pack(fill=tk.X)

        header = tk.Frame(card, bg='#16213e')
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        tk.Label(header, text="📊 Statistics", font=('Segoe UI', 12, 'bold'),
                 fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)

        stats_container = tk.Frame(card, bg='#16213e')
        stats_container.pack(fill=tk.X, padx=20, pady=(0, 15))

        update_box = tk.Frame(stats_container, bg='#1a1a2e')
        update_box.pack(fill=tk.X, pady=5)
        tk.Label(update_box, text="Data Updates", font=('Segoe UI', 9),
                 fg='#7d8b99', bg='#1a1a2e').pack(anchor=tk.W, padx=15, pady=(10, 5))
        self.count_label = tk.Label(update_box, text="0", font=('Segoe UI', 16, 'bold'),
                                    fg='#3498db', bg='#1a1a2e')
        self.count_label.pack(anchor=tk.W, padx=15, pady=(0, 10))

    def create_system_info_card(self, parent):
        card = tk.Frame(parent, bg='#16213e', relief='flat', bd=0)
        card.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(card, bg='#16213e')
        header.pack(fill=tk.X, padx=20, pady=(15, 10))
        tk.Label(header, text="⚙️ System Info", font=('Segoe UI', 12, 'bold'),
                 fg='#ffffff', bg='#16213e').pack(side=tk.LEFT)

        info_container = tk.Frame(card, bg='#16213e')
        info_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        threshold_frame = tk.Frame(info_container, bg='#1a1a2e')
        threshold_frame.pack(fill=tk.X, pady=5)
        inner = tk.Frame(threshold_frame, bg='#1a1a2e')
        inner.pack(padx=15, pady=12)
        tk.Label(inner, text="Fever Threshold:", font=('Segoe UI', 9, 'bold'),
                 fg='#7d8b99', bg='#1a1a2e').pack(side=tk.LEFT)
        tk.Label(inner, text=f"{self.FEVER_THRESHOLD}°C", font=('Segoe UI', 10, 'bold'),
                 fg='#e74c3c', bg='#1a1a2e').pack(side=tk.LEFT, padx=(5, 15))
        tk.Label(inner, text="Warning:", font=('Segoe UI', 9, 'bold'),
                 fg='#7d8b99', bg='#1a1a2e').pack(side=tk.LEFT)
        tk.Label(inner, text=f"{self.FEVER_THRESHOLD - 0.5}°C", font=('Segoe UI', 10, 'bold'),
                 fg='#f39c12', bg='#1a1a2e').pack(side=tk.LEFT, padx=5)

        error_frame = tk.Frame(info_container, bg='#1a1a2e')
        error_frame.pack(fill=tk.X, pady=5)
        self.error_label = tk.Label(error_frame, text="✓ No errors",
                                   font=('Segoe UI', 9), fg='#27ae60',
                                   bg='#1a1a2e', anchor=tk.W, padx=15, pady=12)
        self.error_label.pack(fill=tk.X)

        ports_frame = tk.Frame(info_container, bg='#1a1a2e')
        ports_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(ports_frame, text="Available Ports", font=('Segoe UI', 9, 'bold'),
                 fg='#7d8b99', bg='#1a1a2e').pack(anchor=tk.W, padx=15, pady=(10, 5))
        self.ports_text = tk.Text(ports_frame, height=4, font=('Consolas', 9),
                                 bg='#0f1419', fg='#7d8b99', relief='flat',
                                 padx=10, pady=5)
        self.ports_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

    def open_map(self):
        lat = self.sensor_data.get('latitude')
        lon = self.sensor_data.get('longitude')

        if lat and lon:
            url = f"https://www.google.com/maps?q={lat},{lon}"
            webbrowser.open(url)
        else:
            messagebox.showinfo("No Location", "GPS data not available yet")

    def check_fever_status(self, temperature):
        try:
            if temperature is None:
                return 'NO DATA', False
            if temperature >= self.FEVER_THRESHOLD:
                return 'FEVER DETECTED!', True
            if temperature >= self.FEVER_THRESHOLD - 0.5:
                return 'ELEVATED TEMP', False
            return 'NORMAL', False
        except Exception:
            return 'ERROR', False

    def list_serial_ports_devices(self):
        devices = [p.device for p in serial.tools.list_ports.comports()]
        return devices

    def list_serial_ports_descriptions(self):
        return [f"{p.device} - {p.description}" for p in serial.tools.list_ports.comports()]

    def update_ports_display(self):
        ports = self.list_serial_ports_descriptions()
        self.ports_text.delete(1.0, tk.END)
        if ports:
            for p in ports:
                self.ports_text.insert(tk.END, f"• {p}\n")
        else:
            self.ports_text.insert(tk.END, "No serial ports detected")

        devices = self.list_serial_ports_devices()
        self.port_combo['values'] = devices
        if devices and not self.port_var.get():
            self.port_var.set(devices[0])

    def refresh_ports(self):
        self.update_ports_display()
        messagebox.showinfo("Refreshed", "Port list updated")

    def connect_serial(self):
        port = self.port_var.get().strip() or 'COM5'
        try:
            self.connect_btn.config_state('disabled')
            self.connection_label.config(text="● Connecting...", fg='#f39c12')

            if self.ser and getattr(self.ser, 'is_open', False):
                try:
                    self.ser.close()
                except Exception:
                    pass
                time.sleep(0.5)

            self.ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(1.5)

            with self.serial_lock:
                self.sensor_data['connected'] = True
                self.sensor_data['error'] = None

            self.connection_label.config(text="● Connected", fg='#27ae60')
            self.status_dot.itemconfig(self.status_circle, fill='#27ae60')
            self.disconnect_btn.config_state('normal')
            self.connect_btn.config_state('disabled')

            messagebox.showinfo("Success", f"Connected to {port} successfully!")

        except serial.SerialException as e:
            error_msg = str(e)
            self.connection_label.config(text="● Connection Failed", fg='#e74c3c')
            self.connect_btn.config_state('normal')

            if "Access is denied" in error_msg or "could not open port" in error_msg.lower():
                messagebox.showerror("Connection Error",
                                     f"Failed to connect to {port}: {error_msg}\n\n"
                                     "Troubleshooting:\n"
                                     "1. Close Arduino IDE/Serial Monitor\n"
                                     "2. Unplug and replug USB\n"
                                     "3. Check permissions (run as admin on Windows)\n"
                                     "4. Try a different port")
            else:
                messagebox.showerror("Connection Error", f"Failed to connect: {error_msg}")

        except Exception as e:
            self.connection_label.config(text="● Error", fg='#e74c3c')
            self.connect_btn.config_state('normal')
            messagebox.showerror("Error", f"Unexpected error: {e}")

    def disconnect_serial(self):
        try:
            if self.ser and getattr(self.ser, 'is_open', False):
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None

            with self.serial_lock:
                self.sensor_data['connected'] = False
                self.sensor_data['error'] = 'Manually disconnected'

            self.connection_label.config(text="● Disconnected", fg='#e74c3c')
            self.status_dot.itemconfig(self.status_circle, fill='#e74c3c')
            self.connect_btn.config_state('normal')
            self.disconnect_btn.config_state('disabled')

        except Exception as e:
            messagebox.showerror("Error", f"Error disconnecting: {e}")

    def read_serial_data(self):
        while True:
            try:
                if self.ser is None or not getattr(self.ser, 'is_open', False):
                    time.sleep(0.5)
                    continue

                if self.ser.in_waiting <= 0:
                    time.sleep(0.1)
                    continue

                raw = self.ser.readline()
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
                    with self.serial_lock:
                        self.sensor_data['error'] = 'Invalid data format (JSON expected)'
                    continue

                with self.serial_lock:
                    if 'temperature' in parsed:
                        self.sensor_data['temperature'] = parsed.get('temperature')
                        self.sensor_data['latitude'] = parsed.get('latitude')
                        self.sensor_data['longitude'] = parsed.get('longitude')
                        self.sensor_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.sensor_data['connected'] = True
                        self.sensor_data['error'] = None

                        self.sensor_data['gps_available'] = (
                            self.sensor_data['latitude'] is not None and
                            self.sensor_data['longitude'] is not None
                        )

                        status, alert = self.check_fever_status(self.sensor_data['temperature'])
                        self.sensor_data['fever_status'] = status
                        self.sensor_data['fever_alert'] = alert

            except Exception as e:
                print(f"Serial communication error: {e}")
                with self.serial_lock:
                    self.sensor_data['connected'] = False
                    self.sensor_data['error'] = str(e)
                try:
                    if self.ser and getattr(self.ser, 'is_open', False):
                        self.ser.close()
                except Exception:
                    pass
                self.ser = None
                time.sleep(2)

    def update_ui(self):
        with self.serial_lock:
            data = self.sensor_data.copy()

        if data.get('connected'):
            self.connection_label.config(text="● Connected", fg='#27ae60')
            self.status_dot.itemconfig(self.status_circle, fill='#27ae60')
            self.connect_btn.config_state('disabled')
            self.disconnect_btn.config_state('normal')
        else:
            self.connection_label.config(text="● Disconnected", fg='#e74c3c')
            self.status_dot.itemconfig(self.status_circle, fill='#e74c3c')
            self.connect_btn.config_state('normal')
            self.disconnect_btn.config_state('disabled')

        temp = data.get('temperature')
        if temp is not None:
            try:
                temp_float = float(temp)
                self.temp_value.config(text=f"{temp_float:.1f}")
                if data.get('fever_alert'):
                    self.temp_value.config(fg='#e74c3c')
                elif data.get('fever_status', '').startswith('ELEVATED'):
                    self.temp_value.config(fg='#f39c12')
                elif data.get('fever_status') == 'NORMAL':
                    self.temp_value.config(fg='#27ae60')
                else:
                    self.temp_value.config(fg='#3498db')
            except Exception:
                self.temp_value.config(text="--.-", fg='#7d8b99')
        else:
            self.temp_value.config(text="--.-", fg='#7d8b99')

        fs = data.get('fever_status', 'NO DATA')
        self.fever_status.config(text=fs)
        if data.get('fever_alert'):
            self.fever_status.config(bg='#e74c3c', fg='white')
        elif fs.startswith('ELEVATED'):
            self.fever_status.config(bg='#f39c12', fg='white')
        elif fs == 'NORMAL':
            self.fever_status.config(bg='#27ae60', fg='white')
        else:
            self.fever_status.config(bg='#7f8c8d', fg='white')

        if data.get('gps_available') and data.get('latitude') and data.get('longitude'):
            try:
                self.lat_value.config(text=f"{float(data['latitude']):.6f}")
                self.lon_value.config(text=f"{float(data['longitude']):.6f}")
                self.location_type.config(text="📡 GPS Active", fg='#27ae60')
            except Exception:
                self.lat_value.config(text=str(data.get('latitude', '--')))
                self.lon_value.config(text=str(data.get('longitude', '--')))
                self.location_type.config(text="📡 GPS Error", fg='#e74c3c')
        else:
            self.lat_value.config(text="--")
            self.lon_value.config(text="--")
            self.location_type.config(text="⏳ Waiting for GPS", fg='#7d8b99')

        if data.get('timestamp'):
            self.last_update.config(text=f"Last update: {data['timestamp']}")
            if data['timestamp'] != self._last_timestamp:
                self.update_count += 1
                self.count_label.config(text=str(self.update_count))
                self._last_timestamp = data['timestamp']

        if data.get('error'):
            self.error_label.config(text=f"⚠ {data['error']}", fg='#e74c3c')
        else:
            self.error_label.config(text="✓ No errors", fg='#27ae60')

        now = time.time()
        if not hasattr(self, "_last_ports_refresh") or now - getattr(self, "_last_ports_refresh") > 5:
            self.update_ports_display()
            self._last_ports_refresh = now

        self.root.after(1000, self.update_ui)

    def start_serial_thread(self):
        if self.read_thread is None or not self.read_thread.is_alive():
            self.read_thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.read_thread.start()
            
        self.root.after(1000, self.update_ui)
        self.update_ports_display()

    def on_closing(self):
        try:
            if self.ser and getattr(self.ser, 'is_open', False):
                self.ser.close()
        except Exception:
            pass
        self.root.destroy()

def main():
    try:
        root = tk.Tk()
        app = LivestockMonitor(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")
        try:
            messagebox.showerror("Fatal Error", f"The application encountered an error:\n{e}")
        except Exception:
            pass

if __name__ == "__main__":
    main()