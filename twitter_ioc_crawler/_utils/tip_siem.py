import logging
import requests
from .config import SIEM_API_KEY, SIEM_API_URL

SIEM_HEADERS = {
    "Authorization": SIEM_API_KEY,
    "Content-Type": "application/json",
}

DATASET_COLUMNS = [
    "twitter_link",
    "ioc",
    "ioc_type",

    # VirusTotal
    "vt_last_analysis_date",
    "vt_malicious_score",

    # AbuseIPDB
    "abuseipdb_lastReportedAt",
    "abuseipdb_abuseConfidenceScore",
    "abuseipdb_totalReports",
    "abuseipdb_domain",

    # AlienVault OTX
    "alienvault_time",
    "alienvault_pulse_info_count",
    "alienvault_link",

    # MalwareBazaar
    "malwarebazaar_first_seen",
    "malwarebazaar_last_seen",
    "malwarebazaar_signature",
    "malwarebazaar_vendor_intel_count",
]


def _build_siem_event(result: dict) -> dict:
    """
    Build a SIEM-safe event aligned with DATASET_COLUMNS.
    Missing fields are sent as empty string.
    """
    event = {}

    for col in DATASET_COLUMNS:
        event[col] = result.get(col, "")

    return event


def send_tip_result_to_siem(result: dict):
    """
    Send ONE newly enriched IOC to SIEM.
    Dataset schema is fixed & normalized.
    """

    if not SIEM_API_URL or not SIEM_API_KEY:
        logging.warning("SIEM config missing — skipping SIEM send")
        return

    event = _build_siem_event(result)

    try:
        res = requests.post(
            SIEM_API_URL,
            headers=SIEM_HEADERS,
            json=event,
            timeout=30,
        )

        if res.status_code not in (200, 201, 202):
            logging.error(
                f"SIEM rejected IOC={event.get('ioc')} | "
                f"status={res.status_code} | body={res.text}"
            )
        else:
            logging.info(f"SIEM accepted IOC={event.get('ioc')}")

    except Exception as e:
        logging.error(
            f"SIEM error IOC={event.get('ioc')} | {e}",
            exc_info=True
        )
