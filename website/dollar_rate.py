"""
Fetches the live USD -> Toman exchange rate from tgju.org once, and caches
it in memory. Intended to be called exactly once at FastAPI startup
(see app.py's startup event), not on every request.
"""
import re
import requests

from config import DOLLAR_RATE_URL

# Module-level cache. None until fetch_and_cache_dollar_rate() succeeds once.
_cached_dollar_rate = None


def fetch_dollar_rate_from_tgju() -> float:
    """
    Fetches https://www.tgju.org/profile/price_dollar_rl and extracts the
    value inside:
        <span data-col="info.last_trade.PDrCotVal">1,596,000</span>
    Strips thousands-separator commas, converts to float, then divides by
    10000 (per the training data convention, e.g. 1,596,000 -> 159.6).
    """
    print(f"[dollar_rate] fetching live USD/Toman rate from {DOLLAR_RATE_URL} ...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(DOLLAR_RATE_URL, headers=headers, timeout=15)
    response.raise_for_status()

    match = re.search(
        r'data-col="info\.last_trade\.PDrCotVal"[^>]*>([\d,]+)<',
        response.text
    )
    if not match:
        raise ValueError("Could not find the PDrCotVal span in the tgju.org page (page layout may have changed)")

    raw_value_str = match.group(1).replace(",", "")
    raw_value = float(raw_value_str)
    dollar_rate = round(raw_value / 10000, 2)

    print(f"[dollar_rate] ✅ fetched raw value '{match.group(1)}' -> DollarRate = {dollar_rate}")
    return dollar_rate


def fetch_and_cache_dollar_rate() -> float:
    """
    Call this once at server startup. On success, caches the value in memory
    for get_cached_dollar_rate() to use on every subsequent request without
    re-scraping. On failure, logs the error and leaves the cache as a safe
    fallback value rather than crashing server startup.
    """
    global _cached_dollar_rate
    try:
        _cached_dollar_rate = fetch_dollar_rate_from_tgju()
    except Exception as err:
        print(f"[dollar_rate] ❌ failed to fetch live dollar rate at startup: {err}")
        print("[dollar_rate] falling back to a safe default of 0 -- THIS WILL AFFECT PRICE PREDICTIONS.")
        print("[dollar_rate] consider checking your network/proxy settings or the tgju.org page structure.")
        _cached_dollar_rate = 0.0
    return _cached_dollar_rate


def get_cached_dollar_rate() -> float:
    """
    Returns the cached dollar rate. If fetch_and_cache_dollar_rate() was
    never called (e.g. during local testing), fetches it on the spot once
    as a safety net, then caches it.
    """
    global _cached_dollar_rate
    if _cached_dollar_rate is None:
        print("[dollar_rate] cache empty (startup fetch never ran?), fetching now as a fallback...")
        fetch_and_cache_dollar_rate()
    return _cached_dollar_rate
