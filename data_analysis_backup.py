# ✅ Updated Flask App with Three Layers:
# 1. First Layer: Detection Maps (URL: /)
# 2. Second Layer: Charts (/charts)
# 3. Third Layer: Detection Tables (/detection)

from flask import Flask, render_template_string, url_for, request

import requests
import json
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import pandas as pd
import matplotlib.image as mpimg
import sqlite3

MALAYSIA_TZ = timezone(timedelta(hours=8))
app = Flask(__name__)
received_data = []  

API_TOKEN = "083ff613-961c-4da0-9df2-59805368af6f"
WEBHOOK_ID = "9c5e82ec-4ecc-433b-a176-c56955ea74b0"

API_URL = f"https://webhook.site/token/{WEBHOOK_ID}/requests?sorting=newest"

headers = {
    "api-key": API_TOKEN,
    "Accept": "application/json"
}

# ---------------------- HTML Templates ----------------------

FIRST_LAYER_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>🛡️First Layer: Detection Maps</title>
    <meta http-equiv="refresh" content="5">

    <style>
    body {
        font-family: 'Times New Roman', Times, serif;
        padding: 20px;
        margin: 0 auto;
        max-width: 1300px;
    }

    h1 {
        font-size: 38px;
        text-align: center;
        margin-bottom: 10px;
    }

    .time {
        text-align: right;
        color: gray;
        font-size: 0.9em;
        margin-bottom: 10px;
    }

    .map-row {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        flex-wrap: nowrap;
        margin-top: 30px;
    }

    .map-box {
        flex: 1;
        max-width: 640px;     /* Keeps both maps in balance */
        min-width: 400px;
        text-align: center;
    }

    h2 {
        font-size: 20px;
        margin-bottom: 10px;
    }

    img {
        width: 100%;          /* Responsive width within the box */
        height: auto;         /* Keep correct aspect ratio */
        border: 1px solid #ccc;
        max-height: 450px;    /* Prevent from growing too tall */
    }

    .nav {
        text-align: center;
        margin-top: 40px;
        font-size: 18px;
    }

    .nav a {
        margin: 0 20px;
        text-decoration: underline;
    }
</style>

</head>
<body>
    <h1>📍Mediveil Real-time Detection Maps (Coordinates)</h1>
    <div class="time">Last updated: {{ last_update }}</div>


    <div class="map-row">
    <div class="map-box">
        <h2>🩸 Bloodstain Detection Map</h2>
       <img src="{{ url_for('static', filename='blood_detection_map.png') }}" style="max-width: 95%; height: auto; max-height: 400px;">

    </div>
    <div class="map-box">
    <h2>🚷 Unauthorized Person Detection Map</h2>
    <img src="{{ url_for('static', filename='unauthorized_detection_map.png') }}" style="max-width: 95%; height: auto; max-height: 400px;">
</div>

</div> <!-- Close map-row -->

    </div>
    <div style="text-align: center; margin-top: 40px; font-size: 18px;">
        <a href="/" style="margin: 0 20px; text-decoration: underline;">🗺Maps</a>|
        <a href="/charts" style="margin: 0 20px; text-decoration: underline;">📊Charts</a>|
        <a href="/detection" style="margin: 0 20px; text-decoration: underline;">📋Detections</a>|
    </div>
