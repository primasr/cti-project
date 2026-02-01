import argparse

from crawler import crawler_main
from tip import tip_main

def main():
    parser = argparse.ArgumentParser(
        description="Twitter IOC Crawler + TIP Enrichment"
    )

    parser.add_argument(
        "--tweets",
        type=int,
        default=3,
        help="Number of tweets to crawl (default: 3)",
    )

    parser.add_argument(
        "--siem",
        action="store_true",
        help="Send enriched results to SIEM"
    )

    args = parser.parse_args()

    if args.tweets <= 0:
        parser.error("--tweets must be greater than 0")

    crawler_main(max_tweets=args.tweets)
    tip_main(send_to_siem=args.siem)


if __name__ == "__main__":
    main()