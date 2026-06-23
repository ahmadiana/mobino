import re


def parse_display_specs(specifications_dict):
    def fa_to_en(text):
        return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    specs_display = specifications_dict.get("صفحه نمایش", {})

    # 1. Parse PPI (Density)
    raw_ppi = specs_display.get("تراکم پیکسلی", "")
    display_ppi = ""
    if raw_ppi:
        cleaned_ppi = fa_to_en(str(raw_ppi))
        ppi_match = re.search(r"(\d+)", cleaned_ppi)
        if ppi_match:
            display_ppi = int(ppi_match.group(1))

    # 2. Parse Display Size
    raw_size = specs_display.get("اندازه", "")
    display_size_inches = ""
    if raw_size:
        cleaned_size = fa_to_en(str(raw_size))
        # Match decimals or integers safely
        size_match = re.search(r"(\d+\.?\d*)", cleaned_size)
        if size_match:
            display_size_inches = float(size_match.group(1))

    return display_ppi, display_size_inches