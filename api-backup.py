from flask import Flask, jsonify
import json
import os
from dotenv import load_dotenv
from db import connect

app = Flask(__name__)
load_dotenv()

#returns cached data from json file most current - even if there is no event triggering database entry
@app.route("/api/status")
def api_status():
    try:
        with open ("cached_vehicle_data.json") as f:
            data = json.load(f)
        
        charge = data["charge_state"]

        return jsonify({
            "battery_level": charge["battery_level"],
            "charging_state": charge["charging_state"],
            "charge_rate": charge["charge_rate"],
            "energy_added": charge["charge_energy_added"],
            "estimated_range": charge["battery_range"],
            "is_live": True  # For now assume it was live when cached
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#returns most recent database entry log
@app.route("/api/recent-events")
def api_recent_events():
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT timestamp, battery_level, energy_added, charging_state, event_type 
                    FROM charge_log 
                    ORDER BY timestamp DESC 
                    LIMIT 10;
                """)
                rows = cur.fetchall()

        events = []
        for row in rows:
            events.append({
                "timestamp": row[0],
                "battery_level": row[1],
                "energy_added": row[2],
                "charging_state": row[3],
                "event_type": row[4]
            })

        return jsonify(events)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)