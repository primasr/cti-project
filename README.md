# cti-project

This project contains two scripts:

1. **prep_new_links.py**  
   - Prepares a list of **new, unique Facebook URLs** that are not yet in your reference database.  
   - It cleans and normalizes URLs (removes `http/https/www`, trims newlines).  
   - Outputs a `new_links.csv` file containing only links that are not already present in the database.

2. **fb_selenium_scraper.py**  
   - Reads `new_links.csv` and opens each URL in Chromium using Selenium.  
   - Closes Facebook login pop-ups if present.  
   - Takes **full-page screenshots** of each page.  
   - Saves screenshots as `{id}.png` in the specified output folder.

---

## Requirements

Install required Python packages:

```bash
pip install selenium pandas openpyxl
```

## Usage

### Step 1: Find new links

Run the prep script to compare the alert CSV against your database Excel file:

```bash
python3 prep_new_links.py alerts.csv database.xlsx --out new_links.csv
```
- alerts.csv → your exported alerts file (must have column Post Url)
- database.xlsx → your Excel database (must have column Full URL [Ketik lengkap tanpa http dan https])
- new_links.csv → output file containing only new, unique links


### Step 2: Scrape new links

Run the scraper to capture screenshots:

```bash
python fb_selenium_scraper.py new_links.csv --outdir shots
```
- new_links.csv → output from step 1 (must have column Original URL)
- shots/ → folder where screenshots will be saved

## Output
- new_links.csv
Contains the original and normalized URLs of links not yet in the DB.
- shots/
Contains full-page screenshots named after the Facebook id value. Example:

```text
shots/
 ├─ 61578564095904.png
 ├─ 61579116255147.png
 └─ ...
```
