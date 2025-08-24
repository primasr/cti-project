import os, re, time, hashlib, argparse
from urllib.parse import urlparse
import urllib.parse as up
import pandas as pd
from datetime import datetime

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

MAX_HEIGHT_BY_SITE = {
    "facebook" : 12000,
    "twitter"  : 9000,
    "instagram": 9000,
    "youtube"  : 6000,
    "linkedin" : 11000,
    "telegram" : 9000,
    "other"    : 9000,
}

# ---------- helpers ----------
def _file_ok(path: str) -> bool:
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except Exception:
        return False

def timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    base = (parsed.netloc + parsed.path).strip("/").replace("/", "_")
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return (base or "page") + "_" + h

def read_urls(csv_path: str, column_name="Original URL"):
    df = pd.read_csv(csv_path, sep=None, engine="python")
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in {csv_path}")
    return df[column_name].dropna().astype(str).tolist()

def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def is_facebook(url: str) -> bool:
    d = domain_of(url)
    return "facebook.com" in d

def is_twitter(url: str) -> bool:
    d = domain_of(url)
    return ("twitter.com" in d) or ("x.com" in d)

def is_instagram(url: str) -> bool:
    d = domain_of(url)
    return "instagram.com" in d

def is_youtube(url: str) -> bool:
    d = domain_of(url)
    return ("youtube.com" in d) or ("youtu.be" in d)

def is_linkedin(url: str) -> bool:
    d = domain_of(url)
    return "linkedin.com" in d

def is_telegram(url: str) -> bool:
    d = domain_of(url)
    return ("t.me" in d) or ("telegram.me" in d) or ("web.telegram.org" in d)

def extract_fb_basename(url: str) -> str:
    """Prefer ?id=... for Ads/Profile; fallback to slug."""
    p = up.urlparse(url)
    qs = up.parse_qs(p.query)
    fb_id = qs.get("id", ["noid"])[0]
    return fb_id if fb_id != "noid" else slugify_url(url)

def extract_tweet_id(url: str) -> str:
    """
    Expecting:
      https://twitter.com/<user>/status/<id>
      https://x.com/<user>/status/<id>
    """
    p = urlparse(url)
    parts = [seg for seg in p.path.split("/") if seg]
    try:
        i = parts.index("status")
        tid = parts[i+1].split("?")[0]
        return tid
    except Exception:
        return "noid"

def extract_instagram_code(url: str) -> str:
    """
    Supports:
      https://www.instagram.com/p/<code>/
      https://www.instagram.com/reel/<code>/
      https://www.instagram.com/reels/<code>/
      https://www.instagram.com/tv/<code>/
    """
    p = urlparse(url)
    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        return "noid"
    try:
        if parts[0] in ("p", "reel", "reels", "tv") and len(parts) >= 2:
            code = parts[1].split("?")[0]
            return code or "noid"
        return "noid"
    except Exception:
        return "noid"

def extract_youtube_id(url: str) -> str:
    """
    Supports:
      https://www.youtube.com/watch?v=<id>
      https://youtu.be/<id>
    """
    p = urlparse(url)
    if "youtu.be" in p.netloc.lower():
        code = (p.path.strip("/").split("/")[0] if p.path else "").split("?")[0]
        return code or "noid"
    qs = up.parse_qs(p.query or "")
    vid = qs.get("v", ["noid"])[0]
    return vid if vid else "noid"

def extract_linkedin_activity_id(url: str) -> str:
    """
    From examples like:
      .../posts/<slug>-activity-7362315281374851072-FWoJ?...  -> 7362315281374851072
    """
    m = re.search(r"activity-(\d+)", url)
    if m:
        return m.group(1)
    # Fallback: last non-empty path segment (without params)
    p = urlparse(url)
    segs = [s for s in p.path.split("/") if s]
    if segs:
        return segs[-1].split("?")[0] or "noid"
    return "noid"

def extract_telegram_slug(url: str) -> str:
    """
    For t.me/<handle> or t.me/<handle>/<post>, we take the first non-empty segment.
    Examples:
      https://t.me/byondkhiva           -> byondkhiva
      https://t.me/nsndjekrkkrkrbot     -> nsndjekrkkrkrbot
      https://t.me/somechannel/1234     -> somechannel
    """
    p = urlparse(url)
    segs = [s for s in p.path.split("/") if s]
    return (segs[0].split("?")[0] if segs else "noid") or "noid"

# ---------- selenium setup ----------
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

# ---------- fb modal handling ----------
def try_close_facebook_modal(driver):
    # 1) buttons with visible text
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

    # 2) common selectors
    for sel in CLOSE_SELECTORS:
        try:
            el = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            el.click()
            time.sleep(0.6)
            return True
        except Exception:
            pass

    # 3) ESC on any dialog
    try:
        dialogs = driver.find_elements(By.CSS_SELECTOR, '[role="dialog"]')
        if dialogs:
            dialogs[0].send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return True
    except Exception:
        pass

    return False

