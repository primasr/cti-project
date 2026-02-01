import base64
import requests
from datetime import datetime, timezone
from typing import Optional

from .text_utils import get_ioc_type
from .config import VT_API_KEY, VT_BASE
from .time_utils import UTC_PLUS_7

HEADERS = {"x-apikey": VT_API_KEY}


def vt_lookup(ioc: str) -> Optional[dict]:
    try:
        ioc_type = get_ioc_type(ioc)

        if ioc_type == "hash":
            url = f"{VT_BASE}/files/{ioc}"
        elif ioc_type == "ip":
            url = f"{VT_BASE}/ip_addresses/{ioc}"
        elif ioc_type == "url":
            encoded = base64.urlsafe_b64encode(ioc.encode()).decode().strip("=")
            url = f"{VT_BASE}/urls/{encoded}"
        else:
            return None

        r = requests.get(url, headers=HEADERS, timeout=20)

        # ---- Not found or API error ----
        if r.status_code != 200:
            return None

        data = r.json().get("data")
        if not data:
            return None

        attrs = data.get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        # ---- last_analysis_date (UTC+7) ----
        last_analysis_date = ""
        ts = attrs.get("last_analysis_date")

        if ts:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            last_analysis_date = dt.astimezone(UTC_PLUS_7).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        return {
            "ioc": ioc,
            "ioc_type": ioc_type,
            "last_analysis_date": last_analysis_date,
            "malicious": stats.get("malicious", 0),
        }

    except requests.RequestException:
        return None

    except Exception:
        return None