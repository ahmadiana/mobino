import re


def parse_battery_and_charging_specs(specifications_dict):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    # Safely extract sub-dictionary category
    specs_other = specifications_dict.get("سایر مشخصات", {})

    primary_capacity = specs_other.get("ظرفیت باتری", "")
    primary_power = specs_other.get("توان شارژ", "")
    primary_capabilities = specs_other.get("قابلیت‌های شارژ", "")
    backup_battery_specs = specs_other.get("مشخصات باتری", "")

    # ---------------------------------------------
    # 1. PROCESS WIRELESS CHARGING
    # ---------------------------------------------
    has_wireless_charging = False
    wireless_keywords = ["بی‌سیم", "بی سیم", "وایرلس", "wireless"]

    # Check primary field first
    if primary_capabilities:
        if any(kw in str(primary_capabilities) for kw in wireless_keywords):
            has_wireless_charging = True

    # Check backup field if primary didn't confirm support
    if not has_wireless_charging and backup_battery_specs:
        if any(kw in str(backup_battery_specs) for kw in wireless_keywords):
            has_wireless_charging = True

    # ---------------------------------------------
    # 2. PROCESS BATTERY CAPACITY
    # ---------------------------------------------
    battery_capacity_mah = ""

    if primary_capacity:
        cleaned_capacity = fa_to_en(primary_capacity)
        match = re.search(r"(\d+)", cleaned_capacity)
        if match:
            battery_capacity_mah = int(match.group(1))

    # Backup logic: Look for values greater than 4000 mAh
    if not battery_capacity_mah and backup_battery_specs:
        cleaned_backup = fa_to_en(backup_battery_specs)
        all_nums = re.findall(r"\b\d+\b", cleaned_backup)
        for num_str in all_nums:
            val = int(num_str)
            if val > 4000:
                battery_capacity_mah = val
                break

    # ---------------------------------------------
    # 3. PROCESS WIRED CHARGING POWER
    # ---------------------------------------------
    wired_charging_power = ""

    if primary_power:
        cleaned_power = fa_to_en(primary_power)
        match = re.search(r"(\d+\.\d+|\d+)", cleaned_power)
        if match:
            wired_charging_power = float(match.group(1))
            if wired_charging_power.is_integer():
                wired_charging_power = int(wired_charging_power)

    # Backup logic: Segment-slice to isolate true high wired-wattage values
    if not wired_charging_power and backup_battery_specs:
        # Split text into independent feature segments to clean context
        segments = re.split(r"[,/;\-\n\"]", backup_battery_specs)
        for segment in segments:
            segment_en = fa_to_en(segment).lower()
            # Look for explicit wattage tokens while filtering out wireless/reverse indicators
            if "وات" in segment or "w" in segment_en:
                exclude_keywords = [
                    "بی‌سیم",
                    "بی سیم",
                    "وایرلس",
                    "معکوس",
                    "wireless",
                    "reverse",
                ]
                if not any(
                    kw in segment_en or kw in segment for kw in exclude_keywords
                ):
                    match = re.search(r"(\d+\.\d+|\d+)", segment_en)
                    if match:
                        val = float(match.group(1))
                        # Only commit high wattage values safely avoiding percentages (e.g. 15W+)
                        if val >= 15:
                            wired_charging_power = (
                                int(val) if val.is_integer() else val
                            )
                            break

    return battery_capacity_mah, wired_charging_power, has_wireless_charging