import logging
import re
import requests
import urllib.parse
from datetime import datetime, timezone
from typing import Optional
from .regex import HASH_SHA256_REGEX, IP_REGEX, URL_REGEX

from .config import ALIENVAULT_OTX_KEY, ALIENVAULT_BASE_API, ALIENVAULT_BASE_UI

IOC_TYPE_MAP = {
    "ip": "IPv4",
    "url": "url",
    "hash": "file",
}

def _detect_ioc_type(ioc: str) -> Optional[str]:
    ioc = ioc.strip()

    if IP_REGEX.fullmatch(ioc):
        return "ip"

    if HASH_SHA256_REGEX.fullmatch(ioc):
        return "hash"

    if URL_REGEX.fullmatch(ioc):
        return "url"

    return None


def alienvault_lookup(ioc: str) -> Optional[dict]:
    """
    Lookup IOC in AlienVault OTX.
    Returns extracted fields or None.
    """

    if not ALIENVAULT_OTX_KEY:
        logging.error("ALIENVAULT_OTX_KEY not set")
        return None

    ioc_type = _detect_ioc_type(ioc)
    if not ioc_type:
        logging.info(f"AlienVault skipped | Unsupported IOC={ioc}")
        return None

    otx_type = IOC_TYPE_MAP[ioc_type]
    ioc_value = ioc

    # ---- URL handling ----
    if ioc_type == "url":
        if not ioc_value.endswith("/"):
            ioc_value += "/"
        ioc_value = urllib.parse.quote(ioc_value, safe="")

    api_url = f"{ALIENVAULT_BASE_API}/{otx_type}/{ioc_value}/general"

    headers = {
        "X-OTX-API-KEY": ALIENVAULT_OTX_KEY,
        "Accept": "application/json",
        "User-Agent": "CTI-TIP/1.0",
    }

    logging.info(f"AlienVault lookup | IOC={ioc}")

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logging.error(f"AlienVault request failed | IOC={ioc} | {e}")
        return None

    pulse_info = raw.get("pulse_info", {})
    pulse_count = pulse_info.get("count", 0)

    if pulse_count == 0:
        logging.info(f"AlienVault not found | IOC={ioc}")
        return None

    # ---- Build UI link ----
    if ioc_type == "url":
        ui_link = f"{ALIENVAULT_BASE_UI}/url/{ioc_value}"
    else:
        ui_link = f"{ALIENVAULT_BASE_UI}/{otx_type}/{ioc}"

    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    logging.info(
        f"AlienVault hit | IOC={ioc} | pulses={pulse_count}"
    )

    return {
        "alienvault_checked_at": checked_at,
        "alienvault_pulse_count": pulse_count,
        "alienvault_link": ui_link,
    }
