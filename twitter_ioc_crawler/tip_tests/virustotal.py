import requests
import json
import re
import base64
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[0]

VT_API_KEY = os.getenv("VT_API_KEY")
VT_BASE = os.getenv("VT_BASE")

def get_ioc_type(ioc):
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ioc):
        return "ip"
    if re.match(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$", ioc):
        return "hash"
    if ioc.startswith("http://") or ioc.startswith("https://"):
        return "url"
    return None

def check_ioc_virustotal(ioc):
    ioc_type = get_ioc_type(ioc)

    if ioc_type == "hash":
        url = f"{VT_BASE}/files/{ioc}"

    elif ioc_type == "ip":
        url = f"{VT_BASE}/ip_addresses/{ioc}"

    elif ioc_type == "url":
        encoded = base64.urlsafe_b64encode(ioc.encode()).decode().strip("=")
        url = f"{VT_BASE}/urls/{encoded}"

    else:
        raise ValueError("Unsupported IOC type")

    headers = {
        "x-apikey": VT_API_KEY,
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=15)

    # Handle VT "not found" cleanly
    if response.status_code == 404:
        return ioc_type, {"error": "IOC not found in VirusTotal"}

    response.raise_for_status()
    return ioc_type, response.json()

def save_response(ioc_type, data):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"response_virustotal_{ioc_type}_{timestamp}.json"
    filename = BASE_DIR / filename

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[+] Response saved to: {filename}")

if __name__ == "__main__":
    ioc = input("Enter IP / URL / Hash: ").strip()

    ioc_type, result = check_ioc_virustotal(ioc)
    save_response(ioc_type, result)
