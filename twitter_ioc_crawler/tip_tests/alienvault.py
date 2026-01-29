import requests
import json
import re
import urllib.parse
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[0]

ALIENVAULT_OTX_KEY = os.getenv("ALIENVAULT_OTX_KEY")
BASE_URL = "https://otx.alienvault.com/api/v1/indicators"

IOC_TYPE_MAP = {
    "ip": "IPv4",
    "domain": "domain",
    "url": "url",
    "file": "file"
}

def detect_ioc_type(ioc):
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ioc):
        return "ip"
    if re.match(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$", ioc):
        return "file"
    if ioc.startswith("http://") or ioc.startswith("https://"):
        return "url"
    return "domain"

def check_ioc_otx(ioc):
    ioc_type = detect_ioc_type(ioc)
    otx_type = IOC_TYPE_MAP[ioc_type]
    ioc_value = ioc

    if ioc_type == "url":
        ioc_value = urllib.parse.quote(ioc, safe="")

    url = f"{BASE_URL}/{otx_type}/{ioc_value}/general"

    headers = {
        "X-OTX-API-KEY": ALIENVAULT_OTX_KEY,
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=10)

    # Helpful error logging
    if response.status_code != 200:
        raise RuntimeError(
            f"OTX query failed ({response.status_code}): {response.text}"
        )

    return ioc_type, response.json()

def save_response(ioc_type, data):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"response_alienvault_{ioc_type}_{timestamp}.json"
    filename = BASE_DIR / filename

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[+] Response saved to: {filename}")

if __name__ == "__main__":
    ioc = input("Enter IP / Domain / URL / Hash: ").strip()

    ioc_type, result = check_ioc_otx(ioc)
    save_response(ioc_type, result)
