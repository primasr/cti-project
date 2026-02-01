# Twitter IOC Crawler & TIP Enrichment Pipeline

This project is a lightweight **Cyber Threat Intelligence (CTI) pipeline** designed to crawl Twitter (X) for Indicators of Compromise (IOCs), store them locally, enrich them using multiple Threat Intelligence Platforms (TIPs), and optionally forward enriched results to a SIEM. It is intended for testing, learning, and validating IOC collection and enrichment workflows in a modular and automation-friendly environment.

The pipeline is composed of two core components: a Crawler that collects tweets from configurable Twitter usernames and extracts IOCs (hash, IP, URL), and a TIP Enrichment engine that enriches collected IOCs using VirusTotal, AlienVault OTX, MalwareBazaar, and AbuseIPDB. The system supports runtime customization such as tweet count selection and optional SIEM forwarding.

## Latest Update (Feb 2nd 2026)

The pipeline now supports runtime customization and better logging.

1. Custom Twitter Username List
Users can define which X accounts to crawl via a text file instead of hardcoding.

2. Custom Number of Tweets to Crawl
Users can specify how many IOC-containing tweets to process. Default is 3.

3. Optional SIEM Forwarding
Users can choose whether to send enrichment results to SIEM. Default is disabled.

4. Dual Log Output
Logs are written to:

- `logging.log`
- `twitter_ioc_crawler_log.txt`

5. Python 3.9 Compatibility Adjustments
Typing updated to avoid Python 3.10-only syntax.

6. Improved IOC Detection
Supports SHA256 hashes, IPv4 addresses, and HTTP/HTTPS URLs.

## How to Run

Run with default behavior (SIEM disabled):
```python
python3 main.py --tweets 2
```

If you want to forward the results to SIEM:
```python
python3 main.py --tweets 2 --siem
```

## Requirements
- Python 3.9 (or higher)
- Selenium-compatible browser (e.g., Chromium / Chrome)
- Valid API keys for:
   * VirusTotal
   * AlienVault OTX
   * MalwareBazaar
   * AbuseIPDB
   * SIEM (if needed)
- Twitter account cookies for authenticated crawling (_AUTH_TOKEN_ & _CT0_)

## Input(s)
You need to create a `.txt` file named `twitter_users.txt` containing the list of X/Twitter users that you want to crawl. The format is one username per line. See example.

## Outputs
The pipeline generates the following files:

- `logging.log` & `twitter_ioc_crawler_log.txt`
Contains execution logs for crawling, enrichment, warnings, and errors.
- `iocs.txt`
Stores the list of IOCs collected from Twitter, including:
   * IOC value
   * IOC type
   * Tweet (X) link
- `tip_results.txt`
Stores the final enrichment results after checking IOC verdicts from multiple Threat Intelligence Platforms.

## File Structure

1. `crawler.py`
Crawls Twitter using Selenium, extracts IOCs, and saves them locally.
2. `tip.py`
Enriches collected IOCs using multiple Threat Intelligence Platforms and sends the results to a SIEM.
3. `main.py`
Entry point. Supports CLI arguments for runtime configuration.

## Folder Structure

1. ### _utils/
Contains helper modules and shared utility functions used by the main pipeline, such as logging, configuration, Selenium setup, IOC parsing, file I/O, and TIP API wrappers.

2. ### old/
Contains archived versions of older crawler and TIP implementations, kept for reference and historical purposes.

3. ### tip_tests/
Contains standalone test scripts used to validate the functionality of each individual Threat Intelligence Platform (TIP) integration.

## Scripts

1. ### `crawler.py`

Responsible for collecting IOCs from Twitter.

Main features:
   - Uses Selenium with cookie-based authentication
   - Scrolls tweets dynamically
   - Detects and extracts IOCs from tweet text
   - Skips pinned tweets and duplicates
   - Stores IOC, IOC type, and tweet link

Configuration highlights:
   - MAX_HASH_TWEETS limits how many IOC-containing tweets are processed
   - Stops automatically after multiple idle scrolls

2. ### `tip.py`

Responsible for enriching IOCs using external TIPs.

Main features:
   - Loads IOC index from crawler output
   - Skips already enriched IOCs
   - Enriches IOCs using:
      * VirusTotal
      * AlienVault OTX
      * MalwareBazaar (hash only)
      * AbuseIPDB (IP only)
   - Normalizes key VirusTotal fields
   - Sends new enrichment results to SIEM
   - Rate-limited using VT_SLEEP

3. ### `main.py`

Pipeline entry point.

Execution order:
   - Run Twitter crawler
   - Run TIP enrichment

Parameters:
  - `-h`, `--help`      show this help message and exit
  - `--tweets TWEETS`   Number of tweets to crawl (default: 3)
  - `-siem`             Send enriched results to SIEM
