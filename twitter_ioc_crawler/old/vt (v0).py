import re
import base64
import requests
import csv
import os
import time
import random
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[0]

# ================= CONFIG =================
VT_API_KEY = os.getenv("VT_API_KEY")
VT_BASE = os.getenv("VT_BASE")

IOC_INDEX_FILE = BASE_DIR / "iocs.txt"
VT_RESULTS_FILE = BASE_DIR / "vt_results.txt"

VT_SLEEP = 20  # seconds (free tier rate-limit)

UTC_PLUS_7 = timezone(timedelta(hours=7))

HEADERS = {
    "x-apikey": VT_API_KEY
}

# ---------- SIEM CONFIG ----------
SIEM_API_URL = os.getenv("SIEM_API_URL")
SIEM_API_KEY = os.getenv("SIEM_API_KEY")

SIEM_HEADERS = {
    "Authorization": SIEM_API_KEY,
    "Content-Type": "application/json"
}

# ================= REGEX =================
HASH_REGEX = re.compile(r'^[a-fA-F0-9]{32,64}$')
IP_REGEX = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
URL_REGEX = re.compile(r'https?://[^\s]+')

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("vt_logging.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ================= UTILS =================
def get_ioc_type(ioc: str) -> str:
    if HASH_REGEX.match(ioc):
        return "hash"
    if IP_REGEX.match(ioc):
        return "ip"
    if URL_REGEX.fullmatch(ioc):
        return "url"
    return "other"

def parse_ts_to_epoch_ms(ts: str) -> int:
    """
    Convert 'YYYY-mm-dd HH:MM:SS' to epoch milliseconds (UTC)
    """
    if not ts:
        return int(time.time() * 1000)

    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

# ================= VT API =================
def vt_lookup(ioc: str):
    ioc_type = get_ioc_type(ioc)
    try:
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
        if r.status_code != 200:
            return {"ioc": ioc, "error": r.status_code}

        data = r.json()["data"]
        attrs = data.get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})

        # get last analysis
        last_analysis_ts = attrs.get("last_analysis_date")
        last_analysis_date = ""
        if last_analysis_ts:
            dt_utc = datetime.fromtimestamp(last_analysis_ts, tz=timezone.utc)
            last_analysis_date = dt_utc.astimezone(UTC_PLUS_7).strftime("%Y-%m-%d %H:%M:%S")

        result = {
            "last_analysis_date": last_analysis_date,
            "ioc": ioc,
            "ioc_type": ioc_type,
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "score": stats.get("malicious", 0) + stats.get("suspicious", 0),
            "vt_url": f"https://www.virustotal.com/gui/search/{ioc}",
            # default empty values for new descriptive columns
            "filename": "",
            "file_type": "",
            "size": "",
            "categories": "",
            "tags": "",
            "as_owner": ""
        }

        if ioc_type == "hash":
            result["filename"] = attrs.get("meaningful_name") or (attrs.get("names") or [""])[0]
            result["file_type"] = attrs.get("type_description")
            result["size"] = attrs.get("size")

        elif ioc_type == "url":
            categories = attrs.get("categories", {})
            result["categories"] = random.choice(list(categories.values())) if categories else ""
            result["tags"] = ", ".join(attrs.get("tags", []))

        elif ioc_type == "ip":
            result["as_owner"] = attrs.get("as_owner", "")
            result["tags"] = ", ".join(attrs.get("tags", []))

        return result

    except Exception as e:
        return {"ioc": ioc, "error": str(e)}

# ================= SIEM SENDER (NEW) =================
def send_vt_result_to_siem(result: dict):
    """
    Send ONE newly enriched IOC to SIEM
    """
    event = {
        "last_analysis_date": result.get("last_analysis_date"),
        "source": "VirusTotal",
        "ioc": result.get("ioc"),
        "ioc_type": result.get("ioc_type"),
        "score": int(result.get("score", 0)),
        "malicious": int(result.get("malicious", 0)),
        "suspicious": int(result.get("suspicious", 0)),
        "harmless": int(result.get("harmless", 0)),
        "undetected": int(result.get("undetected", 0)),
        "filename": result.get("filename"),
        "file_type": result.get("file_type"),
        "size": result.get("size"),
        "categories": result.get("categories"),
        "tags": result.get("tags"),
        "as_owner": result.get("as_owner"),
        "vt_url": result.get("vt_url"),
        "confidence": (
            "high" if int(result.get("malicious", 0)) > 5
            else "medium" if int(result.get("malicious", 0)) > 0
            else "low"
        )
    }

    try:
        res = requests.post(
            url=SIEM_API_URL,
            headers=SIEM_HEADERS,
            json=event,
            # json=[event],   # SIEM expects list
            timeout=30
        )

        if res.status_code not in (200, 201, 202):
            logging.error(
                f"SIEM rejected IOC={result['ioc']} | status={res.status_code} | body={res.text}"
            )
        else:
            logging.info(f"SIEM accepted IOC={result['ioc']}")

    except Exception as e:
        logging.error(f"SIEM error IOC={result['ioc']} | {e}")

