# cti-project

A project that can scrape several social media platforms (Facebook, Twitter, LinkedIn, Telegram, YouTube, and Instagram) and capture screenshots of them.

This project contains two scripts:

1. **prep_new_links.py**  
   - Prepares a list of **new, unique SocMed URLs** that are not yet in your reference database.  
   - It cleans and normalizes URLs (removes `http/https/www`, trims newlines).  
   - Outputs a `data_YYYYmmdd_HHMMSS.csv` file containing only links that are not already present in the database.

2. **socmed_scraper.py**  
   - Reads `data_YYYYmmdd_HHMMSS.csv` from previous file and opens each URL in Chromium/Chrome using Selenium.  
   - Closes SocMed login pop-ups if present.  
   - Takes **full-page screenshots** of each page.  
   - Saves screenshots as `{timestamp1}_{timestamp2}_{socialMediaName}_{id}.png` in the specified output folder.

---

## Requirements

Install required Python packages:

```bash
pip install selenium pandas openpyxl
```

## Usage

### Step 1: Find Unchecked Data from Database

Run the prep script to compare the new CSV file against your database Excel file:

```bash
python3 prep_new_links.py <url.csv> <database.xlsx>
```

#### Mandatory Arguments
- `url.csv` → your exported url file (must have column Post Url)
- `database.xlsx` → your Excel database (must have column 'Full URL [Ketik lengkap tanpa http dan https]')

#### Optional Arguments
- `--col_csv` → Column name in source CSV (default: 'Post Url')
- `--col_excel` → Column name in source Excel (default: 'Full URL [Ketik lengkap tanpa http dan https]')
- `--outfile` → Output CSV filename (default: 'data.csv')
- `--outdir` → Directory name to save the output (default: 'cleaned_data')

## Output
- `cleaned_data/`
Contains CSV file that need to be scrape. Example:

```text
cleaned_data/
 ├─ data_20250921_235833.csv
 ├─ data_20250922_001024.csv
 └─ ...
```

### Step 2: Scrape Social Media using the Provided Links

Run the scraper to capture screenshots:

```bash
python socmed_scraper.py <data.csv>
```

#### Mandatory Arguments
- `data.csv` → output from step 1 (must have column Original URL)

#### Optional Arguments
- `--col_csv` → Input custom column name (default: 'Original Url')
- `--outdir` → Output directory name (default: 'shots')
- `--headful` → Show browser window (default: 'False')
- `--delay` → Scraping delay between process (default: 1.0)
- `--width` → Screenshot media width (default: '1366')
- `--height` → Screenshot media height (default: '768')
- `--device` → Device Used: Chromium or Chrome (default: 'Chromium')

## Output
- `shots/`
Contains full-page screenshots named after the social media id value. Example:

```text
shots/
 ├─ 20250824
 ├─── 20250824_225325_twitter_1954714711330787623.png
 ├─── 20250824_225325_facebook_1292443142434634.png
 └─ ...
```
- `reports/`
Contains an Excel file reporting the status of each scraping process. Example:

```text
reports/
 ├─ reports_20250824_223937.xlsx
 ├─ reports_20250824_225325.xlsx
 └─ ...
```
