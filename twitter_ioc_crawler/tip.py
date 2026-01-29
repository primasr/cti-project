import time
import logging

from _utils.tip_siem import send_tip_result_to_siem
from _utils.logging_config import setup_logging
from _utils.config import VT_SLEEP
from _utils.tip_vt_api import vt_lookup
from _utils.tip_abuseipdb_api import abuseipdb_lookup
from _utils.tip_malwarebazaar_api import malwarebazaar_lookup
from _utils.tip_alienvault_api import alienvault_lookup
from _utils.tip_file_io import (
    load_ioc_index,
    load_existing_tip_results,
    save_tip_result,
)

setup_logging()

def tip_main():
    logging.info("[✓] START - Cheking to Threat Intelligence Tools")

    indexed_iocs = load_ioc_index()
    seen_results = load_existing_tip_results()

    logging.info(f"[+] Loaded {len(indexed_iocs)} IOCs from index")
    logging.info(f"[+] Loaded {len(seen_results)} existing VT results")

    new_count = 0

    for ioc, ioc_type, tweet_link in indexed_iocs:
        if ioc in seen_results:
            logging.info(f"Skipping IOC={ioc} (already enriched)")
            continue


        # ---- VirusTotal (IP, Url, Hash) ----
        logging.info(f"VT lookup | IOC={ioc}")
        result = vt_lookup(ioc)

        if not result:
            logging.warning(f"Skipped IOC={ioc} (unsupported type)")
            continue
        if "error" in result:
            logging.error(f"Error enriching IOC={ioc}: {result['error']}")
            continue

        # ---- Normalize VirusTotal fields ----
        result["vt_last_analysis_date"] = result.get("last_analysis_date", "")
        result["vt_malicious_score"] = result.get("malicious", "")

        result["ioc"] = ioc
        result["ioc_type"] = ioc_type
        result["twitter_link"] = tweet_link

        # ---- AlienVault OTX (IP / URL / HASH) ----
        logging.info(f"AlienVault lookup | IOC={ioc}")
        alien = alienvault_lookup(ioc)
        if alien:
            result.update(alien)
            logging.info(f"AlienVault enriched | IOC={ioc}")
        else:
            logging.warning(f"AlienVault no data | IOC={ioc}")

        # ---- MalwareBazaar (HASH Only) ----
        if ioc_type == "hash":
            logging.info(f"MalwareBazaar lookup | IOC={ioc}")

            mb = malwarebazaar_lookup(ioc)
            if mb:
                result.update(mb)
                logging.info(f"MalwareBazaar enriched | IOC={ioc}")
            else:
                logging.warning(f"MalwareBazaar no data | IOC={ioc}")

        # ---- AbuseIPDB (IP Only) ----
        if ioc_type == "ip":
            logging.info(f"AbuseIPDB lookup | IOC={ioc}")

            abuse = abuseipdb_lookup(ioc)
            if abuse:
                result.update(abuse)
                logging.info(f"AbuseIPDB enriched | IOC={ioc}")
            else:
                logging.warning(f"AbuseIPDB no data | IOC={ioc}")
 
        # ---- SAVE RESULT ----
        save_tip_result(result)
        seen_results.add(ioc)

        # ---- SEND TO SIEM (ONLY NEW IOC) ----
        send_tip_result_to_siem(result)

        new_count += 1

        logging.info(
            f"Enriched IOC={ioc}"
        )

        time.sleep(VT_SLEEP)

    logging.info(f"[✓] FINISH - Cheking to Threat Intelligence Tools | new={new_count}")


# if __name__ == "__main__":
#     tip_main()