def try_close_instagram_modal(driver):
    """
    Close IG's signup/login modal:
    <div role="button"><svg aria-label="Close"><title>Close</title>...</svg></div>
    Click the nearest ancestor with role=button (more reliably clickable).
    """
    def _click(el):
        try:
            el.click()
            time.sleep(0.3)
            return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.3)
                return True
            except Exception:
                return False

    # XPath: find the svg with aria-label/title 'Close', then go up to the clickable role=button
    xpaths = [
        "//*[name()='svg' and (@aria-label='Close' or ./*[name()='title' and normalize-space(.)='Close'])]/ancestor::*[@role='button'][1]",
        # fallback: any element with aria-label=Close that is a button
        "//*[@role='button' and (@aria-label='Close' or contains(., 'Close'))]"
    ]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xp)))
            if _click(el):
                return True
        except Exception:
            pass

    # ESC as last resort
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.3)
        return True
    except Exception:
        return False

def try_close_linkedin_modal(driver):
    """
    Best-effort close for small LinkedIn pop dialogs when logged out.
    We look for a dialog and 'Dismiss'/'Close' buttons; fallback ESC.
    """
    def _click(el):
        try:
            el.click(); time.sleep(0.25); return True
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.25); return True
            except Exception:
                return False

    # Common close patterns
    xpaths = [
        "//div[@role='dialog']//button[contains(@aria-label,'Dismiss') or contains(@aria-label,'Close')]",
        "//div[@role='dialog']//*[@role='button' and (contains(.,'Dismiss') or contains(.,'Close'))]",
    ]
    for xp in xpaths:
        try:
            el = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xp)))
            if _click(el):
                return True
        except Exception:
            pass

    # ESC fallback
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.2)
        return True
    except Exception:
        return False

