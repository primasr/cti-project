import time
import re
import csv
import os
import logging
import requests
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[0]

# ================= CONFIG =================
USERNAME = "malwrhunterteam"
MAX_HASH_TWEETS = 3

LOG_FILE = BASE_DIR / "crawler_logging.log"
TXT_FILE = BASE_DIR / "posts.txt"
IOC_INDEX_FILE = BASE_DIR / "iocs.txt"

# === AUTH COOKIE (WAJIB LOGIN X) ===
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
CT0 = os.getenv("CT0")

# ================= REGEX ==================
COMPANY_REGEX = re.compile(r'^"([^"]+)"', re.M)
CERT_REGEX = re.compile(r'\(([^)]*cert[^)]*)\)', re.I)

FILENAME_REGEX = re.compile(
    r'"([^"]+\.(exe|dll|pif|msi|zip))"', re.I
)
FILENAME_PLAIN_REGEX = re.compile(
    r'\b([\w\-]+\.(exe|dll|pif|msi|zip))\b', re.I
)

HASH_SHA256_REGEX = re.compile(r'\b[a-fA-F0-9]{32,64}\b')
URL_REGEX = re.compile(r'https?://[^\s]+')

SEEN_REGEX = re.compile(r'seen from\s+([A-Za-z ]+)', re.I)
IP_REGEX = re.compile(
    r'\b\d{1,3}(?:\[\.\]|\.)\d{1,3}(?:\[\.\]|\.)\d{1,3}(?:\[\.\]|\.)\d{1,3}\b'
)

def get_ioc_type(ioc: str) -> str:
    if HASH_SHA256_REGEX.fullmatch(ioc):
        return "hash"
    if IP_REGEX.fullmatch(ioc):
        return "ip"
    if URL_REGEX.fullmatch(ioc):
        return "url"
    return "unknown"

# ================= LOGGING ================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ================= UTILS ==================
def normalize(text: str) -> str:
    return text.replace("[.]", ".")

def has_ioc(text: str) -> bool:
    return bool(
        HASH_SHA256_REGEX.search(text) or
        IP_REGEX.search(text) or
        URL_REGEX.search(text)
    )

UTC_PLUS_7 = timezone(timedelta(hours=7))
def get_tweet_time(tweet):
    try:
        time_elem = tweet.find_element(By.XPATH, ".//time")
        dt = time_elem.get_attribute("datetime")
        if dt:
            utc_time = datetime.fromisoformat(
                dt.replace("Z", "+00:00")
            )
            return utc_time.astimezone(UTC_PLUS_7)
    except:
        pass
    return None

def load_existing_hashes():
    hashes = {}

    if not os.path.isfile(TXT_FILE):
        logging.info("TXT file not found, starting fresh")
        return hashes

    try:
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("|")
                if len(parts) >= 5:
                    h = parts[4].strip()
                    if h:
                        hashes[h] = "txt"
    except Exception as e:
        logging.error(f"Failed to load existing hashes: {e}", exc_info=True)

    return hashes


def load_existing_ioc_index():
    seen = set()

    if not os.path.isfile(IOC_INDEX_FILE):
        return seen

    try:
        with open(IOC_INDEX_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                ioc = line.strip().split("|")[0]
                seen.add(ioc)
    except Exception as e:
        logging.error(f"Failed to load IOC index: {e}", exc_info=True)

    return seen

# ================= TXT ====================
def save_txt(row, tweet_time, ioc):
    exists = os.path.isfile(TXT_FILE)

    with open(TXT_FILE, "a", encoding="utf-8") as f:
        if not exists:
            f.write(
                "# time | filename | company | certificate | hash | country | ip | url | images\n"
            )

        f.write(
            f"{(tweet_time or datetime.now(UTC_PLUS_7)).strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{row.get('filename','')} | "
            f"{row.get('company','')} | "
            f"{row.get('certificate','')} | "
            f"{ioc} | "
            f"{row.get('country','')} | "
            f"{row.get('ip','')} | "
            f"{row.get('url','')} | "
            f"{','.join(row.get('images', []))}\n"
        )

# ================= PARSER =================
def parse(text, images):
    text = normalize(text)

    data = {
        "company": "",
        "certificate": "",
        "filename": "",
        "iocs": [],
        "country": "",
        "ip": "",
        "url": "",
        "images": images
    }

    m = COMPANY_REGEX.search(text)
    if m:
        data["company"] = m.group(1)

    m = CERT_REGEX.search(text)
    if m:
        data["certificate"] = m.group(1)

    m = FILENAME_REGEX.search(text) or FILENAME_PLAIN_REGEX.search(text)
    if m:
        data["filename"] = m.group(1)

    # Change to array, so that the we can get multiple IoCs
    hashes = HASH_SHA256_REGEX.findall(text)
    if hashes:
        data["iocs"] = list(set(hashes))  # deduplicate inside tweet

    m = SEEN_REGEX.search(text)
    if m:
        data["country"] = m.group(1).strip()

    m = IP_REGEX.search(text)
    if m:
        data["ip"] = normalize(m.group(0))

    m = URL_REGEX.search(text)
    if m:
        data["url"] = normalize(m.group(0))

    return data

# ================= DRIVER =================
def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=opts)

