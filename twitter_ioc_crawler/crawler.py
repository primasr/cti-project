import time
import os
import logging
from selenium.webdriver.common.by import By

from _utils.logging_config import setup_logging
from _utils.config import MAX_HASH_TWEETS, IOC_INDEX_FILE
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


setup_logging()

# ================= MAIN ===================
def crawler_main():
    logging.info("[✓] START CRAWLING")

    driver = create_driver()
    inject_cookies(driver)

    try:
        wait_for_tweets(driver)
    except Exception:
        logging.error("Tweets did not load — aborting")
        driver.quit()
        return

    seen_ioc = load_existing_iocs()
    logging.info(f"Loaded {len(seen_ioc)} existing IOC records")

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

            # pinned tweet check
            try:
                t.find_element(By.XPATH, ".//*[text()='Pinned']")
                continue
            except:
                pass

            text = t.text.strip()
            if not text or not has_ioc(text):
                continue

            hash_tweets_seen += 1

            parsed = parse_tweet(text, images=[])

            if not parsed["iocs"]:
                continue

            # get tweet time
            tweet_time = None
            try:
                time_elem = t.find_element(By.XPATH, ".//time")
                tweet_time = time_elem.get_attribute("datetime")
            except:
                pass

            tweet_link = ""
            try:
                link_elem = t.find_element(
                    By.XPATH,
                    ".//a[contains(@href, '/status/')]"
                )
                href = link_elem.get_attribute("href")
                if href:
                    tweet_link = href.split("?")[0]  # remove tracking params
            except:
                pass

            # iocs.txt
            for ioc in parsed["iocs"]:
                if (ioc, tweet_link) in seen_ioc:
                    logging.info(f"Duplicate IOC skipped | IOC={ioc}")
                    continue

                # ---- SAVE POST ----
                ioc_type = get_ioc_type(ioc)
                save_ioc(ioc, ioc_type, tweet_link)
                seen_ioc.add((ioc, tweet_link))
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
        f"[✓] FINISH CRAWLING | "
        f"hash_tweets_seen={hash_tweets_seen} | "
        f"new_ioc={new_ioc_count}"
    )


# if __name__ == "__main__":
#     crawler_main()
