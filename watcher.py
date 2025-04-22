import time
import os
import json
from datetime import datetime, timezone
from flask import Flask, jsonify
from tesla_client import get_vehicle_data, save_to_cache, get_vehicle, wake_up_vehicle
from db import log_charge_data, log_drive_event, log_idle_event
from flask_cors import CORS

POLL_INTERVAL = 60  # seconds
CACHE_PATH = "/home/ec2-user/TeslaCharging/cached_vehicle_data.json"
CACHE_INTERVAL = 300  # 5 minutes

app = Flask(__name__)
CORS(app)

@app.route("/api/pickles-mode", methods=["POST"])
def activate_pickles_mode():
    try:
        import teslapy
        import os
        from flask import jsonify

        email = os.getenv("TESLA_EMAIL")
        with teslapy.Tesla(email) as tesla:
            if not tesla.authorized:
                tesla.fetch_token()

            vehicle = tesla.vehicle_list()[0]
            vehicle.sync_wake_up()

            # ✅ Log all available endpoints
            available_endpoints = list(vehicle.api.__self__.keys())

            return jsonify({
                "available_endpoints": available_endpoints
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/status")
def api_status():
    try:
        with open(CACHE_PATH) as f:
            data = json.load(f)

        charge = data["charge_state"]
        last_modified = datetime.fromtimestamp(os.path.getmtime(CACHE_PATH), tz=timezone.utc).isoformat()

        return jsonify({
            "battery_level": charge["battery_level"],
            "charging_state": charge["charging_state"],
            "charge_rate": charge["charge_rate"],
            "energy_added": charge["charge_energy_added"],
            "estimated_range": charge["battery_range"],
            "is_live": True,
            "last_updated": last_modified
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def watch_for_charge_end():
    print("Watching for unplug events...")

    # Tracking previous states
    last_charging_state = None
    last_battery_level = None
    last_odometer = None
    last_shift_state = None

    # Drive session tracking
    in_drive_session = False
    drive_start_odometer = None
    drive_event_miles = None
    drive_start_range = None
    drive_start_time = None

    # Charge session tracking
    peak_charge_rate = 0.0
    updated_range = None
    charge_start_time = None

    # Idle session tracking
    in_idle_session = False
    park_start_range = None
    idle_start_time = None

    while True:
        try:
            data, is_live = get_vehicle_data()

            if not is_live:
                print("Vehicle asleep — skipping.")
                time.sleep(POLL_INTERVAL)
                continue

            # Check if we should save a snapshot
            try:
                last_modified = os.path.getmtime(CACHE_PATH)
                seconds_since_update = time.time() - last_modified
            except FileNotFoundError:
                seconds_since_update = float('inf')

            if seconds_since_update >= CACHE_INTERVAL:
                print("Saving snapshot to cache (no previous file found)")
                save_to_cache(data)

            # --- Data extraction ---
            charge = data['charge_state']
            vehicle_state = data['vehicle_state']
            drive_state = data['drive_state']

            charging_state = charge['charging_state']
            battery_level = charge['battery_level']
            odometer = vehicle_state['odometer']
            shift_state = drive_state['shift_state']
            miles_added = charge["charge_miles_added_rated"]

            print(f"Vehicle online, Charging: {charging_state}")

            # --- Charge detection ---
            if charging_state == "Charging":
                peak_charge_rate = max(peak_charge_rate, charge['charge_rate'])
                print("Charge Started")
                charge_start_time = time.time()

            if last_charging_state == "Charging" and charging_state != "Charging":
                print("⚡️ Charge session ended — saving data.")
                duration = int(time.time() - charge_start_time) if charge_start_time else 0
                log_charge_data(data, peak_charge_rate, miles_added, duration)
                peak_charge_rate = 0.0
                updated_range = charge["battery_range"]
                in_idle_session = False
                charge_start_time = None

            # --- Drive session detection ---
            if shift_state in ["D", "R", "N"] and not in_drive_session:
                print("Drive started")
                drive_start_odometer = odometer
                updated_range = charge["battery_range"]
                in_drive_session = True
                drive_start_time = time.time()

            if in_drive_session and shift_state in ["P", None]:
                print("🚗 Drive completed — logging drive event.")
                drive_event_miles = odometer - drive_start_odometer
                miles_lost = updated_range - charge["battery_range"]
                duration = int(time.time() - drive_start_time) if drive_start_time else 0
                log_drive_event(data, drive_event_miles, odometer, miles_lost, duration)
                in_drive_session = False
                drive_start_odometer = None
                drive_event_miles = None
                miles_lost = None
                updated_range = charge["battery_range"]
                drive_start_time = None

            # --- Idle session detection ---
            print(f"Shift state: {shift_state}, Charging: {charging_state}, in_idle_session: {in_idle_session}")
            if shift_state in ["P", None] and not in_idle_session and charging_state != "Charging":
                in_idle_session = True
                idle_start_time = time.time()
                updated_range = charge["battery_range"]
                print("Idle Started")

            if in_idle_session and (shift_state in ["D", "R", "N"] or charging_state == "Charging"):
                range_drop = updated_range - charge["battery_range"]
                duration = int(time.time() - idle_start_time) if idle_start_time else 0
                print("🪫 Idle drain detected — logging idle event.")
                log_idle_event(data, range_drop, duration)
                in_idle_session = False
                park_start_range = None
                updated_range = charge["battery_range"]
                idle_start_time = None

            # --- Update state for next loop ---
            last_charging_state = charging_state
            last_odometer = odometer
            last_battery_level = battery_level
            last_shift_state = shift_state

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    import threading

    # Thread 1: background data collection
    t1 = threading.Thread(target=watch_for_charge_end)
    t1.daemon = True
    t1.start()

    # Thread 2: run Flask API server
    app.run(host="0.0.0.0", port=8080)