def inject_cookies(driver):
    driver.get("https://x.com/")
    time.sleep(3)

    driver.add_cookie({
        "name": "auth_token",
        "value": AUTH_TOKEN,
        "path": "/",
        "secure": True,
        "httpOnly": True
    })
    driver.add_cookie({
        "name": "ct0",
        "value": CT0,
        "path": "/",
        "secure": True
    })

    # driver.refresh()
    driver.get(f"https://x.com/{USERNAME}")
    time.sleep(5)

def is_pinned(tweet):
    try:
        tweet.find_element(By.XPATH, ".//*[text()='Pinned']")
        return True
    except:
        return False

def wait_for_tweets(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//article"))
    )

# ================= MAIN ===================
def crawler_main():
    logging.info("START CRAWLING")

    driver = create_driver()
    inject_cookies(driver)

    try:
        wait_for_tweets(driver)
    except Exception:
        logging.error("Tweets did not load — aborting")
        driver.quit()
        return

    seen_ioc = load_existing_hashes()
    logging.info(f"Loaded {len(seen_ioc)} existing hashes from CSV")

    seen_index = load_existing_ioc_index()
    logging.info(f"Loaded {len(seen_index)} indexed IOCs")

    hash_tweets_seen = 0
    new_ioc_count = 0

    processed_articles = set()
    no_new_rounds = 0
    MAX_IDLE_ROUNDS = 3

    while hash_tweets_seen < MAX_HASH_TWEETS and no_new_rounds < MAX_IDLE_ROUNDS:
        tweets = driver.find_elements(By.XPATH, "//article")
        new_seen_this_round = False

        for t in tweets:
            tid = t.get_attribute("outerHTML")
            if tid in processed_articles:
                continue
            processed_articles.add(tid)
            new_seen_this_round = True

            if is_pinned(t):
                continue

            text = t.text.strip()
            if not text or not has_ioc(text):
                continue

            hash_tweets_seen += 1

            parsed = parse(text, [])

            if not parsed["iocs"]:
                continue

            tweet_time = get_tweet_time(t)

            # posts.txt + iocs.txt must be written together
            for ioc in parsed["iocs"]:
                if ioc in seen_ioc:
                    logging.info(
                        f"Duplicate IOC skipped | hash={ioc} | source={seen_ioc[ioc]}"
                    )
                    continue

                # ---- SAVE POST ----
                save_txt(parsed, tweet_time, ioc)
                seen_ioc[ioc] = "runtime"
                new_ioc_count += 1
                logging.info(f"New IOC collected | hash={ioc}")

                # ---- INDEX IOC (ONLY IF POST IS NEW) ----
                related_iocs = set()
                related_iocs.add(ioc)

                if parsed.get("ip"):
                    related_iocs.add(parsed["ip"])

                if parsed.get("url"):
                    related_iocs.add(parsed["url"])

                index_exists = os.path.isfile(IOC_INDEX_FILE)

                with open(IOC_INDEX_FILE, "a", encoding="utf-8") as f:
                    if not index_exists:
                        f.write("# ioc | ioc_type\n")

                    for idx_ioc in related_iocs:
                        if idx_ioc in seen_index:
                            continue

                        ioc_type = get_ioc_type(idx_ioc)
                        f.write(f"{idx_ioc} | {ioc_type}\n")
                        seen_index.add(idx_ioc)

            # posts.csv
            for ioc in parsed["iocs"]:
                if ioc in seen_ioc:
                    logging.info(
                        f"Duplicate IOC skipped | hash={ioc} | source={seen_ioc[ioc]}"
                    )
                    continue

                save_txt(parsed, tweet_time, ioc)

                seen_ioc[ioc] = "runtime"
                new_ioc_count += 1

                logging.info(f"New IOC collected | hash={ioc}")

            if hash_tweets_seen >= MAX_HASH_TWEETS:
                break

        if not new_seen_this_round:
            no_new_rounds += 1
        else:
            no_new_rounds = 0

        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

    driver.quit()

    logging.info(
        f"FINISH CRAWLING | "
        f"hash_tweets_seen={hash_tweets_seen} | "
        f"new_ioc={new_ioc_count}"
    )
