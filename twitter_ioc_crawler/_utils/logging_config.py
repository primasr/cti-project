import logging
from .config import LOG_FILE

def setup_logging():
    """
    Centralized logging configuration.
    Call ONCE at app startup.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
