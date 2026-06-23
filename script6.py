import re


def parse_weight_and_thickness(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    specs_general = specifications_dict.get("مشخصات کلی", {})

    # 1. Parse Weight
    raw_weight = specs_general.get("وزن", "")
    weight_grams = ""
    if raw_weight:
        cleaned_weight = fa_to_en(raw_weight)
        weight_match = re.search(r"(\d+\.?\d*)", cleaned_weight)
        if weight_match:
            weight_grams = float(weight_match.group(1))
            # Convert clean whole numbers to int format
            if weight_grams.is_integer():
                weight_grams = int(weight_grams)

    # 2. Parse Thickness (Find the smallest number)
    raw_dimensions = specs_general.get("ابعاد", "")
    thickness_mm = ""
    if raw_dimensions:
        cleaned_dims = fa_to_en(raw_dimensions)
        # Extract all floating point and integer numbers found in text
        all_nums = re.findall(r"(\d+\.\d+|\d+)", cleaned_dims)
        if all_nums:
            float_nums = [float(n) for n in all_nums if float(n) > 0]
            if float_nums:
                # The minimum value corresponds to the depth/thickness
                smallest_val = min(float_nums)
                thickness_mm = smallest_val
                if thickness_mm.is_integer():
                    thickness_mm = int(thickness_mm)

    return weight_grams, thickness_mm