</body>
</html>
"""
SECOND_LAYER_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>🛡️Second Layer: Summary Chart Insights</title>
    <meta http-equiv="refresh" content="15">
    <style>
        body { font-family: 'Times New Roman', Times, serif; padding: 20px; }
        h1 { font-size: 42px; text-align: center; margin-bottom: 10px; }
        .time { text-align: right; color: gray; font-size: 0.9em; margin-bottom: 10px; }
        .chart-row { display: flex; justify-content: center; gap: 40px; flex-wrap: wrap; margin-top: 40px; }
        .chart-box { flex: 1; min-width: 400px; text-align: center; }
        h2 { text-align: center; }
        img { max-width: 100%; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>📊Mediveil Charts Summary Dashboard (1 HOUR)</h1>
    <div class="time">Last updated: {{ last_update }}</div>

    <div class="chart-row">
        <div class="chart-box">
            <h2>👣 People Traffic per 10-MINUTES</h2>
            <img src="{{ url_for('static', filename='person_10min_chart.png') }}">
        </div>
        <div class="chart-box">
            <h2>🚷 Unauthorized Person per 10-MINUTES</h2>
            <img src="{{ url_for('static', filename='unauthorized_10min_chart.png') }}">
        </div>
    </div>
    <div style="text-align: center; margin-top: 40px; font-size: 18px;">
        <a href="/" style="margin: 0 20px; text-decoration: underline;">🗺Maps</a>|
        <a href="/charts" style="margin: 0 20px; text-decoration: underline;">📊Charts</a>|
        <a href="/detection" style="margin: 0 20px; text-decoration: underline;">📋Detections</a>|
    </div>
</body>
</html>
"""

