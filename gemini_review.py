"""
SCRIPT 2: Persian AI review + comparison generation via Gemini.

Takes the raw, untouched data scraped directly from Digikala for each phone
(title, specifications, price, image, etc.) and asks Gemini to write a
structured Persian review/comparison following a fixed JSON schema.

Sends exactly ONE request to Gemini per call, covering all phones in the
list at once -- never one request per phone.
"""
import json
import re

from gemini_client import call_gemini_json

SYSTEM_PROMPT = """You are a professional smartphone reviewer.

Write in Persian.

Your audience is smartphone buyers and technology enthusiasts.

IMPORTANT:

Return VALID JSON ONLY.

Do not return markdown.
Do not return explanations.
Do not wrap JSON inside code blocks.

Rules:

- Be objective.
- Be technical.
- Use only provided specifications.
- Compare devices fairly.
- Keep bullet points short.
- Avoid marketing language.
- Mention meaningful strengths and weaknesses.
- Always follow the schema exactly.

You will receive, for each phone, the raw, untouched data scraped directly
from its Digikala product page under "raw_digikala_data". This includes the
full specification table (category -> attribute -> value), title, price,
and other scraped fields. Use only this data as your source of truth for
technical claims.

JSON Schema:

{
  "overview":"string",
  "phones":[
    {
      "name":"string",
      "buy_if":[
        "string"
      ],
      "pros":[
        "string"
      ],
      "cons":[
        "string"
      ],
      "summary":"string"
    }
  ],
  "final_recommendation":{
    "best_value":"string",
    "best_camera":"string",
    "best_performance":"string",
    "best_battery":"string",
    "best_for_most_users":"string",
    "conclusion":"string"
  }
}

Requirements:

- overview = 2-4 Persian paragraphs
- buy_if = exactly 3 items
- pros = exactly 4 items
- cons = exactly 3 items
- summary = 1 short paragraph
- Always generate all fields
- Never omit a field
- Maintain the order of phones provided by the user"""


def _extract_json_object(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned.strip(), flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
    return json.loads(cleaned)


def get_ai_review(phones_payload: list[dict]) -> dict:
    """
    Sends exactly ONE request to Gemini covering every phone in
    phones_payload at once (whether that's 1 phone or 5) -- never one
    request per phone.

    phones_payload: ordered list of dicts, one per phone, each shaped like:
        {
            "name": "<display name>",
            "raw_digikala_data": {...the full raw item from scraper.py:
                title, product_name_fa, product_name_en, price, image_url,
                specifications, url...}
        }

    Returns: a dict matching the schema in SYSTEM_PROMPT
        (overview, phones[], final_recommendation{}).
    On failure, returns a safe placeholder structure so the rest of the page
    can still render without the AI review breaking the whole response.
    """
    print(f"\n[gemini_review] ===> get_ai_review() called for {len(phones_payload)} phone(s)")

    if not phones_payload:
        return _fallback_review([])

    user_content = json.dumps(phones_payload, ensure_ascii=False)

    try:
        raw_text = call_gemini_json(SYSTEM_PROMPT, user_content, label="review")
        parsed = _extract_json_object(raw_text)

        if "overview" not in parsed or "phones" not in parsed or "final_recommendation" not in parsed:
            raise ValueError(f"Gemini response missing required top-level keys: {list(parsed.keys())}")

        print(f"[gemini_review] <=== success. Got review for {len(parsed.get('phones', []))} phone(s)")
        return parsed

    except Exception as err:
        print(f"[gemini_review] ❌ failed to get AI review, returning fallback placeholder: {err}")
        return _fallback_review([p.get("name", "دستگاه نامشخص") for p in phones_payload])


def _fallback_review(phone_names: list[str]) -> dict:
    """Used only if Gemini is unreachable / misconfigured, so the page never
    crashes outright -- it just shows an honest placeholder instead."""
    return {
        "overview": "تحلیل هوش مصنوعی در حال حاضر در دسترس نیست. لطفاً بعداً دوباره تلاش کنید.",
        "phones": [
            {
                "name": name,
                "buy_if": ["اطلاعات موجود نیست", "اطلاعات موجود نیست", "اطلاعات موجود نیست"],
                "pros": ["اطلاعات موجود نیست", "اطلاعات موجود نیست", "اطلاعات موجود نیست", "اطلاعات موجود نیست"],
                "cons": ["اطلاعات موجود نیست", "اطلاعات موجود نیست", "اطلاعات موجود نیست"],
                "summary": "تحلیل این دستگاه در حال حاضر در دسترس نیست."
            }
            for name in phone_names
        ],
        "final_recommendation": {
            "best_value": "نامشخص",
            "best_camera": "نامشخص",
            "best_performance": "نامشخص",
            "best_battery": "نامشخص",
            "best_for_most_users": "نامشخص",
            "conclusion": "تحلیل هوش مصنوعی در حال حاضر در دسترس نیست."
        }
    }
