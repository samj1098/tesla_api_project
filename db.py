import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

#connection with PostgreSQL
def connect():
    return psycopg2.connect(DB_URL)

def create_table():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS charge_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    battery_level INTEGER,
                    charging_state TEXT,
                    charge_rate FLOAT,
                    energy_added FLOAT,
                    est_range FLOAT
                );
            """)
            conn.commit()

def prune_logs(cur, limit=30):
    cur.execute(f"""
        DELETE FROM charge_log
        WHERE id NOT IN (
            SELECT id FROM charge_log
            ORDER BY timestamp DESC
            LIMIT {limit}
        );
    """)

def log_charge_data(data, peak_charge_rate, miles_added, duration):
    charge = data['charge_state']
    battery_level = charge['battery_level']
    energy_added = charge['charge_energy_added']
    est_range = charge['battery_range']

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO charge_log (
                    battery_level, charging_state, charge_rate, energy_added,
                    est_range, event_type, miles_driven, miles_lost, miles_added, duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                battery_level,
                charge['charging_state'],
                peak_charge_rate,
                energy_added,
                est_range,
                "charge",
                0.0,  # miles_driven
                0.0,  # miles_lost
                miles_added,  # miles_added (optional logic)
                duration
            ))

            prune_logs(cur)
            conn.commit()
            print("✅ CHARGE event logged.")

def log_drive_event(data, miles_driven, odometer, miles_lost, duration):
    charge = data['charge_state']

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO charge_log (
                    battery_level, charging_state, charge_rate, energy_added,
                    est_range, event_type, miles_driven, miles_lost, miles_added, duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                charge['battery_level'],
                charge['charging_state'],
                0.0,  #didn't charge
                0.0,  # no energy added
                charge['battery_range'],
                "drive",
                miles_driven,
                miles_lost,
                0.0,
                duration
            ))

            prune_logs(cur)
            conn.commit()
            print("✅ DRIVE event logged.")

def log_idle_event(data, miles_lost, duration):
    charge = data['charge_state']
    zero_value = 0.0

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO charge_log (
                    battery_level, charging_state, charge_rate, energy_added,
                    est_range, event_type, miles_driven, miles_lost, miles_added, duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                charge['battery_level'],
                charge['charging_state'],
                zero_value,
                zero_value,
                charge['battery_range'],
                "idle",
                0.0,
                miles_lost,
                0.0,
                duration
            ))

            prune_logs(cur)
            conn.commit()
            print("✅ IDLE event logged.")
