from _utils.tip_siem import send_tip_result_to_siem

# dummy_result.py (or inline for testing)

result = {
    # Core
    "twitter_link": "https://twitter.com/example/status/1234567890",
    "ioc": "https://sassonco.com/zxc/kito",
    "ioc_type": "url",

    # VirusTotal
    "vt_last_analysis_date": "2026-01-28 10:15:30",
    "vt_malicious_score": 69,

    # AbuseIPDB
    "abuseipdb_lastReportedAt": "",
    "abuseipdb_abuseConfidenceScore": "",
    "abuseipdb_totalReports": "",
    "abuseipdb_domain": "",

    # AlienVault OTX
    "alienvault_time": "2026-01-26 12:34:56",
    "alienvault_pulse_info_count": 3,
    "alienvault_link": "https://otx.alienvault.com/indicator/url/https://sassonco.com/zxc/kito",

    # MalwareBazaar
    "malwarebazaar_first_seen": "2026-01-26 12:34:56",
    "malwarebazaar_last_seen": "2026-06-26 12:34:56",
    "malwarebazaar_signature": "AgentTesla",
    "malwarebazaar_vendor_intel_count": 7,
}

send_tip_result_to_siem(result)