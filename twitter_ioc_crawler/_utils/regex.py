import re

COMPANY_REGEX = re.compile(r'^"([^"]+)"', re.M)
CERT_REGEX = re.compile(r'\(([^)]*cert[^)]*)\)', re.I)

FILENAME_REGEX = re.compile(r'"([^"]+\.(exe|dll|pif|msi|zip))"', re.I)
FILENAME_PLAIN_REGEX = re.compile(r'\b([\w\-]+\.(exe|dll|pif|msi|zip))\b', re.I)

HASH_REGEX = re.compile(r'\b[a-fA-F0-9]{32,64}\b')
IP_REGEX = re.compile(r'\b\d{1,3}(?:\[\.\]|\.)\d{1,3}(?:\[\.\]|\.)\d{1,3}(?:\[\.\]|\.)\d{1,3}\b')
URL_REGEX = re.compile(r'https?://[^\s]+')

SEEN_REGEX = re.compile(r'seen from\s+([A-Za-z ]+)', re.I)