# ---------- screenshot ----------
def fullpage_screenshot(driver, path, max_height=8000):
    """
    Full-page screenshot via CDP with a safe height cap.
    ALWAYS resets device metrics afterward so the next page isn't stuck tall.
    """
    try:
        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        width = int(metrics["contentSize"]["width"])
        height = int(metrics["contentSize"]["height"])

        # Clamp very tall pages to avoid huge captures
        cap_h = max(500, min(height, int(max_height)))

        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "mobile": False,
            "width": width,
            "height": cap_h,
            "deviceScaleFactor": 1,
            "scale": 1
        })

        res = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "fromSurface": True,
            "captureBeyondViewport": True
        })

        import base64
        with open(path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        ok = True
    except Exception:
        # Fallback: simple viewport screenshot
        driver.save_screenshot(path)
        ok = False
    finally:
        # CRITICAL: reset so the NEXT page doesn't inherit huge height
        try:
            driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
        except Exception:
            pass
    return ok

# ---------- unified scraper ----------
def scrape(csv_path, outdir="shots", headless=True, delay=1.0, width=1366, height=768):
    os.makedirs(outdir, exist_ok=True)
    urls = read_urls(csv_path)

    batch_ts = timestamp_id()

    # report dir
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"reports_{batch_ts}.xlsx")

    if not urls:
        print("No URLs found.")
        pd.DataFrame(columns=["No", "Original URL", "Status", "Screenshot Saved As"]).to_excel(report_path, index=False)
        print(f"→ wrote empty report: {report_path}")
        return

    results = []

    driver = setup_driver(headless=headless, width=width, height=height)
    try:
        for i, url in enumerate(urls, 1):
            status = ""
            saved_as = ""
            base_name = ""
            socmed_name = ""

            # choose platform + filename base
            if is_facebook(url):
                base_name = extract_fb_basename(url)
                socmed_name = "facebook"
            elif is_twitter(url):             
                tid = extract_tweet_id(url)
                base_name = tid if tid != "noid" else slugify_url(url)
                socmed_name = "twitter"
            elif is_instagram(url):
                ig = extract_instagram_code(url)
                base_name = ig if ig != "noid" else slugify_url(url)
                socmed_name = "instagram"           
            elif is_youtube(url):
                yid = extract_youtube_id(url)
                base_name = yid if yid != "noid" else slugify_url(url)
                socmed_name = "youtube"     
            elif is_linkedin(url):
                lid = extract_linkedin_activity_id(url)
                base_name = lid if lid != "noid" else slugify_url(url)
                socmed_name = "linkedin"
            elif is_telegram(url):
                tslug = extract_telegram_slug(url)
                base_name = tslug if tslug != "noid" else slugify_url(url)
                socmed_name = "telegram"
            else:
                # unknown platform → still handle (no modal)
                base_name = slugify_url(url)
                socmed_name = "other"

            fname = f"{batch_ts}_{socmed_name}_{base_name}.png"
            outpath = os.path.join(outdir, fname)

            print(f"[{i}/{len(urls)}] {url}")
            try:
                driver.get(url)

                # --- platform-specific flow ---
                if is_facebook(url):
                    # allow DOM to build
                    time.sleep(1.5)
                    # Try multiple times (FB often spawns modal after a short delay)
                    closed = False
                    for _ in range(3):
                        if try_close_facebook_modal(driver):
                            closed = True
                            time.sleep(0.5)
                        time.sleep(0.4)
                    # small settle time for images
                    time.sleep(1.0)

                elif is_twitter(url):
                    # Wait for body first
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                    except Exception:
                        pass

                    # Wait for tweet container <article> to show
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.presence_of_element_located((By.TAG_NAME, "article"))
                        )
                    except Exception:
                        pass

                    # Extra settle time for images and text
                    time.sleep(2.0)

                    # Small scroll to trigger lazy-loaded media
                    try:
                        driver.execute_script("window.scrollTo(0, 400);")
                    except Exception:
                        pass
                    time.sleep(2.0)

                elif is_instagram(url):
                    # Wait for body and some content to exist
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    except Exception:
                        pass

                    # Give IG a moment to render the modal if it will appear
                    time.sleep(1.0)

                    # Try to close the IG modal (signup/login)
                    # Try a few times because it can animate in slightly later
                    for _ in range(3):
                        if try_close_instagram_modal(driver):
                            break
                        time.sleep(0.4)

                    # Ensure a post container or media is present
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.TAG_NAME, "article")),
                                EC.presence_of_element_located((By.CSS_SELECTOR, "main img"))
                            )
                        )
                    except Exception:
                        pass

                    # Extra settle for images/text
                    time.sleep(1.0)

                    # Small scroll to trigger lazy media
                    try:
                        driver.execute_script("window.scrollTo(0, 400);")
                    except Exception:
                        pass
                    time.sleep(0.7)

                elif is_youtube(url):
                    # YouTube: wait for body, then player, then settle and small scroll
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    except Exception:
                        pass
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "#player")),
                                EC.presence_of_element_located((By.TAG_NAME, "ytd-player"))
                            )
                        )
                    except Exception:
                        pass
                    time.sleep(1.5)  # let thumbnails/controls paint
                    try:
                        driver.execute_script("window.scrollTo(0, 300);")
                    except Exception:
                        pass
                    time.sleep(0.7)

                elif is_linkedin(url):
                    # Body first
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    except Exception:
                        pass

                    # Give LI a moment; sometimes a tiny dialog appears
                    time.sleep(0.8)
                    for _ in range(3):
                        if try_close_linkedin_modal(driver):
                            break
                        time.sleep(0.3)

                    # Wait for post layout: article/main or feed detail container
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.TAG_NAME, "article")),
                                EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='feed-detail-main']")),
                            )
                        )
                    except Exception:
                        pass

                    # Settle and reveal more area
                    time.sleep(1.0)
                    try:
                        driver.execute_script("window.scrollTo(0, 400);")
                    except Exception:
                        pass
                    time.sleep(0.7)

                elif is_telegram(url):
                    # Wait for body, then Telegram landing container to exist
                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    except Exception:
                        pass
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".tgme_page")),          # main page wrapper
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".tgme_page_widget")),   # embedded widget
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".tgme_page_title")),    # title
                            )
                        )
                    except Exception:
                        pass

                    # Small settle to let images/text paint
                    time.sleep(1.0)

                    # Nudge scroll to trigger any lazy assets
                    try:
                        driver.execute_script("window.scrollTo(0, 400);")
                    except Exception:
                        pass
                    time.sleep(0.7)

                else:
                    # generic: short wait
                    time.sleep(1.0)

                ok = fullpage_screenshot(driver, outpath, max_height=MAX_HEIGHT_BY_SITE.get(socmed_name, 9000))

                if ok and _file_ok(outpath):
                    status = "SUCCESS"
                    saved_as = outpath
                else:
                    if _file_ok(outpath):
                        status = "SUCCESS"
                        saved_as = outpath
                    else:
                        status = "FAILED: screenshot empty or not created"

                print(f"  → saved {outpath}")
                time.sleep(delay)

            except TimeoutException as te:
                status = f"TimeoutException: {te.__class__.__name__}"
                print("  ! navigation timeout")
            except Exception as e:
                status = f"Exception: {type(e).__name__}: {e}"
                print(f"  ! error: {e}")

            results.append({
                "No": i,
                "Original URL": url,
                "Status": status if status else "UNKNOWN",
                "Screenshot Saved As": saved_as
            })

    finally:
        df_report = pd.DataFrame(results, columns=["No", "Original URL", "Status", "Screenshot Saved As"])
        try:
            df_report.to_excel(report_path, index=False)
            print(f"→ wrote report: {report_path} ({len(df_report)} rows)")
        except Exception as e:
            fallback_csv = os.path.splitext(report_path)[0] + ".csv"
            df_report.to_csv(fallback_csv, index=False)
            print(f"→ could not write Excel ({e}); wrote CSV instead: {fallback_csv}")

        driver.quit()

def main():
    ap = argparse.ArgumentParser(description="Selenium Social Screenshotter (CSV -> PNG) for Facebook & Twitter/X")
    ap.add_argument("csv", help="CSV with 'Original URL' column")
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
