def parse_market_tier(specifications_dict):
    specs_general = specifications_dict.get("مشخصات کلی", {})
    raw_tier = specs_general.get("دسته ‌بندی", "")

    if not raw_tier:
        return ""

    # ۱. تبدیل به رشته، حذف تمام نیم‌فاصله‌ها و جایگزینی خطوط جدید (\n) با فاصله معمولی
    cleaned_tier = (
        str(raw_tier).replace("\u200c", "").replace("\n", " ").strip()
    )

    # ۲. بررسی شروط بر اساس کلمات کاملاً پاک‌سازی شده و بدون نیم‌فاصله
    # اولویت اول: پرچم‌دار
    if "پرچمدار" in cleaned_tier:
        return "Flagship"

    # اولویت دوم: میان‌رده (حتی اگر در کنار گیمینگ یا اقتصادی آمده باشد)
    elif "میانرده" in cleaned_tier:
        return "Mid-Range"

    # اولویت سوم: اقتصادی
    elif "اقتصادی" in cleaned_tier:
        return "Entry-Level"

    return ""