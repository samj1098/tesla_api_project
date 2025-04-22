import os
import teslapy
from dotenv import load_dotenv

load_dotenv()
email = os.getenv("TESLA_EMAIL")  # Make sure your .env has TESLA_EMAIL

with teslapy.Tesla(email) as tesla:
    if not tesla.authorized:
        tesla.fetch_token()
    print("✅ Access token:", tesla.token['access_token'])
