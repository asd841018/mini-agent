import json
import re

TOOL_USE_RE = re.compile(r"<tool_use>\s*(\{.*?\})\s*</tool_use>", re.DOTALL)

def parse_tool_use(text: str) -> dict | None:
    match = TOOL_USE_RE.search(text)
    if not match:
        return None

    raw_json = match.group(1).strip()

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid tool_use JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("tool_use must be a JSON object")

    if "name" not in payload or "arguments" not in payload:
        raise ValueError("tool_use must contain 'name' and 'arguments'")

    if not isinstance(payload["name"], str):
        raise ValueError("tool_use.name must be a string")

    if not isinstance(payload["arguments"], dict):
        raise ValueError("tool_use.arguments must be an object")

    return payload