import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

# ---- Twitter / X ----
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
CT0 = os.getenv("CT0")
TWITTER_USER_FILE = BASE_DIR / "twitter_users.txt"

# ---- Files ----
LOG_FILE = BASE_DIR / "logging.log"
IOC_INDEX_FILE = BASE_DIR / "iocs.txt"
TIP_RESULTS_FILE = BASE_DIR / "tip_results.txt"

# ---- SIEM ----
SIEM_API_URL = os.getenv("SIEM_API_URL")
SIEM_API_KEY = os.getenv("SIEM_API_KEY")

# ---- VirusTotal ----
VT_API_KEY = os.getenv("VT_API_KEY")
VT_BASE = os.getenv("VT_BASE")
VT_SLEEP = 20

# ---- AbuseIPDB ----
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
ABUSEIPDB_URL = os.getenv("ABUSEIPDB_URL")

# ---- MalwareBazaar ----
MALWAREBAZAAR_API_KEY = os.getenv("MALWAREBAZAAR_API_KEY")
MALWAREBAZAAR_URL = os.getenv("MALWAREBAZAAR_URL")

# ---- AlienVault OTX ----
ALIENVAULT_OTX_KEY = os.getenv("ALIENVAULT_OTX_KEY")
ALIENVAULT_BASE_API = os.getenv("ALIENVAULT_BASE_API")
ALIENVAULT_BASE_UI = os.getenv("ALIENVAULT_BASE_UI")