# ================= TXT =================
def load_ioc_index():
    iocs = []

    if not os.path.isfile(IOC_INDEX_FILE):
        return iocs

    with open(IOC_INDEX_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # iocs.txt format: ioc | ioc_type
            parts = [p.strip() for p in line.split("|")]

            if len(parts) >= 1:
                ioc = parts[0]
                ioc_type = parts[1] if len(parts) > 1 else ""
                iocs.append({
                    "ioc": ioc,
                    "ioc_type": ioc_type
                })

    return iocs

def load_existing_tip_results():
    seen = set()

    if not os.path.isfile(VT_RESULTS_FILE):
        return seen

    with open(VT_RESULTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                seen.add(parts[1])  # ioc column

    return seen


def save_vt_result(result: dict):
    ioc = result["ioc"]
    last_analysis = result.get("last_analysis_date", "")

    rows = {}

    # Load existing TXT
    if os.path.isfile(VT_RESULTS_FILE):
        with open(VT_RESULTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    rows[parts[1]] = parts

    # Decide action
    action = "new"
    if ioc in rows:
        existing_date = rows[ioc][0]
        if last_analysis > existing_date:
            action = "updated"
        else:
            action = "duplicate"

    if action in ("new", "updated"):
        rows[ioc] = [
            result.get("last_analysis_date", ""),
            result.get("ioc", ""),
            result.get("ioc_type", ""),
            str(result.get("score", "")),
            str(result.get("malicious", "")),
            str(result.get("suspicious", "")),
            str(result.get("harmless", "")),
            str(result.get("undetected", "")),
            result.get("filename", ""),
            result.get("file_type", ""),
            str(result.get("size", "")),
            result.get("vt_url", ""),
            result.get("categories", ""),
            result.get("tags", ""),
            result.get("as_owner", "")
        ]

    # Write PIPE-separated TXT
    with open(VT_RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "# last_analysis_date | ioc | ioc_type | score | malicious | suspicious | "
            "harmless | undetected | filename | file_type | size | vt_url | "
            "categories | tags | as_owner\n"
        )
        for r in rows.values():
            f.write(" | ".join(r) + "\n")

    # Logging + SIEM
    if action == "new":
        logging.info(f"VT result saved | IOC={ioc} | NEW")
        # send_vt_result_to_siem(result)

    elif action == "duplicate":
        logging.info(f"VT result skipped | IOC={ioc} | DUPLICATE")

    elif action == "updated":
        logging.info(f"VT result updated | IOC={ioc} | NEWER last_analysis_date")


# ================= MAIN =================
def vt_main():
    logging.info("[✓] START")

    indexed_iocs = load_ioc_index()
    seen_results = load_existing_tip_results()

    logging.info(f"[+] Loaded {len(indexed_iocs)} IOCs from index")
    logging.info(f"[+] Loaded {len(seen_results)} existing VT results")

    new_count = 0

    for item in indexed_iocs:
        ioc = item["ioc"]

        if ioc in seen_results:
            logging.info(f"Skipping IOC={ioc} (already enriched)")
            continue  # already enriched

        logging.info(f"VT lookup | IOC={ioc}")
        result = vt_lookup(ioc)

        if not result:
            logging.warning(f"Skipped IOC={ioc} (unsupported type)")
            continue
        if "error" in result:
            logging.error(f"Error enriching IOC={ioc}: {result['error']}")
            continue

        save_vt_result(result)
        seen_results.add(ioc)
        new_count += 1

        logging.info(
            f"Enriched IOC={ioc} | score={result['score']} "
            f"(mal={result['malicious']}, susp={result['suspicious']})"
        )

        time.sleep(VT_SLEEP)

    logging.info(f"[✓] FINISH | new={new_count}")