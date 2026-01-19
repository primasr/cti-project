# CTI IOC Pipeline

This project is a simple **Cyber Threat Intelligence (CTI) pipeline** that collects Indicators of Compromise (IOCs), enriches them with VirusTotal, and forwards the results to a SIEM.

## Pipeline Overview

1. **Crawler (`crawler.py`)**
   - Crawls posts from X (Twitter)
   - Extracts IOCs (hash, IP, URL)
   - Saves them into `iocs.txt` (pipe `|` separated)
   - Generates `posts.txt` with metadata for each collected post

2. **IOC Feed (`iocs.txt`)**
   - Central IOC index
   - Format:
     ```
     # ioc | ioc_type
     1.2.3.4 | ip
     abcd1234... | hash
     https://example.com | url
     ```

3. **VT Enrichment (`vt.py`)**
   - Reads IOCs from `iocs.txt`
   - Queries VirusTotal API
   - Saves enrichment results into `vt_results.txt`
   - Prevents duplicate enrichment

4. **SIEM Integration**
   - Runs in parallel in the `vt.py` file
   - Newly enriched IOCs are sent to SIEM
   - Includes score, confidence, and metadata

## Output Files

- `iocs.txt` – raw IOC feed
- `posts.txt` – raw posts collected from X/Twitter
- `vt_results.txt` – VirusTotal enrichment results
- `*.log` – execution logs

## Configuration

- Secrets and API keys are loaded from `.env`
- `.env` is ignored via `.gitignore`
- Please check `requirements.txt`

## Purpose

This pipeline is designed for:
- Lightweight CTI collection
- IOC enrichment automation
- SIEM-ready threat intelligence feeds
