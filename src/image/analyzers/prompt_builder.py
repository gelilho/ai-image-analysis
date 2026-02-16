"""Build the structured Gemini prompt for image analysis."""

from datetime import datetime


def build_analysis_prompt(
    retailer_list: list[str],
    product_list: list[str],
    vertical_list: list[str],
    family_list: list[str],
    model_list: list[str],
) -> str:
    """Return the full Gemini analysis prompt with injected feature lists."""
    retailers = ",\n                    ".join(retailer_list)
    products = ",\n            ".join(product_list)
    verticals = ",\n".join(vertical_list)
    families = ",\n".join(family_list)
    models = ",\n".join(model_list)
    max_year = datetime.now().year + 2

    return f"""
Analyze this image and provide a detailed JSON response with the following structure:
{{
    "classification_labels": [
        {{"label": "primary category", "confidence": 1-100}},
        {{"label": "secondary category if applicable", "confidence": 1-100}}
    ],
    "tag_information": {{
        "is_tag_present": true/false,
        "extracted_fields": [
            {{"field_name": "e.g. size_us", "value": "extracted text", "confidence": 1-100}}
        ],
        "raw_text": "complete raw text visible on the tag",
        "overall_confidence": 1-100
    }},
    "labels": ["list", "of", "single", "word", "labels"],
    "primary_label": "most_relevant_single_word",
    "description": "A detailed description of what's in the image",
    "objects_detected": ["list", "of", "objects"],
    "contains_harmful_content": false,
    "harmful_content_type": null or "violence|adult|drugs|weapons|other",
    "safety_score": 0.0 to 1.0,
    "on_running_related": false,
    "on_running_confidence": 0.0 to 1.0,
    "on_running_details": "Details if related to On Running brand",
    "detected_brands": ["list", "of", "brands"],
    "is_product_image": false,
    "is_athletic_content": false,
    "image_quality": "high|medium|low",
    "dominant_colors": ["list", "of", "colors"],
    "scene_type": "indoor|outdoor|studio|unknown",
    "people_count": 0,
    "text_detected": "any text visible in the image or null",
    "image_category": <one of: "PROOF_OF_PURCHASE", "SHOE_SOLES", "SHOE_INNERTAG", "SHOE_LABEL", "SHOE_DEFECT", "OTHER">,
    "product_category": <one of: "shoes", "accessories", "apparel">,
    "product_gender": <one of: "Mens", "Womens", "Unisex", "Youth", "Kids">,
    "product_year": <integer 2020-{max_year}>,
    "product_season": <one of: "Spring/Summer", "Fall/Winter">,
    "product_vertical": <one of: {verticals}>,
    "product_family": <list of 2 best matches from: {families}>,
    "product_model": <list of 3 best matches from: {models}>,
    "product_generation": <integer 1-9>,
    "product_primary_colour": "#HEX",
    "product_secondary_colour": "#HEX",
    "language_category": <one of: "en", "fr", "de", "es", "it", "pt", "ja", "zh", "other">,
    "receipt_fields": <include only if image is a receipt> {{
        "receipt_type": <one of: "official_receipt_paper", "official_receipt_digital", "invoice", "e_receipt", "order_confirmation", "bank_statement", "bank_transfer_screenshot", "payment_confirmation", "shipping_label", "other">,
        "image_in_receipt": true/false,
        "retailer_name": <closest match from: {retailers} or "other"/"missing"/"unclear">,
        "retailer_raw": "raw retailer string",
        "retailer_location": "location or online",
        "purchase_date": "YYYY-MM-DD or unclear",
        "product_counts": {{"product_name": quantity}},
        "product_prices": {{"product_name": price_float}},
        "product_skus": {{"product_name": "sku"}},
        "transaction_number": "order number",
        "url": "web address if online",
        "address": "physical address if in-store",
        "country": "purchase country",
        "confidence": 0.0 to 1.0
    }}
}}

Use product names from this list for receipts: {products}

GUIDELINES:
- Provide 1-5 classification labels ranked by relevance
- Extract ALL visible tag fields with individual confidence scores
- For On Running detection look for: CloudTec, Swiss Engineering, on-running.com
- For product fields: always give your best guess, never return None
- Return ONLY valid JSON, no additional text.
"""
