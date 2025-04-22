from db import connect
from datetime import date

def drop_charge_log_table():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS charge_log;")
            conn.commit()
            print("❌ Dropped charge_log table.")

def create_charge_log_table():
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
                    est_range FLOAT,
                    event_type TEXT,
                    miles_driven FLOAT,
                    miles_lost FLOAT,
                    miles_added FLOAT,
                    duration_seconds INTEGER
                );
            """)
            conn.commit()
            print("✅ Recreated charge_log table with updated schema.")


# --- Run this file directly ---
if __name__ == "__main__":
    drop_charge_log_table()
    create_charge_log_table()
    # Optional: uncomment if you want to clear today's data
    # delete_today_rows()
