import re


def parse_system_and_camera_specs(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Extract relevant categories safely
    specs_camera = specifications_dict.get("دوربین", {})
    specs_general = specifications_dict.get("مشخصات کلی", {})
    specs_connectivity = specifications_dict.get("ارتباطات", {})
    specs_software = specifications_dict.get("امکانات نرم افزاری", {})

    # ---------------------------------------------
    # 1. REAR CAMERA COUNT
    # ---------------------------------------------
    raw_rear_count = specs_camera.get("تعداد دوربین‌های پشت گوشی", "")
    rear_camera_count = ""
    if raw_rear_count:
        cleaned_rear = fa_to_en(raw_rear_count)
        match = re.search(r"(\d+)", cleaned_rear)
        if match:
            rear_camera_count = int(match.group(1))

    # ---------------------------------------------
    # 2. NANO SIM COUNT
    # ---------------------------------------------
    raw_sim_count = specs_general.get("تعداد سیم کارت", "")
    nano_sim = ""
    if raw_sim_count:
        if "دو" in raw_sim_count:
            nano_sim = 2
        elif "یک" in raw_sim_count:
            nano_sim = 1

    # ---------------------------------------------
    # 3. ESIM SUPPORT (Keyword check)
    # ---------------------------------------------
    raw_sim_type = specs_general.get("نوع سیم کارت", "")
    has_esim_support = False
    if raw_sim_type:
        # Search directly for "esim" case-insensitively
        if "esim" in str(raw_sim_type).lower():
            has_esim_support = True

    # ---------------------------------------------
    # 4. MAX NETWORK GENERATION
    # ---------------------------------------------
    raw_network = specs_connectivity.get("شبکه‌های مخابراتی", "")
    max_network_generation = ""
    if raw_network:
        cleaned_net = fa_to_en(raw_network)
        if "5" in cleaned_net:
            max_network_generation = "5G"
        else:
            max_network_generation = "4G"

    # ---------------------------------------------
    # 5. OPERATING SYSTEM VERSION
    # ---------------------------------------------
    raw_os_version = specs_software.get("نسخه سیستم عامل", "")
    operating_system_version = ""
    if raw_os_version:
        cleaned_os_v = fa_to_en(raw_os_version)
        match = re.search(r"(\d+\.\d+|\d+)", cleaned_os_v)
        if match:
            operating_system_version = float(match.group(1))
            # Convert to int if it's a whole number (e.g., 16.0 -> 16)
            if operating_system_version.is_integer():
                operating_system_version = int(operating_system_version)

    # ---------------------------------------------
    # 6. FRONT CAMERA MEGAPIXELS
    # ---------------------------------------------
    raw_front = specs_camera.get("رزولوشن دوربین سلفی", "")
    front_camera_megapixels = ""
    if raw_front:
        cleaned_front = fa_to_en(raw_front)
        match = re.search(r"(\d+\.\d+|\d+)", cleaned_front)
        if match:
            front_camera_megapixels = float(match.group(1))
            if front_camera_megapixels.is_integer():
                front_camera_megapixels = int(front_camera_megapixels)

    # ---------------------------------------------
    # 7. OPERATING SYSTEM (With Fallback)
    # ---------------------------------------------
    primary_os = specs_software.get("سیستم عامل", "")
    fallback_os = specs_general.get("نوع گوشی موبایل", "")

    # Combine text pools to safely inspect
    os_text_pool = f" {primary_os} {fallback_os} ".lower()
    operating_system = ""

    if "android" in os_text_pool or "اندروید" in os_text_pool:
        operating_system = "Android"
    elif "ios" in os_text_pool:
        operating_system = "iOS"

    return (
        rear_camera_count,
        nano_sim,
        has_esim_support,
        max_network_generation,
        operating_system_version,
        front_camera_megapixels,
        operating_system,
    )