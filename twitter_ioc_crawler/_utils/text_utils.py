from .regex import *

def normalize(text: str) -> str:
    return text.replace("[.]", ".")

def has_ioc(text: str) -> bool:
    return bool(
        HASH_SHA256_REGEX.search(text) or
        IP_REGEX.search(text) or
        URL_REGEX.search(text)
    )

def get_ioc_type(ioc: str) -> str:
    if HASH_SHA256_REGEX.fullmatch(ioc):
        return "hash"
    if IP_REGEX.fullmatch(ioc):
        return "ip"
    if URL_REGEX.fullmatch(ioc):
        return "url"
    return "unknown"
