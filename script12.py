import re


def parse_storage_and_display(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Whitelists
    storage_whitelist = [
        "UFS 4.1",
        "UFS",
        "UFS 4.0",
        "UFS 4.x",
        "Unknown",
        "UFS 3.1",
        "NVMe",
        "UFS 2.2",
        "uMCP",
        "UFS 3.x",
        "SFS 1.0",
        "UFS 2.x",
        "UFS 3.0",
        "UFS 2.1",
        "eMMC 5.1",
        "eMMC",
        "UFS 2.0",
    ]

    display_whitelist = [
        "LTPO AMOLED",
        "LTPO OLED",
        "AMOLED",
        "LTPO 4.1 AMOLED",
        "OLED",
        "Foldable LTPO OLED",
        "Dynamic LTPO AMOLED 2X",
        "Foldable LTPO2 AMOLED",
        "Foldable LTPO P-OLED",
        "Dual-layer LTPO OLED",
        "Foldable LTPO AMOLED",
        "LTPO Super Retina XDR OLED",
        "P-OLED",
        "Dynamic AMOLED 2X",
        "Foldable Dynamic LTPO AMOLED 2X",
        "Tri-foldable Dynamic LTPO AMOLED 2X",
        "LTPO4 AMOLED",
        "LTPO AMOLED 2X",
        "Foldable LTPO2 OLED",
        "LTPO3 Fluid AMOLED",
        "LTPO2 Fluid AMOLED",
        "Fluid AMOLED",
        "Swift AMOLED",
        "Foldable LTPO OLED+",
        "LTPO3 OLED",
        "Foldable LTPO3 Flexi-fluid AMOLED",
        "LTPO P-OLED",
        "Super Retina XDR OLED",
        "Super AMOLED+",
        "LTPO Fluid2 AMOLED",
        "Foldable Dynamic AMOLED 2X",
        "Super AMOLED",
        "Foldable OLED",
        "Tri-foldable LTPO OLED",
        "IPS LCD",
        "Super AMOLED Plus",
        "TFT LCD",
        "Super Retina OLED",
        "PLS LCD",
        "Retina IPS LCD",
        "Liquid Retina IPS LCD",
        "LCD",
    ]

    # Extract raw data fields
    storage_specs = specifications_dict.get("حافظه", {})
    display_specs = specifications_dict.get("صفحه نمایش", {})

    raw_storage = fa_to_en(storage_specs.get("تکنولوژی حافظه", "")).strip()
    raw_display = (
        fa_to_en(display_specs.get("فناوری صفحه‌ نمایش", ""))
        .strip()
        .replace("  ", " ")
    )

    # ---------------------------------------------
    # 1. PROCESS STORAGE TYPE
    # ---------------------------------------------
    storage_type = "Unknown"

    if raw_storage:
        # Normalize structural variations (e.g., 'UFS 4' -> 'UFS 4.0')
        if raw_storage.lower() == "ufs 4":
            raw_storage = "UFS 4.0"

        # Direct exact/case-insensitive matching
        match = next(
            (i for i in storage_whitelist if i.lower() == raw_storage.lower()),
            None,
        )
        if match:
            storage_type = match

    # ---------------------------------------------
    # 2. PROCESS DISPLAY TECH
    # ---------------------------------------------
    display_tech = "Unknown"

    if raw_display:
        # Common layout normalization rules to match whitelist
        norm_display = raw_display.lower()
        if norm_display == "tft":
            norm_display = "tft lcd"
        elif norm_display == "ips" or norm_display == "ips lcd":
            norm_display = "ips lcd"
        elif norm_display == "pls":
            norm_display = "pls lcd"
        elif norm_display == "liquid retina":
            norm_display = "liquid retina ips lcd"
        elif norm_display == "super retina":
            norm_display = "super retina oled"

        match = next(
            (i for i in display_whitelist if i.lower() == norm_display), None
        )
        if match:
            display_tech = match

    return storage_type, display_tech