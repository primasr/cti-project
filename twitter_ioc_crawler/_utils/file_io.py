import os
import logging
from datetime import datetime

from .config import IOC_INDEX_FILE
from .time_utils import UTC_PLUS_7

def load_existing_iocs():
    """
    Load existing IOC + twitter_link combinations
    Return: set of (ioc, twitter_link)
    """
    seen = set()

    if not os.path.isfile(IOC_INDEX_FILE):
        logging.info("iocs.txt not found, starting fresh")
        return seen

    try:
        with open(IOC_INDEX_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    seen.add((parts[0], parts[2]))
    except Exception as e:
        logging.error(f"Failed to load existing IOCs: {e}", exc_info=True)

    return seen

def save_ioc(ioc: str, ioc_type: str, twitter_link: str):
    """
    Append ONE IOC record to iocs.txt
    Always ensures it is written on a NEW LINE.
    """
    exists = os.path.isfile(IOC_INDEX_FILE)

    try:
        # --- Ensure file ends with newline ---
        if exists:
            with open(IOC_INDEX_FILE, "rb") as f:
                f.seek(0, os.SEEK_END)
                if f.tell() > 0:
                    f.seek(-1, os.SEEK_END)
                    last_char = f.read(1)
                else:
                    last_char = b"\n"

            if last_char != b"\n":
                with open(IOC_INDEX_FILE, "a", encoding="utf-8") as f:
                    f.write("\n")

        # --- Append new IOC ---
        with open(IOC_INDEX_FILE, "a", encoding="utf-8") as f:
            if not exists:
                f.write("# ioc | ioc_type | twitter_link\n")

            f.write(f"{ioc} | {ioc_type} | {twitter_link}\n")

    except Exception as e:
        logging.error(f"Failed to save IOC={ioc}: {e}", exc_info=True)


