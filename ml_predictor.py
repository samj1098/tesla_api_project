import pandas as pd
from db import connect  # your existing DB helper

def fetch_data():
    with connect() as conn:
        df = pd.read_sql_query("""
            SELECT timestamp, battery_level, charging_state, charge_rate, energy_added,
                est_range, event_type, miles_driven, miles_lost, miles_added
            FROM charge_log
            ORDER BY timestamp ASC;
        """, conn)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

def engineer_features(df):
    # Time-based features
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    # Event type as numeric (one-hot encoding)
    df = pd.get_dummies(df, columns=["event_type"])

    # Drop unused columns
    df = df.drop(columns=["timestamp", "charging_state"])

    return df

def label_next_charge_times(df):
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["next_charge_time_delta_minutes"] = None
    df["next_charge_duration_minutes"] = None

    for i, row in df.iterrows():
        if row["event_type_charge"]:  # skip charge rows
            continue

        next_charges = df[(df.index > i) & (df["event_type_charge"])]
        if not next_charges.empty:
            next_charge = next_charges.iloc[0]
            delta = (next_charge["timestamp"] - row["timestamp"]).total_seconds() / 60
            duration = (next_charge["miles_added"] / 3.0) * 5  # crude estimate: 3 miles per 5 mins

            df.at[i, "next_charge_time_delta_minutes"] = delta
            df.at[i, "next_charge_duration_minutes"] = duration

    df = df.dropna(subset=["next_charge_time_delta_minutes", "next_charge_duration_minutes"])
    return df



if __name__ == "__main__":
    df = fetch_data()
    print("✅ Raw data:")
    print(df.head())

# Step 1: Label data while timestamp still exists
    df = label_next_charge_times(df)

# Step 2: Now we can drop timestamp + encode features
    df = engineer_features(df)

    print("\n✅ Features + Labels:")
    print(df[["next_charge_time_delta_minutes", "next_charge_duration_minutes"]].head())
