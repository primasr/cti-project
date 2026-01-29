import re

HASH_REGEX = re.compile(r'^[a-fA-F0-9]{32,64}$')
IP_REGEX = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
URL_REGEX = re.compile(r'https?://[^\s]+')

def get_ioc_type(ioc: str) -> str:
    if HASH_REGEX.match(ioc):
        return "hash"
    if IP_REGEX.match(ioc):
        return "ip"
    if URL_REGEX.fullmatch(ioc):
        return "url"
    return "other"
