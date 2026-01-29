from .regex import *
from .text_utils import normalize

def parse_tweet(text, images):
    text = normalize(text)

    data = {
        "company": "",
        "certificate": "",
        "filename": "",
        "iocs": [],
        "country": "",
        "ip": "",
        "url": "",
        "images": images
    }

    if m := COMPANY_REGEX.search(text):
        data["company"] = m.group(1)

    if m := CERT_REGEX.search(text):
        data["certificate"] = m.group(1)

    if m := (FILENAME_REGEX.search(text) or FILENAME_PLAIN_REGEX.search(text)):
        data["filename"] = m.group(1)

    hashes = HASH_REGEX.findall(text)
    data["iocs"] = list(set(hashes))

    if m := SEEN_REGEX.search(text):
        data["country"] = m.group(1).strip()

    if m := IP_REGEX.search(text):
        data["ip"] = normalize(m.group(0))

    if m := URL_REGEX.search(text):
        data["url"] = normalize(m.group(0))

    return data
