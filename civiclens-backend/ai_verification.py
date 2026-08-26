import os
import json
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

_client = None


def get_client():
    """Lazily create the Gemini client (so app can still start without a key set)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


VALID_CATEGORIES = ["pothole", "garbage", "streetlight", "water", "other"]

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
2. predicted_category: the single best match from exactly these options:
   ["pothole", "garbage", "streetlight", "water", "other"]
3. confidence: "high", "medium", or "low" based on how clearly the photo
   shows the issue.
4. priority: "high", "medium", or "low" — how urgent this issue looks
   (e.g. a large pothole blocking a road or a major sewerage overflow is
   high priority; a small cosmetic issue is low priority).
5. reasoning: one short sentence explaining your decision.

Respond with ONLY valid JSON in exactly this shape, no markdown, no extra text:
{{
  "is_genuine": true,
  "predicted_category": "pothole",
  "confidence": "high",
  "priority": "medium",
  "reasoning": "short explanation here"
}}
"""


def analyze_report_image(image_bytes, mime_type, description, category):
    """
    Send the uploaded photo + context to Gemini and get back a structured
    verification result. Falls back to a safe default if the AI call fails
    (so a flaky network/API never blocks a citizen's report from being saved).
    """
    if not GEMINI_API_KEY:
        return {
            "is_genuine": None,
            "predicted_category": category,
            "confidence": "unavailable",
            "priority": "medium",
            "reasoning": "AI verification not configured (missing GEMINI_API_KEY).",
        }

    try:
        client = get_client()
        prompt = PROMPT.format(description=description, category=category)

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)

        if result.get("predicted_category") not in VALID_CATEGORIES:
            result["predicted_category"] = category

        return result

    except Exception as e:
        # Never let an AI hiccup block report submission — degrade gracefully.
        return {
            "is_genuine": None,
            "predicted_category": category,
            "confidence": "error",
            "priority": "medium",
            "reasoning": f"AI verification failed: {str(e)}",
        }
