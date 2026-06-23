import re


def parse_screen_features(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    screen_specs = specifications_dict.get("صفحه نمایش", {})
    raw_other_features = screen_specs.get("سایر قابلیت‌ها", "")
    raw_protection = screen_specs.get("نوع محافظ صفحه نمایش گوشی", "")

    # -------------------------------------------------------------------------
    # PART 1: HDR STATUS MAPPING (Remains precise based on industry standards)
    # -------------------------------------------------------------------------
    hdr_status = "Unknown"
    if raw_other_features:
        hdr_text = fa_to_en(raw_other_features).lower()

        if "dolby vision" in hdr_text:
            hdr_status = "Dolby Vision"
        elif any(k in hdr_text for k in ["hdr10+", "hdr10 پلاس", "+hdr10"]):
            hdr_status = "HDR10+"
        elif "hdr10" in hdr_text or "hdr 10" in hdr_text:
            hdr_status = "HDR10"
        elif "hdr vivid" in hdr_text:
            hdr_status = "HDR Vivid"
        elif "hdr" in hdr_text:
            hdr_status = "HDR"

    # -------------------------------------------------------------------------
    # PART 2: COMPREHENSIVE DISPLAY PROTECTION TIER MAPPING
    # -------------------------------------------------------------------------
    protection_tier = "Unknown"

    if raw_protection:
        prot_text = fa_to_en(raw_protection).lower().strip()

        # --- TIER 1: ULTRA PREMIUM ---
        # Top-shelf modern flagship protection (Victus series, Armor, Ceramic Shield, Kunlun)
        ultra_premium_keywords = [
            "victus",
            "armor",
            "ceramic shield",
            "kunlun",
            "nanocrystal",
            "crystal shield",
            "xensation alpha",
        ]

        # --- TIER 2: PREMIUM BRANDED ---
        # High-end legacy or mid-range modern branded glass (GG 5, GG 6, GG 7i, Dragontrail Pro)
        premium_branded_keywords = [
            "gorilla glass 5",
            "gorilla glass 6",
            "gorilla glass 7i",
            "dragontrail pro",
            "dragontrail star",
            "xensation up",
        ]

        # --- TIER 3: STANDARD BRANDED ---
        # Entry-to-mid branded glass (GG 1-4, generic Dragontrail, NEG, Ion-Strengthened)
        standard_branded_keywords = [
            "gorilla glass 3",
            "gorilla glass 3+",
            "gorilla glass 4",
            "gorilla glass 2",
            "corning gorilla glass",
            "dragontrail",
            "neg glass",
            "nippon electric",
            "ion-strengthened",
            "scratch-resistant glass",
            "asahi",
        ]

        # --- TIER 4: NONE / GENERIC ---
        # Explicitly unprotected or generic unbranded claims
        none_generic_keywords = [
            "بدون محافظ",
            "scratch-proof glass",
            "no protection",
            "none",
            "unprotected",
        ]

        # 1. Primary contextual check using specific keyword sets
        if any(k in prot_text for k in ultra_premium_keywords):
            protection_tier = "ultra_premium"
        elif any(k in prot_text for k in premium_branded_keywords):
            protection_tier = "premium_branded"
        elif any(k in prot_text for k in standard_branded_keywords):
            protection_tier = "standard_branded"
        elif any(k in prot_text for k in none_generic_keywords):
            protection_tier = "none_generic"

        # 2. Broad Fallback Rules (For edge cases or partial text values)
        if protection_tier == "Unknown":
            if "سرامیک" in prot_text or "ceramic" in prot_text:
                # Most modern ceramic glass fits ultra or premium tier
                protection_tier = (
                    "ultra_premium"
                    if "shield" in prot_text or "kunlun" in prot_text
                    else "premium_branded"
                )
            elif "gorilla" in prot_text:
                # If it's Gorilla Glass but missed specific numbers above (e.g. "Corning Gorilla Glass")
                protection_tier = "standard_branded"
            elif (
                "بدون" in prot_text
                or "نامشخص" in prot_text
                or "no " in prot_text
            ):
                protection_tier = "none_generic"

    return hdr_status, protection_tier