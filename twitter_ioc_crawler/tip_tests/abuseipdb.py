from pathlib import Path
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import json

# ================= BASE DIR =================
BASE_DIR = Path(__file__).resolve().parents[0]

# ================= ENV =================
load_dotenv()

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"

def check_ip(ip_address):
    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY,
        "User-Agent": "CTI-TIP/1.0 (contact: security-research)"
    }

    params = {
        "ipAddress": ip_address,
        "maxAgeInDays": 90,
        "verbose": True
    }

    response = requests.get(
        ABUSEIPDB_URL,
        headers=headers,
        params=params,
        timeout=10
    )

    response.raise_for_status()
    return response.json()

def save_response(data):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"response_abuseipdb_ip_{timestamp}.json"
    filepath = BASE_DIR / filename

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[+] Response saved to: {filepath}")

if __name__ == "__main__":
    ip = input("Enter IP to check: ").strip()

    result = check_ip(ip)
    save_response(result)