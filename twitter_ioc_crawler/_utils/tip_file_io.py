import os
import logging
from .config import IOC_INDEX_FILE, TIP_RESULTS_FILE

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

TIP_FIELD_MAPPING = {
    # ---- VirusTotal ----
    "last_analysis_date": "vt_last_analysis_date",
    "malicious": "vt_malicious_score",

    # ---- AbuseIPDB ----
    "abuseipdb_lastReportedAt": "abuseipdb_lastReportedAt",
    "abuseipdb_abuseConfidenceScore": "abuseipdb_abuseConfidenceScore",
    "abuseipdb_totalReports": "abuseipdb_totalReports",
    "abuseipdb_domain": "abuseipdb_domain",

    # ---- AlienVault ----
    "alienvault_time": "alienvault_time",
    "alienvault_pulse_info_count": "alienvault_pulse_info_count",
    "alienvault_link": "alienvault_link",

    # ---- MalwareBazaar ----
    "malwarebazaar_first_seen": "malwarebazaar_first_seen",
    "malwarebazaar_last_seen": "malwarebazaar_last_seen",
    "malwarebazaar_signature": "malwarebazaar_signature",
    "malwarebazaar_vendor_intel_count": "malwarebazaar_vendor_intel_count",
}

def merge_tip_fields(row: dict, result: dict):
    """
    Map provider-specific fields into unified TIP dataset.
    Only non-empty values overwrite existing ones.
    """
    for src_field, dst_field in TIP_FIELD_MAPPING.items():
        value = result.get(src_field)
        if value not in (None, ""):
            row[dst_field] = str(value)


def load_ioc_index():
    iocs = set()

    if not os.path.isfile(IOC_INDEX_FILE):
        return iocs

    with open(IOC_INDEX_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]

            ioc = parts[0]
            ioc_type = parts[1] if len(parts) > 1 else ""
            tweet_link = parts[2] if len(parts) > 2 else ""

            iocs.add((ioc, ioc_type, tweet_link))

    return iocs


def load_existing_tip_results():
    seen = set()
    if not os.path.isfile(TIP_RESULTS_FILE):
        return seen

    with open(TIP_RESULTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            seen.add(line.split("|")[1].strip())
    return seen


def save_tip_result(result: dict):
    """
    Save unified TIP result (VT / AbuseIPDB / AlienVault / MalwareBazaar)
    """

    rows = {}

    # ---- Load existing rows ----
    if os.path.isfile(TIP_RESULTS_FILE):
        with open(TIP_RESULTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                row = dict(zip(DATASET_COLUMNS, parts))
                rows[row["ioc"]] = row

    ioc = result.get("ioc")
    if not ioc:
        raise ValueError("Result missing IOC field")

    # ---- Initialize empty row ----
    row = {col: "" for col in DATASET_COLUMNS}
    row["ioc"] = ioc
    row["ioc_type"] = result.get("ioc_type", "")
    row["twitter_link"] = result.get("twitter_link", "")

    # ---- Merge new data (non-empty only) ----
    for col in DATASET_COLUMNS:
        if col in result and result[col] not in (None, ""):
            row[col] = str(result[col])

    # ---- Merge provider fields ----
    merge_tip_fields(row, result)

    action = "new"

    # ---- Duplicate logic (based on VT date if exists) ----
    if ioc in rows:
        old_vt_date = rows[ioc].get("vt_last_analysis_date", "")
        new_vt_date = row.get("vt_last_analysis_date", "")

        if new_vt_date and old_vt_date and new_vt_date <= old_vt_date:
            action = "duplicate"
        else:
            # merge with existing row
            for k, v in rows[ioc].items():
                if row.get(k, "") == "":
                    row[k] = v

    if action != "duplicate":
        rows[ioc] = row

    # ---- Write file ----
    with open(TIP_RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write("# " + " | ".join(DATASET_COLUMNS) + "\n")
        for r in rows.values():
            f.write(" | ".join(r.get(c, "") for c in DATASET_COLUMNS) + "\n")

    logging.info(
        f"TIP result {'saved' if action=='new' else 'skipped'} | IOC={ioc} | {action.upper()}"
    )