THIRD_LAYER_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>🛡️Third Layer: Real-Time Camera Detection</title>
    <style>
        body {
            font-family: 'Times New Roman', Times, serif;
            padding: 20px;
        }
        .time {
            text-align: right;
            color: gray;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .table-row {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            flex-wrap: wrap;
        }
        .table-container {
            flex: 1;
            min-width: 400px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: center;
        }
        th {
            background: #f2f2f2;
        }
        h1 {
            font-size: 42px;
            text-align: center;
            margin-bottom: 10px;
        }
        .shield-icon {
            font-size: 60px;
            color: #d32f2f;
            vertical-align: middle;
        }
        h2 {
            text-align: center;
        }
    </style>
    <meta http-equiv="refresh" content="5">
</head>
<body>
    <h1>
        <span style="margin-left: 10px;">🛡️Mediveil Real-time Detection Dashboard</span>
    </h1>
    </div>
    <div style="text-align: center; margin-top: 40px; font-size: 18px;">
        <a href="/" style="margin: 0 20px; text-decoration: underline;">🗺Maps</a>|
        <a href="/charts" style="margin: 0 20px; text-decoration: underline;">📊Charts</a>|
        <a href="/detection" style="margin: 0 20px; text-decoration: underline;">📋Detections</a>|
    </div>
    <div class="time">Last updated: {{ last_update }}</div>
    <div class="table-row">
        <div class="table-container">
            <h2>🩸 Bloodstain Detection</h2>
            {% if blood_records %}
            <table><thead><tr><th>Confidence</th><th>Coordinates</th><th>Timestamp</th></tr></thead>
            <tbody>{% for r in blood_records %}<tr><td>{{ r.confidence }}</td><td>{{ r.coordinates }}</td><td>{{ r.created_at }}</td></tr>{% endfor %}</tbody>
            </table>
            {% else %}<p>No bloodstain data received.</p>{% endif %}
        </div>
        <div class="table-container">
            <h2>🚷 Unauthorized Person Detection</h2>
            {% if unauthorized_records %}
            <table><thead><tr><th>Confidence</th><th>Coordinates</th><th>Timestamp</th></tr></thead>
            <tbody>{% for r in unauthorized_records %}<tr><td>{{ r.confidence }}</td><td>{{ r.coordinates }}</td><td>{{ r.created_at }}</td></tr>{% endfor %}</tbody>
            </table>
            {% else %}<p>No unauthorized data received.</p>{% endif %}
        </div>
    
</body>
</html>
"""
HISTORY_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>🗂️ Detection History</title>
    <style>
        body { font-family: 'Times New Roman'; padding: 20px; }
        h1 { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        .form-group { margin-bottom: 10px; }
        label { margin-right: 10px; }
        .nav { text-align: center; margin-top: 30px; font-size: 18px; }
    </style>
</head>
<body>
    <h1>🗂️ Mediveil Detection History</h1>
    <form method="GET" action="/history">
    <div class="nav">
        <a href="/">🗺 Maps</a> |
        <a href="/charts">📊 Charts</a> |
        <a href="/detection">📋 Detections</a> |
        <a href="/history">🗂️ History</a>
    </div>
        <div class="form-group">
            <label for="type">Detection Type:</label>
            <select name="type">
            <option value="">All</option>
            <option value="bloodstain" {% if selected_type == "bloodstain" %}selected{% endif %}>Bloodstain</option>
            <option value="unauthorised" {% if selected_type == "unauthorised" %}selected{% endif %}>Unauthorized</option>
            <option value="person" {% if selected_type == "person" %}selected{% endif %}>Person</option>
        </select>

        
        <button type="submit">Search</button>
    </form>

    {% if records %}
    <table>
        <thead>
            <tr><th>ID</th><th>Type</th><th>Coordinates</th><th>Confidence</th><th>Timestamp</th></tr>
        </thead>
        <tbody>
            {% for r in records %}
            <tr>
                <td>{{ r[0] }}</td>
                <td>{{ r[1] }}</td>
                <td>{{ r[2] }}</td>
                <td>{{ r[3] }}</td>
                <td>{{ r[4] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>No matching records found.</p>
    {% endif %}

</body>
</html>
"""

# ---------------------- FUNCTIONS ----------------------

DB_PATH = "mediveil_data.db"
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_type TEXT,
                coordinates TEXT,
                confidence REAL,
                created_at TEXT,
                UNIQUE (detection_type, coordinates, confidence, created_at)
            )
        ''')
        conn.commit()

def fetch_data():
    try:
        response = requests.get(API_URL, headers=headers)
        if response.status_code != 200:
            print("❌ API returned:", response.status_code)
            return []
        try:
            data = response.json()
        except ValueError:
            print("❌ JSON parsing failed. Response was:", response.text)
            return []

        records = []
        for entry in data.get("data", []):
            try:
                content = json.loads(entry["content"])
                content["created_at"] = entry.get("created_at", "N/A")
                records.append(content)
            except Exception as e:
                print("⚠️ JSON decode error:", e)
                continue
        return records
    except Exception as e:
        print("❌ fetch_data() error:", e)
        print("[DEBUG] Malaysia timestamp:", content["created_at"])

        return []

def save_to_sqlite(records):
    if not records:
        print("[DB] No records to save.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        inserted = 0
        for r in records:
            print("[DB] Saving record of type:", r.get("detection_type"))
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO detections (detection_type, coordinates, confidence, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    r.get("detection_type", ""),
                    str(r.get("coordinates", "")),
                    float(r.get("confidence", 0)),
                    r.get("created_at", "")
                ))
                inserted += 1
            except Exception as e:
                print("⚠️ Insert error:", e)
        conn.commit()
        print(f"[DB] Attempted to insert {len(records)} records. Inserted {inserted} new records.")


def draw_bloodstain_detection_map(records):
    blood_records = [r for r in records if 'bloodstain' in r.get("detection_type", "").lower()]
    
    # Step 1: Set fixed coordinate size (same as detection logic)
    width, height = 1280, 720

    fig, ax = plt.subplots(figsize=(8, 6))

    # Step 2: Add background image and force it to fit axis bounds
    img = mpimg.imread('static/hospital_floor.jpg')  # Ensure this is 1280x720
    ax.imshow(img, extent=[0, width, 0, height])  # Force image to match axis without flipping

    # Step 3: Set axis limits and labels (original style)
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)  # Keep top-left origin like OpenCV
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")
    ax.set_title("Bloodstain Detection Map (with real image)", fontsize=14)

    # Step 4: Add detection rectangles
    for item in blood_records:
        try:
            x1, y1, x2, y2 = item['coordinates']
            confidence = float(item.get('confidence', 0))
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                     linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)
            ax.text(x1, y1 - 10, f"{confidence:.2f}", color='red', fontsize=8)
        except:
            continue

    plt.tight_layout()
    plt.savefig("static/blood_detection_map.png")
    plt.close()



import matplotlib.image as mpimg  # Make sure this is imported

def draw_unauthorized_detection_map(records):
    unauthorized_records = [r for r in records if 'unauthorised' in r.get("detection_type", "").lower()]

    # Load background image
    bg_path = "static/unauthorized_bg.jpg"  # make sure this file exists
    img = mpimg.imread(bg_path)

    fig, ax = plt.subplots(figsize=(8, 6))

    # Show background image
    ax.imshow(img, extent=[0, 1280, 0, 720])  # Flip Y-axis for coordinate alignment

    ax.set_xlim(0, 1280)
    ax.set_ylim(0, 720)
    ax.set_title("Unauthorized Person Detection Map (with real image)", fontsize=14)
    ax.set_xlabel("X Coordinate")
    ax.set_ylabel("Y Coordinate")

    for item in unauthorized_records:
        try:
            x1, y1, x2, y2 = item['coordinates']
            confidence = float(item.get('confidence', 0))
            rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                     linewidth=2, edgecolor='navy', facecolor='none')
            ax.add_patch(rect)
            ax.text(x1, y1 - 10, f"{confidence:.2f}", color='navy', fontsize=8)
        except Exception as e:
            print("⚠️ Error drawing box:", e)
            continue

    os.makedirs("static", exist_ok=True)
    plt.tight_layout()
    plt.savefig("static/unauthorized_detection_map.png")
    plt.close()


def draw_detection_10min_chart(original_df, detection_type, filename):
    df = original_df.copy()

    filtered = df[df['detection_type'].str.lower() == detection_type.lower()].copy()
    if filtered.empty:
        print(f"[INFO] No {detection_type} data found. Skipping chart.")
        return False

    filtered['timestamp'] = pd.to_datetime(filtered['created_at'], errors='coerce')
    filtered = filtered.dropna(subset=['timestamp'])

    latest   = filtered['timestamp'].max().floor('10min')
    full_idx = pd.date_range(end=latest, periods=6, freq='10min')

    counts = (
        filtered
        .set_index('timestamp')
        .sort_index()
        .resample('10min')
        .size()
        .reindex(full_idx, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    bar_color = 'darkorange' if detection_type == 'unauthorised' else 'navy'
    counts.plot(kind='bar', ax=ax, color=bar_color)

    ax.set_ylim(bottom=0)
    ax.set_title(f"{detection_type.capitalize()} per 10-min (last 1 h)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'static/{filename}')
    plt.close()
    return True

# --- Flask routes ---

@app.route("/routes")
def list_routes():
    output = [str(rule) for rule in app.url_map.iter_rules()]
    return "<br>".join(output)

@app.route("/")
def map_layer():
    records = fetch_data()
    draw_bloodstain_detection_map(records)
    draw_unauthorized_detection_map(records)
    return render_template_string(FIRST_LAYER_TEMPLATE, last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route("/charts")
def chart_layer():
    records = fetch_data()
    df      = pd.DataFrame(records)

    has_person      = draw_detection_10min_chart(df, "person",       "person_10min_chart.png")
    has_unauthorized= draw_detection_10min_chart(df, "unauthorised", "unauthorized_10min_chart.png")

    return render_template_string(
        SECOND_LAYER_TEMPLATE,
        last_update       = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        has_person        = has_person,
        has_unauthorized  = has_unauthorized
    )
@app.route("/detection")
def table_layer():
    records = fetch_data()
    blood_records = [r for r in records if 'bloodstain' in r.get("detection_type", "").lower()]
    unauthorized_records = [r for r in records if 'unauthorised' in r.get("detection_type", "").lower()]
    return render_template_string(
        THIRD_LAYER_TEMPLATE,
        blood_records=blood_records,
        unauthorized_records=unauthorized_records,
        last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.route("/history", methods=["GET"])
def history_layer():
    detection_type = request.args.get("type", "")
    query = "SELECT id, detection_type, coordinates, confidence, created_at FROM detections WHERE 1=1"
    params = []

    if detection_type:
        query += " AND LOWER(detection_type) = ?"
        params.append(detection_type.lower())

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        records = cur.fetchall()

    return render_template_string(HISTORY_TEMPLATE, records=records)



if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)






