# Twitter IOC Crawler & TIP Enrichment Pipeline

This project is a lightweight **Cyber Threat Intelligence (CTI) pipeline** that crawls Twitter (X) for Indicators of Compromise (IOCs), stores them locally, enriches them using multiple Threat Intelligence Platforms (TIPs), and forwards the enriched results to a SIEM.

The pipeline is designed for testing, learning, and validating IOC collection and enrichment workflows.

## Overview

The pipeline consists of three main components:

1. Crawler
Collects tweets, extracts IOCs, and stores them locally.
2. TIP Enrichment
Enriches collected IOCs using VirusTotal, AlienVault OTX, MalwareBazaar, and AbuseIPDB.
3. Orchestrator
Runs the crawler first, then enriches the collected IOCs.

## File Structure

1. `crawler.py`
Crawls Twitter using Selenium, extracts IOCs from tweets, and saves them to an index file.
2. `tip.py`
Enriches collected IOCs using multiple Threat Intelligence Platforms and sends the results to a SIEM.
3. `main.py`
Entry point that runs the crawler and TIP enrichment sequentially.

## Folder Structure

1. ### _utils/
Contains helper modules and shared utility functions used by the main pipeline, such as logging, configuration, Selenium setup, IOC parsing, file I/O, and TIP API wrappers.

2. ### old/
Contains archived versions of older crawler and TIP implementations, kept for reference and historical purposes.

3. ### tip_tests/
Contains standalone test scripts used to validate the functionality of each individual Threat Intelligence Platform (TIP) integration.

## How It Works

1. ### Twitter Crawling
   - Selenium opens Twitter using stored cookies.
   - Tweets are loaded and scrolled automatically.
   - Pinned tweets are skipped.
   - Each tweet is scanned for IOCs (IP, URL, hash).
   - Duplicate IOCs (based on IOC + tweet link) are skipped.
   - New IOCs are saved locally.

2. ### IOC Enrichment
   - Previously collected IOCs are loaded from the index.
   - Already enriched IOCs are skipped.
   - Each IOC is enriched using:
      * VirusTotal (IP, URL, hash)
      * AlienVault OTX (IP, URL, hash)
      * MalwareBazaar (hash only)
      * AbuseIPDB (IP only)
   - Results are normalized and stored.
   - Newly enriched IOCs are forwarded to the SIEM.

3. ### Execution Flow
   - The crawler runs first.
   - TIP enrichment runs after crawling completes.

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

## Requirements
- Python 3.x
- Selenium-compatible browser (e.g., Chromium / Chrome)
- Valid API keys for:
   * VirusTotal
   * AlienVault OTX
   * MalwareBazaar
   * AbuseIPDB
- Twitter account cookies for authenticated crawling

## Outputs
The pipeline generates the following files:

- `logging.log`
Contains execution logs for crawling, enrichment, warnings, and errors.
- `iocs.txt`
Stores the list of IOCs collected from Twitter, including:
   * IOC value
   * IOC type
   * Tweet (X) link
- `tip_results.txt`
Stores the final enrichment results after checking IOC verdicts from multiple Threat Intelligence Platforms.
