import time
import os
import logging
from selenium.webdriver.common.by import By

from _utils.logging_config import setup_logging
from _utils.config import IOC_INDEX_FILE, TWITTER_USER_FILE
from _utils.selenium_driver import (
    create_driver,
    inject_cookies,
    wait_for_tweets,
)
from _utils.text_utils import has_ioc, get_ioc_type
from _utils.parser import parse_tweet
from _utils.file_io import (
    load_existing_iocs,
    save_ioc,
)

from _utils.twitter_user_loader import load_usernames


setup_logging()

# ================= MAIN ===================
def crawler_main(max_tweets: int = 3):

    logging.info("[✓] START CRAWLING")

    usernames = load_usernames(TWITTER_USER_FILE)

    if not usernames:
        logging.error("No usernames found to crawl")
        return

    for username in usernames:

        logging.info(f"[+] Crawling @{username}")

        driver = create_driver()
        inject_cookies(driver, username)

        try:
            wait_for_tweets(driver)
        except Exception:
            logging.error(f"Tweets did not load for @{username}")
            driver.quit()
            continue

        # ---- Existing IOC DB ----
        seen_ioc = load_existing_iocs()

        ioc_tweets_seen = 0
        new_ioc_count = 0

        processed_tweet_ids = set()
        no_new_rounds = 0
        MAX_IDLE_ROUNDS = 3

        while ioc_tweets_seen < max_tweets and no_new_rounds < MAX_IDLE_ROUNDS:

            tweets = driver.find_elements(By.XPATH, "//article")
            new_seen_this_round = False

            for t in tweets:

                tweet_link = ""
                tweet_id = ""

                try:
                    link_elem = t.find_element(
                        By.XPATH,
                        ".//a[contains(@href, '/status/')]"
                    )
                    href = link_elem.get_attribute("href")

                    if href:
                        tweet_link = href.split("?")[0]
                        tweet_id = tweet_link.split("/")[-1]

                except Exception:
                    pass

                if not tweet_id or tweet_id in processed_tweet_ids:
                    continue

                processed_tweet_ids.add(tweet_id)
                new_seen_this_round = True

                try:
                    t.find_element(By.XPATH, ".//*[text()='Pinned']")
                    continue
                except Exception:
                    pass

                text = t.text.strip()

                if not text or not has_ioc(text):
                    continue

                ioc_tweets_seen += 1

                parsed = parse_tweet(text, images=[])

                if not parsed["iocs"]:
                    continue

                for ioc in parsed["iocs"]:

                    if ioc in seen_ioc:
                        logging.info(f"Duplicate IOC skipped | IOC={ioc}")
                        continue

                    ioc_type = get_ioc_type(ioc)

                    save_ioc(ioc, ioc_type, tweet_link)

                    seen_ioc.add(ioc)
                    new_ioc_count += 1

                    logging.info(
                        f"New IOC collected | "
                        f"type={ioc_type} | "
                        f"ioc={ioc}"
                    )

                if ioc_tweets_seen >= max_tweets:
                    break

            if not new_seen_this_round:
                no_new_rounds += 1
            else:
                no_new_rounds = 0

            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)

        driver.quit()

        logging.info(
            f"[✓] FINISH @{username} | "
            f"ioc_tweets_seen={ioc_tweets_seen} | "
            f"new_ioc={new_ioc_count}"
        )

    logging.info("[✓] ALL USER CRAWLING FINISHED")
