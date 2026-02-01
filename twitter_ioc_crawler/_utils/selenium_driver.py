import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .config import AUTH_TOKEN, CT0

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    return webdriver.Chrome(options=opts)

def inject_cookies(driver, username: str):
    driver.get("https://x.com")
    time.sleep(5)

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

    driver.get(f"https://x.com/{username}")
    time.sleep(5)

def wait_for_tweets(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, "//article"))
    )
