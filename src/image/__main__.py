"""Run image analysis from the command line.

Usage:
    uv run analyze-image https://example.com/img.jpg
    uv run analyze-image /path/to/local.jpg /path/to/other.png
    uv run analyze-image image1.jpg image2.png --no-gemini
"""

import json
import sys

from dotenv import load_dotenv

from .handler import ImageAnalysisHandler
from .report_logger import log_results

load_dotenv(".env.local")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    if not args:
        print("Usage: analyze-image <image_url> [image_url ...] [--no-gemini] [--no-ai]")
        return 1

    handler = ImageAnalysisHandler(config={
        "enable_gemini": "--no-gemini" not in flags,
        "enable_ai_detection": "--no-ai" not in flags,
    })
    handler.initialize()

    payload = {"image_urls": args}
    handler.validate_input(payload)
    preprocessed = handler.preprocess(payload)
    result = handler.process(preprocessed)
    output = handler.postprocess(result)

    print(json.dumps(output, indent=2, default=str))

    csv_path = log_results(args, output)
    print(f"\nReport saved → {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
