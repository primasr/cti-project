import re

# === HASH (SHA256 ONLY) ===
HASH_SHA256_REGEX = re.compile(
    r'\b[a-fA-F0-9]{64}\b'
)

# === IP (Support normal + defanged like 1[.]1[.]1[.]1) ===
IP_REGEX = re.compile(
    r'\b'
    r'(?:\d{1,3})(?:\[\.\]|\.)'
    r'(?:\d{1,3})(?:\[\.\]|\.)'
    r'(?:\d{1,3})(?:\[\.\]|\.)'
    r'(?:\d{1,3})'
    r'\b'
)

# === URL (http + https, stops at whitespace or closing bracket) ===
URL_REGEX = re.compile(
    r'\bhttps?://[^\s<>"\'\]]+',
    re.IGNORECASE
)