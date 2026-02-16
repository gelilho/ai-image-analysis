"""Utilities for cleaning LLM JSON responses."""

import re


def clean_json_response(response: str) -> str:
    """Extract valid JSON from a Gemini response string.

    Handles markdown code blocks, BOM characters, and text
    surrounding the JSON object.
    """
    if not response:
        return ""

    text = response.strip().lstrip("\ufeff")

    # Strip markdown ```json ... ``` wrapper
    md = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if md:
        text = md.group(1).strip()

    # Find outermost { ... } pair
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if start == -1:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                return text[start : i + 1]

    return text
