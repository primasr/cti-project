from datetime import datetime, timezone, timedelta

UTC_PLUS_7 = timezone(timedelta(hours=7))

def parse_twitter_time(dt: str):
    if not dt:
        return None
    utc = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    return utc.astimezone(UTC_PLUS_7)
