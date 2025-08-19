import os, re, time, hashlib, argparse
from urllib.parse import urlparse
import urllib.parse as up
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CLOSE_TEXT_PATTERNS = [
    r"(?i)^close$",
    r"(?i)^tutup$",
    r"(?i)^cerrar$",
    r"(?i)^fechar$",
    r"(?i)^\s*[x×]\s*$",
]

CLOSE_SELECTORS = [
    '[aria-label="Close"]',
    '[aria-label="Tutup"]',
    '[aria-label="Cerrar"]',
    '[aria-label="Fechar"]',
    'div[aria-label="Close"]',
    'div[aria-label="Tutup"]',
    'div[aria-label="Cerrar"]',
    'div[aria-label="Fechar"]',
    '[role="dialog"] [aria-label="Close"]',
    'div[role="dialog"] [aria-label="Close"]',
]

def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    base = (parsed.netloc + parsed.path).strip("/").replace("/", "_")
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return (base or "page") + "_" + h

# def read_urls(csv_path: str):
#     df = pd.read_csv(csv_path, sep=None, engine="python")
#     col = "Post Url"
#     if col not in df.columns:
#         # try case/underscore variations
#         for c in df.columns:
#             if c.lower().replace("_", " ") == "post url":
#                 col = c
#                 break
#         else:
#             raise ValueError("Column 'Post Url' not found.")
#     urls = [u for u in df[col].dropna().astype(str) if u.strip()]
#     return urls

def read_urls(csv_path: str, column_name="Original URL"):
    df = pd.read_csv(csv_path, sep=None, engine="python")
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in {csv_path}")
    return df[column_name].dropna().astype(str).tolist()

def setup_driver(headless=True, width=1366, height=768):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-US")

    # Chrome
    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

    # Chromium
    opts.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=opts)
    
    driver.set_page_load_timeout(30)
    return driver

def try_close_modal(driver):
    # 1) Try buttons with visible text (various localizations)
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            try:
                name = (b.text or "").strip()
                for pat in CLOSE_TEXT_PATTERNS:
                    if re.fullmatch(pat, name):
                        b.click()
                        time.sleep(0.6)
                        return True
            except Exception:
                pass
    except Exception:
        pass

    # 2) Try common selectors
    for sel in CLOSE_SELECTORS:
        try:
            el = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            el.click()
            time.sleep(0.6)
            return True
        except Exception:
            pass

    # 3) Try ESC on any dialog
    try:
        dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
        if dialogs:
            dialogs[0].send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return True
    except Exception:
        pass

    return False

def fullpage_screenshot(driver, path):
    """
    Full-page screenshot using Chrome DevTools Protocol (Selenium 4).
    Works in Chrome/Edge. Falls back to viewport if CDP fails.
    """
    try:
        # Get the page dimensions
        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        width = int(metrics["contentSize"]["width"])
        height = int(metrics["contentSize"]["height"])

        # Set device metrics to full size
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "mobile": False,
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "scale": 1
        })

        # Capture
        res = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "fromSurface": True,
            "captureBeyondViewport": True
        })
        import base64
        with open(path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        return True
    except Exception:
        # Fallback
        driver.save_screenshot(path)
        return False

def scrape(csv_path, outdir="shots", headless=True, delay=1.0, width=1366, height=768):
    os.makedirs(outdir, exist_ok=True)
    urls = read_urls(csv_path)
    if not urls:
        print("No URLs found.")
        return

    driver = setup_driver(headless=headless, width=width, height=height)

    for i, url in enumerate(urls, 1):
        # fname = slugify_url(url) + ".png"
        parsed = up.urlparse(url)
        qs = up.parse_qs(parsed.query)
        fb_id = qs.get("id", ["noid"])[0]   # default "noid" if not found
        fname = f"{fb_id}.png"
        
        outpath = os.path.join(outdir, fname)
        print(f"[{i}/{len(urls)}] {url}")
        try:
            driver.get(url)
            # allow DOM to build
            time.sleep(1.5)

            # Try multiple times (FB often spawns modal after a short delay)
            closed = False
            for _ in range(3):
                if try_close_modal(driver):
                    closed = True
                    time.sleep(0.5)
                time.sleep(0.4)

            # small settle time for images
            time.sleep(1.0)

            ok = fullpage_screenshot(driver, outpath)
            print(f"  → saved {outpath} (fullpage={ok}, modal_closed={closed})")
            time.sleep(delay)

        except TimeoutException:
            print("  ! navigation timeout")
        except Exception as e:
            print(f"  ! error: {e}")

    driver.quit()

def main():
    ap = argparse.ArgumentParser(description="Selenium Facebook Screenshotter (CSV -> PNG)")
    ap.add_argument("csv", help="CSV with 'Original URL' column (from prep_new_links)")
    ap.add_argument("--outdir", default="shots")
    ap.add_argument("--headful", action="store_true", help="Show browser window")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--width", type=int, default=1366)
    ap.add_argument("--height", type=int, default=768)
    args = ap.parse_args()

    scrape(
        csv_path=args.csv,
        outdir=args.outdir,
        headless=not args.headful,
        delay=args.delay,
        width=args.width,
        height=args.height,
    )

if __name__ == "__main__":
    main()