"""
Shared Gemini API key-rotation helper.

Both gemini_msrp.py and gemini_review.py use call_gemini_json() below instead
of talking to the google-genai SDK directly. This way, key rotation/fallback
logic lives in exactly one place.
"""
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from config import GEMINI_API_KEYS, GEMINI_MODEL


def call_gemini_json(system_instruction: str, user_content: str, label: str = "gemini"):
    """
    Calls the Gemini API with a system instruction + user content, forcing
    JSON-only output. Tries each configured API key in order; if a key fails
    due to a rate limit / quota / auth error, automatically falls through to
    the next key. Raises the last error if every key fails.

    Returns: the raw response text (a JSON string) on success.
    """
    last_error = None

    for key_index, api_key in enumerate(GEMINI_API_KEYS, start=1):
        if not api_key or api_key.startswith("PASTE_YOUR"):
            print(f"[gemini_client:{label}] key slot #{key_index} is not configured, skipping")
            continue

        print(f"[gemini_client:{label}] attempting request with API key #{key_index}...")
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )
            text = response.text
            if not text or not text.strip():
                raise ValueError("Gemini returned an empty response body")

            print(f"[gemini_client:{label}] ✅ success with API key #{key_index} ({len(text)} chars returned)")
            return text

        except genai_errors.APIError as api_err:
            # 429 = rate limit / quota exceeded, 401/403 = bad or revoked key.
            # These are exactly the cases where rotating to the next key makes sense.
            print(f"[gemini_client:{label}] ❌ API key #{key_index} failed: [{getattr(api_err, 'code', '?')}] {api_err}")
            last_error = api_err
            continue

        except Exception as generic_err:
            print(f"[gemini_client:{label}] ❌ API key #{key_index} failed with unexpected error: {generic_err}")
            last_error = generic_err
            continue

    raise RuntimeError(
        f"[gemini_client:{label}] All configured Gemini API keys failed. Last error: {last_error}"
    )
