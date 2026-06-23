"""
SCRIPT 1: Launch MSRP price lookup via Gemini.

Takes a list of phone names (in order) and asks Gemini for the estimated/
official launch MSRP (USD, base storage variant) for each one, in the same
order. Returns a list of ints, one per input phone name, same length and
order as the input.
"""
import json
import re

from gemini_client import call_gemini_json

SYSTEM_PROMPT = """You are a smartphone launch pricing database.

Your task is to determine the launch MSRP price in USD for the base storage variant of each smartphone.

Rules:

- Base variant = lowest storage model officially sold at launch.
- If the phone name you receive happens to mention a specific storage or RAM
  capacity (e.g. "256GB", "12/256", "256 گیگابایت"), IGNORE that capacity
  entirely and still price the lowest-storage base variant of that model,
  not the variant mentioned in the name.
- Return prices in USD.
- Return integers only.
- No currency symbols.
- No commas.
- No explanations.
- No phone names.
- No markdown.
- No text.
- Preserve the exact order of the input.
- Return exactly one value per phone.
- Never return null.
- Never return N/A.
- Never return unknown.
- If an official MSRP cannot be determined, estimate a realistic launch MSRP based on market positioning and specifications.
- Always return a value.

Output format:

{
  "prices":[
    799,
    999,
    649
  ]
}

Return valid JSON only."""


def _extract_json_object(raw_text: str) -> dict:
    """Gemini is asked for JSON-only, but we defensively strip code fences /
    stray text just in case, then parse."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned.strip(), flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
    return json.loads(cleaned)


def get_launch_msrp_prices(phone_names: list[str]) -> list[int]:
    """
    phone_names: ordered list of phone display names (e.g. product_name_en
    or the scraped title), one per phone being analyzed.

    Returns: ordered list of ints (USD launch MSRP), same length/order as input.
    On any failure, falls back to 0 for every phone, never raises, so a
    Gemini outage doesn't take down the whole analysis pipeline.
    """
    print(f"\n[gemini_msrp] ===> get_launch_msrp_prices() called for {len(phone_names)} phone(s): {phone_names}")

    if not phone_names:
        return []

    user_content = json.dumps(phone_names, ensure_ascii=False)

    try:
        raw_text = call_gemini_json(SYSTEM_PROMPT, user_content, label="msrp")
        parsed = _extract_json_object(raw_text)
        prices = parsed.get("prices", [])

        if not isinstance(prices, list):
            raise ValueError(f"'prices' field was not a list: {prices!r}")

        if len(prices) != len(phone_names):
            print(f"[gemini_msrp] ⚠️ Gemini returned {len(prices)} price(s) but {len(phone_names)} phone(s) were sent. Padding/truncating to match.")
            if len(prices) < len(phone_names):
                prices = prices + [0] * (len(phone_names) - len(prices))
            else:
                prices = prices[:len(phone_names)]

        # Coerce every entry to int defensively (Gemini should already return ints).
        clean_prices = []
        for p in prices:
            try:
                clean_prices.append(int(round(float(p))))
            except (TypeError, ValueError):
                clean_prices.append(0)

        print(f"[gemini_msrp] <=== returning {len(clean_prices)} price(s): {list(zip(phone_names, clean_prices))}")
        return clean_prices

    except Exception as err:
        print(f"[gemini_msrp] ❌ failed to get MSRP prices, defaulting all to 0: {err}")
        return [0] * len(phone_names)
