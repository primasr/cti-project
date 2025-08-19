import pandas as pd
from urllib.parse import urlparse
import argparse
import re

def normalize_url(raw: str) -> str:
    """Remove http/https/www, keep host+path+query, strip trailing slash."""
    if not isinstance(raw, str) or not raw.strip():
        return ""
        
    #raw = raw.strip()

    # Clean hidden whitespace/newlines
    raw = re.sub(r"[\r\n\t]", "", raw).strip()
    
    p = urlparse(raw if raw.startswith("http") else "https://" + raw)

    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]

    path = p.path or ""
    query = f"?{p.query}" if p.query else ""
    norm = f"{host}{path}{query}"
    if norm.endswith("/"):
        norm = norm[:-1]
    return norm

def find_new_links(source_csv, db_excel, out_csv):
    df_src = pd.read_csv(source_csv, sep=None, engine="python")
    if "Post Url" not in df_src.columns:
        raise ValueError("Column 'Post Url' not found in source file")

    db = pd.read_excel(db_excel)
    col = "Full URL\n[Ketik lengkap tanpa http dan https]"
    if col not in db.columns:
        raise ValueError(f"Column '{col}' not found in DB Excel")

    src_urls = df_src["Post Url"].dropna().astype(str)
    db_urls = db[col].dropna().astype(str)

    src_norm = src_urls.apply(normalize_url)
    db_norm = db_urls.apply(normalize_url)

    new_mask = ~src_norm.isin(set(db_norm))
    new_df = pd.DataFrame({
        "Original URL": src_urls[new_mask].values,
        "Normalized URL": src_norm[new_mask].values
    }).drop_duplicates(subset=["Normalized URL"]).reset_index(drop=True)

    if not new_df.empty:
        new_df.to_csv(out_csv, index=False)
        print(f"✅ Found {len(new_df)} new links → saved to {out_csv}")
    else:
        print("ℹ️ No new links found.")
    return new_df

def main():
    ap = argparse.ArgumentParser(description="Find new unique links vs DB")
    ap.add_argument("source_csv", help="Alerts CSV (with 'Post Url' column)")
    ap.add_argument("db_excel", help="Database Excel file")
    ap.add_argument("--out", default="new_links.csv", help="Output CSV filename")
    args = ap.parse_args()
    find_new_links(args.source_csv, args.db_excel, args.out)

if __name__ == "__main__":
    main()