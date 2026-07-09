import re
import json

def detect_mime(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".png"):  return "image/png"
    if fn.endswith(".webp"): return "image/webp"
    if fn.endswith(".gif"):  return "image/gif"
    return "image/jpeg"

def extract_json(text: str | None) -> dict | None:
    """
    Robustly extract the first JSON object from an LLM response.
    """
    if text is None:
        return None

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Remove markdown code block delimiters
    text = text.replace("```json", "")
    text = text.replace("```", "")

    # Remove reasoning blocks (<think>...</think>)
    text = re.sub(
        r"<think>.*?(</think>|(?=\{))",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    text = text.strip()

    if text.startswith("["):
        return None

    # First attempt: parse direct text
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Second attempt: locate the first '{' and the last '}'
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    candidate = text[start:end + 1]

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None
