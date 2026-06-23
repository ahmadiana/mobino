import re
import pandas as pd


def parse_chipset(specifications_dict, csv_file_path="nanoreview_chipsets.csv"):
    def fa_to_en(text):
        if not text:
            return ""
        return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

    def is_subsequence(candidate, target_text):
        """Checks if all characters of the candidate name exist within

        the target text in the same order (ignoring spaces/case).
        """
        cand_clean = str(candidate).lower().replace(" ", "")
        target_clean = str(target_text).lower().replace(" ", "")

        if not cand_clean:
            return False

        it = iter(target_clean)
        return all(char in it for char in cand_clean)

    # Safely extract sub-dictionary category
    specs_processor = specifications_dict.get("پردازنده", {})
    raw_chipset = specs_processor.get("تراشه", "")

    if not raw_chipset:
        return "", ""

    # ---------------------------------------------
    # 1. TEXT CLEANING & NORMALIZATION
    # ---------------------------------------------
    cleaned_text = fa_to_en(raw_chipset)

    # Step 1: Remove any variant of manufacturing process size notation e.g., (12 nm) or (7 nm+)
    cleaned_text = re.sub(
        r"\(\s*\d+\s*nm\s*\+?\s*\)", "", cleaned_text, flags=re.IGNORECASE
    )

    # Step 2: Delete text leading up to specific brand identifiers
    keywords = [
        "Snapdragon",
        "Unisoc",
        "Exynos",
        "Helio",
        "Kirin",
        "Tiger",
        "Dimensity",
        "Xring",
    ]
    earliest_idx = len(cleaned_text)
    kw_found = False

    for kw in keywords:
        idx = cleaned_text.lower().find(kw.lower())
        if idx != -1 and idx < earliest_idx:
            earliest_idx = idx
            kw_found = True

    if kw_found:
        cleaned_text = cleaned_text[earliest_idx:]

    # Step 3: Convert "+" symbols to " Plus"
    cleaned_text = cleaned_text.replace("+", " Plus")

    # Final pass: Strip trailing technical boilerplate and collapse spacing
    cleaned_text = re.sub(r"\bchipset\b", "", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    # ---------------------------------------------
    # 2. SMART CSV LOOKUP & RESOLUTION
    # ---------------------------------------------
    chipset = ""
    chipset_score = ""

    try:
        df = pd.read_csv(csv_file_path)

        candidates = []
        for _, row in df.iterrows():
            csv_name = str(row.get("chipset_name", ""))
            score = row.get("nanoreview_score", "")

            # Look for mutual subsequence or substring alignments
            if is_subsequence(csv_name, cleaned_text) or is_subsequence(
                cleaned_text, csv_name
            ):
                candidates.append({"name": csv_name, "score": score})

        if candidates:
            # Sort candidates by length descending to prioritize the "biggest/most specific" substring assignment
            candidates = sorted(
                candidates, key=lambda x: len(str(x["name"])), reverse=True
            )
            best_match = candidates[0]
            chipset = best_match["name"]
            chipset_score = best_match["score"]
        else:
            # Fallback if no CSV entry matches the pattern criteria
            chipset = cleaned_text

    except FileNotFoundError:
        # Graceful fallback if the reference dataset isn't loaded/accessible
        chipset = cleaned_text
        chipset_score = ""

    return chipset, chipset_score