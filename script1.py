import json
import re


def parse_release_year(specifications_dict):
    def fa_to_en(text):
        fa_digits = "۰۱۲۳۴۵۶۷۸۹"
        en_digits = "0123456789"
        return text.translate(str.maketrans(fa_digits, en_digits))

    # Safely navigate JSON structure
    specs_general = specifications_dict.get("مشخصات کلی", {})
    raw_date = specs_general.get("زمان معرفی", "")

    if not raw_date:
        return ""

    # Convert numerals and search for a 4-digit Gregorian year (e.g., 2021, 2025)
    cleaned_text = fa_to_en(str(raw_date))
    match = re.search(r"\b(20\d{2})\b", cleaned_text)

    return int(match.group(1)) if match else ""