import os
import requests
import logging
from .config import ABUSEIPDB_API_KEY, ABUSEIPDB_URL
from requests.exceptions import RequestException
from datetime import datetime
import time

def abuseipdb_lookup(ip: str, retries: int = 3) -> dict | None:
    """
    Lookup IP reputation from AbuseIPDB.
    Returns a dict with extracted fields or None.
    """

    if not ABUSEIPDB_API_KEY:
        logging.error("ABUSEIPDB_API_KEY not set")
        return None

    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY,
        "User-Agent": "CTI-TIP/1.0 (contact: security-research)",
    }

    params = {
        "ipAddress": ip,
        "maxAgeInDays": 90,
        "verbose": True,
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                ABUSEIPDB_URL,
                headers=headers,
                params=params,
                timeout=15,
            )

            # 🚫 Invalid IP → do NOT retry
            if resp.status_code == 422:
                logging.warning(f"Invalid IP address | IP={ip}")
                return None

            resp.raise_for_status()
            raw = resp.json()
            break

        except RequestException as e:
            logging.warning(
                f"AbuseIPDB attempt {attempt}/{retries} failed | IP={ip} | {e}"
            )
            time.sleep(2 * attempt)  # backoff
    else:
        logging.error(f"AbuseIPDB lookup failed after retries | IP={ip}")
        return None

    data = raw.get("data")
    if not data:
        return None

    # ---- Normalize lastReportedAt ----
    last_reported = data.get("lastReportedAt", "")
    if last_reported:
        try:
            last_reported = (
                datetime.fromisoformat(last_reported.replace("Z", "+00:00"))
                .strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception:
            pass  # keep original if parsing fails

    # 🔑 Extract ONLY what TIP needs
    return {
        "abuseipdb_lastReportedAt": last_reported,
        "abuseipdb_abuseConfidenceScore": data.get("abuseConfidenceScore", ""),
        "abuseipdb_totalReports": data.get("totalReports", ""),
        "abuseipdb_domain": data.get("domain", ""),
    }