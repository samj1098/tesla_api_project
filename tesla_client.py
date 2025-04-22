import os
from dotenv import load_dotenv
import teslapy
import json
import time

#loads .envfile and finds "TESLA EMAIL" variable
load_dotenv()
email = os.getenv("TESLA_EMAIL")
CACHE_FILE = 'cached_vehicle_data.json'

tesla = teslapy.Tesla(email)

def wake_up_vehicle(vehicle):
    if vehicle['state'] != 'online':
        vehicle = vehicle.wake_up()
    return vehicle

def get_vehicle():
    """Authenticate and return the primary Tesla vehicle object."""
    if not tesla.authorized:
        print("Fetching token...")
        tesla.fetch_token()

    vehicles = tesla.vehicle_list()
    return vehicles[1]

#saves data to json incase api can't acess info when car is asleep
CACHE_FILE = 'cached_vehicle_data.json'

def save_to_cache(data):
    """Save vehicle data to a local JSON cache file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_from_cache():
    """Load vehicle data from local cache if available."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

#Connect to Tesla API and retrieve vehicle data. If vehicle is asleep, return last cached data.
def get_vehicle_data():
    with teslapy.Tesla(email) as tesla:
        if not tesla.authorized:
            print("Opening browser for Tesla login...")
            tesla.fetch_token()

        vehicle = get_vehicle()  # <-- Good to note: index 1 means second Tesla
        vehicle_state = vehicle['state']

        if vehicle_state != "online":
            print("Vehicle is asleep. Serving cached data from last time vehicle was awake")
            return load_from_cache(), False

        print(f"Vehicle is online, Connected to: {vehicle['display_name']} and data is current")
        data = vehicle.get_vehicle_data()
        save_to_cache(data)
        return data, True
