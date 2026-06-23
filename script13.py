import re


def parse_protection_specs(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    ip_whitelist = [
        "IP68/IP69",
        "IP68/IP69K",
        "IP68",
        "IP58/IP59",
        "IP65",
        "IP69",
        "IP48/IP49",
        "IP48",
        "IPX8",
        "Unknown",
        "IP64",
        "IP54",
        "IP65/IP68",
        "IP66/IP68/IP69/IP69K",
        "IP66",
        "IPX4",
        "IP53",
        "IP67",
        "Water-repellent",
        "Splash Resistant",
        "Waterproof",
        "IP66/IP68/IP69K",
    ]

    # Extract target fields safely
    general_specs = specifications_dict.get("مشخصات کلی", {})

    raw_resistance = general_specs.get("قابلیت‌های مقاومتی", "")
    raw_keys = general_specs.get("ویژگی‌های کلیدی", "")
    raw_body = general_specs.get("توضیحات بدنه", "")

    # Normalize texts to English numerals
    clean_resistance = fa_to_en(raw_resistance)
    clean_keys = fa_to_en(raw_keys)
    clean_body = fa_to_en(raw_body)

    # ---------------------------------------------
    # 1. PROCESS IP RATING
    # ---------------------------------------------
    ip_rating = "Unknown"

    # Search for standard IP tokens (e.g., IP68, IP68/IP69K, IPX4)
    ip_pattern = r"\bIP[0-9Xx](?:/[0-9Xx])?[0-9Kk]*\b"

    # Priority 1: Check key features
    found_ratings = re.findall(ip_pattern, clean_keys, flags=re.IGNORECASE)

    # Priority 2: Fallback to physical body description text
    if not found_ratings:
        found_ratings = re.findall(ip_pattern, clean_body, flags=re.IGNORECASE)

    if found_ratings:
        # Take the most comprehensive match extracted
        candidate_ip = found_ratings[0].upper()
        # Ensure exact string alignment with the target dataset options list
        match = next(
            (i for i in ip_whitelist if i.lower() == candidate_ip.lower()),
            None,
        )
        if match:
            ip_rating = match

    # Explicit textual fallbacks if no alphanumeric token was observed
    if ip_rating == "Unknown":
        combined_text = f"{clean_keys} {clean_body}".lower()
        if "splash resistant" in combined_text or "پاشش آب" in combined_text:
            ip_rating = "Splash Resistant"
        elif "water-repellent" in combined_text:
            ip_rating = "Water-repellent"
        elif "waterproof" in combined_text or "ضد آب" in combined_text:
            ip_rating = "Waterproof"

    # ---------------------------------------------
    # 2. PROCESS IS_DUSTPROOF & IS_WATERPROOF
    # ---------------------------------------------
    is_dustproof = False
    is_waterproof = False

    # Check primary resistance field first if present
    if clean_resistance:
        if any(
            kw in clean_resistance for kw in ["گرد و غبار", "گرد و خاک", "خاک"]
        ):
            is_dustproof = True
        if any(kw in clean_resistance for kw in ["آب", "پاشش"]):
            is_waterproof = True
    else:
        # Fallback 1: Extract from body descriptions text explicitly
        if clean_body:
            if any(kw in clean_body for kw in ["گرد و غبار", "گرد و خاک"]):
                is_dustproof = True
            if any(kw in clean_body for kw in ["مقاوم در برابر آب", "ضد آب"]):
                is_waterproof = True

        # Fallback 2: Deduce logically using numerical parameters from the solved IP rating
        if (not is_dustproof or not is_waterproof) and ip_rating != "Unknown":
            # Direct text indicators
            if ip_rating in ["Waterproof", "Splash Resistant", "Water-repellent"]:
                is_waterproof = True

            # Code processing (e.g., IP68 -> Dust digit 6, Water digit 8)
            digits = re.findall(r"\d", ip_rating)
            if "IPX" in ip_rating:
                is_waterproof = True  # e.g., IPX4, IPX8 are verified for moisture
            elif len(digits) >= 2:
                dust_digit = int(digits[0])
                water_digit = int(digits[1])

                if dust_digit >= 5:
                    is_dustproof = True
                if water_digit >= 3:
                    is_waterproof = True

    # Format return strings to match your data standard requirement
    return (
        "TRUE" if is_dustproof else "FALSE",
        "TRUE" if is_waterproof else "FALSE",
        ip_rating,
    )