import re


def parse_camera_features(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Safely extract sub-dictionary category
    specs_camera = specifications_dict.get("دوربین", {})

    raw_main_mp = specs_camera.get("رزولوشن دوربین اصلی", "")
    raw_specs_main = specs_camera.get("مشخصات دوربین اصلی", "")

    # ---------------------------------------------
    # 1. REAR MAIN CAMERA MEGAPIXELS
    # ---------------------------------------------
    rear_main_camera_megapixels = ""
    if raw_main_mp:
        cleaned_mp = fa_to_en(raw_main_mp)
        match = re.search(r"(\d+\.\d+|\d+)", cleaned_mp)
        if match:
            val = float(match.group(1))
            rear_main_camera_megapixels = (
                int(val) if val.is_integer() else val
            )

    # ---------------------------------------------
    # 2. APERTURE (Aperture1)
    # ---------------------------------------------
    Aperture1 = ""
    if raw_specs_main:
        cleaned_specs = fa_to_en(raw_specs_main)
        # Attempt to target the explicit f/ number format first
        f_match = re.search(r"f/\s*(\d+\.\d+|\d+)", cleaned_specs, re.IGNORECASE)
        if f_match:
            val = float(f_match.group(1))
            Aperture1 = int(val) if val.is_integer() else val
        else:
            # Fallback: grab the very first valid float/int inside the string
            any_num_match = re.search(r"(\d+\.\d+|\d+)", cleaned_specs)
            if any_num_match:
                val = float(any_num_match.group(1))
                Aperture1 = int(val) if val.is_integer() else val

    # ---------------------------------------------
    # 3. OPTICAL IMAGE STABILIZATION (OIS)
    # ---------------------------------------------
    has_optical_image_stabilization = False
    if raw_specs_main:
        ois_keywords = ["لرزشگیر", "اپتیکال", "optical image stabilization", "ois"]
        if any(kw in str(raw_specs_main).lower() for kw in ois_keywords):
            has_optical_image_stabilization = True

    # ---------------------------------------------
    # 4. LENS TYPES (Main, 2nd, 3rd, 4th + Fallback)
    # ---------------------------------------------
    lens_fields = [
        specs_camera.get("نوع لنز دوربین اصلی", ""),
        specs_camera.get("نوع لنز دوربین دوم", ""),
        specs_camera.get("نوع لنز دوربین سوم", ""),
        specs_camera.get("نوع لنز دوربین چهارم", ""),
    ]

    # Consolidate standard fields and fallback string into lowercased search spaces
    primary_lens_pool = " ".join([str(f) for f in lens_fields if f]).lower()
    fallback_pool = str(raw_specs_main).lower()

    # Periscope Evaluation
    has_periscope = False
    if "پریسکوپ" in primary_lens_pool or "periscope" in primary_lens_pool:
        has_periscope = True
    elif "پریسکوپ" in fallback_pool or "periscope" in fallback_pool:
        has_periscope = True

    # Telephoto Evaluation
    has_telephoto = False
    if "تله فوتو" in primary_lens_pool or "telephoto" in primary_lens_pool:
        has_telephoto = True
    elif "تله فوتو" in fallback_pool or "telephoto" in fallback_pool:
        has_telephoto = True

    # Macro Evaluation
    has_macro = False
    if "ماکرو" in primary_lens_pool or "macro" in primary_lens_pool:
        has_macro = True
    elif "ماکرو" in fallback_pool or "macro" in fallback_pool:
        has_macro = True

    # Ultrawide Evaluation
    has_ultrawide = False
    if "فوق عریض" in primary_lens_pool or "ultrawide" in primary_lens_pool:
        has_ultrawide = True
    elif "فوق عریض" in fallback_pool or "ultrawide" in fallback_pool:
        has_ultrawide = True

    return (
        rear_main_camera_megapixels,
        Aperture1,
        has_optical_image_stabilization,
        has_periscope,
        has_telephoto,
        has_macro,
        has_ultrawide,
    )