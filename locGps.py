import serial
import threading
import time
import sqlite3
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE = 'gps_data.db'

# https://chatgpt.com/share/68120961-e7a8-8001-b7d7-7cf6b020a46f
# Create table if not exists
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS location (
                    id INTEGER PRIMARY KEY,
                    time TEXT,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def save_location(time, lat, lon, alt):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO location (time, latitude, longitude, altitude) VALUES (?, ?, ?, ?)",
              (time, lat, lon, alt))
    conn.commit()
    conn.close()

def parse_gpgga(sentence):
    if not sentence.startswith("$GPGGA"):
        return None
    parts = sentence.strip().split(",")
    if len(parts) < 10:
        return None
    try:
        raw_lat = parts[2]
        raw_lon = parts[4]
        lat = float(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
        if parts[3] == 'S':
            lat *= -1
        lon = float(raw_lon[:3]) + float(raw_lon[3:]) / 60.0
        if parts[5] == 'W':
            lon *= -1
        return {
            "time": parts[1],
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "altitude": float(parts[9])
        }
    except:
        return None

def gps_reader():
    try:
        ser = serial.Serial('COM4', 115200, timeout=1)
        print("GPS thread started")
        while True:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line.startswith("$GPGGA"):
                parsed = parse_gpgga(line)
                if parsed:
                    print("Parsed GPGGA:", parsed)
                    save_location(parsed['time'], parsed['latitude'], parsed['longitude'], parsed['altitude'])
            time.sleep(0.5)
    except Exception as e:
        print("GPS read error:", e)

@app.route('/send-location')
def send_location():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT time, latitude, longitude, altitude FROM location ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({
            "time": row[0],
            "latitude": row[1],
            "longitude": row[2],
            "altitude": row[3]
        })
    else:
        return jsonify({"error": "No data"}), 404

if __name__ == '__main__':
    init_db()
    threading.Thread(target=gps_reader, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
