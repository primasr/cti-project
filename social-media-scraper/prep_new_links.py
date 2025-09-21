import pandas as pd
from urllib.parse import urlparse
import argparse
import re, os
from datetime import datetime

def _stamp_filename(filename: str, ts: str | None = None, default_ext: str = ".csv") -> str:
    """Insert _YYYYmmdd_HHMMSS before the extension (or add .csv if missing)."""
    ts = ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    root, ext = os.path.splitext(filename)
    if not ext:
        ext = default_ext
    return f"{root}_{ts}{ext}"

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

def find_new_links(source_csv, db_excel, source_col = "Post Url", dest_col = "Full URL\n[Ketik lengkap tanpa http dan https]", out_file="data.csv", out_dir="cleaned_data"):
    df_src = pd.read_csv(source_csv, sep=None, engine="python")
    if source_col not in df_src.columns:
        raise ValueError(f"Column '{source_col}' not found in source file")

    db = pd.read_excel(db_excel)
    dest_col = "Full URL\n[Ketik lengkap tanpa http dan https]"
    if dest_col not in db.columns:
        raise ValueError(f"Column '{dest_col}' not found in DB Excel")

    src_urls = df_src[source_col].dropna().astype(str)
    db_urls = db[dest_col].dropna().astype(str)

    src_norm = src_urls.apply(normalize_url)
    db_norm = db_urls.apply(normalize_url)

    new_mask = ~src_norm.isin(set(db_norm))
    new_df = pd.DataFrame({
        "Original URL": src_urls[new_mask].values,
        "Normalized URL": src_norm[new_mask].values
    }).drop_duplicates(subset=["Normalized URL"]).reset_index(drop=True)

    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # Build stamped output filename
    stamped = _stamp_filename(out_file)             # e.g., data_20250921_153012.csv
    out_path = os.path.join(out_dir, stamped)

    if not new_df.empty:
        new_df.to_csv(out_path, index=False)
        print(f"✅ Found {len(new_df)} new links → saved to {out_path}")
    else:
        print("ℹ️ No new links found.")
    return new_df

def main():
    ap = argparse.ArgumentParser(description="Find new unique links vs DB")
    ap.add_argument("source_csv", help="Alerts CSV (with 'Post Url' column)")
    ap.add_argument("db_excel", help="Database Excel file")
    ap.add_argument("--col_csv", default="Post Url", help="Column name in source CSV (default: 'Post Url')")
    ap.add_argument("--col_excel", default="Full URL\n[Ketik lengkap tanpa http dan https]", help="Column name in dest Excel (default: 'Full URL\n[Ketik lengkap tanpa http dan https]')")
    ap.add_argument("--outfile", default="data.csv", help="Output CSV filename (default: data.csv)")
    ap.add_argument("--outdir", default="cleaned_data", help="Directory name to save the output (default: 'cleaned_data')")

    args = ap.parse_args()
    find_new_links(
        args.source_csv,
        args.db_excel,
        source_col=args.col_csv,
        dest_col=args.col_excel,
        out_file=args.outfile,
        out_dir=args.outdir
    )


if __name__ == "__main__":
    main()