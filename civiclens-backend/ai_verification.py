import os
import json
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

_client = None


def get_client():
    """Lazily create the Gemini client (so app can still start without a key set,
    and so the heavy google-genai library only loads into memory when actually needed)."""
    global _client
    if _client is None:
        from google import genai
        from google.genai import types
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=15000),  # 15 seconds, in ms
        )
    return _client


VALID_CATEGORIES = ["pothole", "garbage", "streetlight", "water", "other"]

# Try the primary model first; if it's overloaded, fall back to a second
# model rather than failing the whole verification.
MODEL_CANDIDATES = ["gemini-flash-latest", "gemini-2.5-flash"]

MAX_RETRIES_PER_MODEL = 1
BASE_BACKOFF_SECONDS = 0.6

PROMPT = """You are an AI verification system for a civic issue reporting app
used by citizens of Lahore, Pakistan.

You will be given a photo submitted by a citizen along with their description:
"{description}"
Their selected category was: "{category}"

Look at the photo and decide:
1. is_genuine: true if the photo plausibly shows a real civic/infrastructure
   issue (pothole, damaged road, garbage/trash pile, broken streetlight,
   water leakage or sewerage overflow, or another visible civic problem).
   false if the photo is irrelevant, a random/unrelated object, a selfie,
   blank/blurry beyond recognition, or clearly not a civic issue.
2. predicted_category: the single best match from exactly these options,
   based on what the PHOTO actually shows (ignore the citizen's selected
   category if it doesn't match the photo):
   ["pothole", "garbage", "streetlight", "water", "other"]
3. category_match: true if the citizen's selected category ("{category}")
   matches what the photo actually shows, false if they picked the wrong
   category (e.g. selected "streetlight" but the photo shows garbage).
4. confidence: "high", "medium", or "low" based on how clearly the photo
   shows the issue.
5. priority: "high", "medium", or "low" — how urgent this issue looks
   (e.g. a large pothole blocking a road or a major sewerage overflow is
   high priority; a small cosmetic issue is low priority).
6. reasoning: one short sentence explaining your decision. If
   category_match is false, explicitly mention the correction, e.g.
   "Citizen selected streetlight, but photo shows a garbage pile — category
   corrected to garbage."

Respond with ONLY valid JSON in exactly this shape, no markdown, no extra text:
{{
  "is_genuine": true,
  "predicted_category": "pothole",
  "category_match": true,
  "confidence": "high",
  "priority": "medium",
  "reasoning": "short explanation here"
}}
"""


def _call_gemini(model_name, image_bytes, mime_type, prompt):
    """One attempt at calling a given model. Raises on failure."""
    from google.genai import types

    client = get_client()
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


def _is_retryable(exc):
    """503 (overloaded) and 429 (rate limited) are worth retrying; other
    errors (bad key, bad request, etc.) are not."""
    try:
        from google.genai import errors as genai_errors
        if isinstance(exc, genai_errors.APIError):
            return getattr(exc, "code", None) in (503, 429)
    except Exception:
        pass
    return "503" in str(exc) or "UNAVAILABLE" in str(exc) or "429" in str(exc)


def analyze_report_image(image_bytes, mime_type, description, category):
    """
    Send the uploaded photo + context to Gemini and get back a structured
    verification result. Retries transient failures (model overloaded /
    rate limited) with backoff, and falls back to a secondary model before
    giving up. Only returns is_genuine=None if every attempt truly fails.
    """
    if not GEMINI_API_KEY:
        return {
            "is_genuine": None,
            "predicted_category": category,
            "confidence": "unavailable",
            "priority": "medium",
            "reasoning": "AI verification not configured (missing GEMINI_API_KEY).",
        }

    prompt = PROMPT.format(description=description, category=category)
    last_error = None

    for model_name in MODEL_CANDIDATES:
        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                result = _call_gemini(model_name, image_bytes, mime_type, prompt)
                if result.get("predicted_category") not in VALID_CATEGORIES:
                    result["predicted_category"] = category
                return result
            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < MAX_RETRIES_PER_MODEL - 1:
                    time.sleep(BASE_BACKOFF_SECONDS * (2 ** attempt))
                    continue
                break

    return {
        "is_genuine": None,
        "predicted_category": category,
        "confidence": "error",
        "priority": "medium",
        "reasoning": f"AI verification failed: {str(last_error)}",
    }