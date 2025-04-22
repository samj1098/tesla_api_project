from tesla_client import get_vehicle_data
from db import create_table, log_charge_data

def main():
    create_table()
    data, is_live = get_vehicle_data()

    if is_live:
        log_charge_data(data)
        print("Data retrieved and processed.")
    else:
        print("Data is from cache, skipping DB log")

if __name__ == "__main__":
    main()