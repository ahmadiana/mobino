import re


def parse_ram_and_storage(specifications_dict):
    def fa_to_en(text):
        return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    specs_memory = specifications_dict.get("حافظه", {})

    # 1. Parse RAM
    raw_ram = specs_memory.get("مقدار RAM", "")
    ram_gb = ""
    if raw_ram:
        cleaned_ram = fa_to_en(str(raw_ram))
        ram_match = re.search(r"(\d+)", cleaned_ram)
        if ram_match:
            ram_gb = int(ram_match.group(1))

    # 2. Parse Storage
    raw_storage = specs_memory.get("حافظه داخلی", "")
    storage_gb = ""
    if raw_storage:
        cleaned_storage = fa_to_en(str(raw_storage))
        storage_match = re.search(r"(\d+)", cleaned_storage)
        if storage_match:
            value = int(storage_match.group(1))
            # Unit conversions
            if "ترابایت" in cleaned_storage or "TB" in cleaned_storage:
                storage_gb = value * 1024
            elif "مگابایت" in cleaned_storage or "MB" in cleaned_storage:
                storage_gb = round(value / 1024, 2)
            else:
                storage_gb = value

    return ram_gb, storage_gb