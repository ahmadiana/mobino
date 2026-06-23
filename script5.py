import re


def parse_refresh_rate_and_brightness(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Extract all potential raw fields safely
    specs_display = specifications_dict.get("صفحه نمایش", {})
    specs_general = specifications_dict.get("مشخصات کلی", {})

    primary_refresh = specs_display.get("نرخ به‌روزرسانی تصویر", "")
    primary_brightness = specs_display.get("روشنایی صفحه نمایش", "")

    backup_1 = specs_display.get("سایر قابلیت‌ها", "")
    backup_2 = specs_general.get("ویژگی‌های کلیدی", "")

    # Combine all text for fallback searches if primary fields fail
    fallback_pool = f" {backup_1} {backup_2} "

    # ---------------------------------------------
    # 1. PROCESS REFRESH RATE
    # ---------------------------------------------
    allowed_rates = ["185", "165", "144", "120", "90", "60"]
    display_refresh_rate_hz = ""

    # Check primary field first
    if primary_refresh:
        cleaned_primary = fa_to_en(primary_refresh)
        for rate in allowed_rates:
            if rate in cleaned_primary:
                display_refresh_rate_hz = int(rate)
                break

    # Fallback if primary didn't yield an allowed rate
    if not display_refresh_rate_hz:
        cleaned_fallbacks = fa_to_en(fallback_pool)
        # Use regex boundary to avoid matching 1200 nits as 120 Hz
        for rate in allowed_rates:
            if re.search(r"\b" + rate + r"\b", cleaned_fallbacks):
                display_refresh_rate_hz = int(rate)
                break

    # ---------------------------------------------
    # 2. PROCESS BRIGHTNESS NITS
    # ---------------------------------------------
    brightness_nits = ""

    # Check primary field first
    if primary_brightness:
        cleaned_bright = fa_to_en(primary_brightness)
        bright_match = re.search(r"(\d+)", cleaned_bright)
        if bright_match:
            val = int(bright_match.group(1))
            if 400 <= val <= 7000:
                brightness_nits = val

    # Fallback logic looking inside the range of 400 to 7000
    if not brightness_nits:
        cleaned_fallbacks = fa_to_en(fallback_pool)
        # Find all numbers to inspect them
        all_numbers = re.findall(r"\b\d+\b", cleaned_fallbacks)
        for num_str in all_numbers:
            val = int(num_str)
            # Filter out standard refresh rates so they don't corrupt brightness
            if val in [60, 90, 120, 144, 165, 185]:
                continue
            if 400 <= val <= 7000:
                brightness_nits = val
                break  # Take the first matching valid brightness value

    return display_refresh_rate_hz, brightness_nits