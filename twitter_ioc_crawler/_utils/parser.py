from .regex import *
from .text_utils import normalize

def parse_tweet(text, images):
    text = normalize(text)

    data = {
        "iocs": []
    }

    iocs = set()
    iocs.update(HASH_SHA256_REGEX.findall(text))
    iocs.update(IP_REGEX.findall(text))
    iocs.update(URL_REGEX.findall(text))

    data["iocs"] = list(iocs)

    return data
