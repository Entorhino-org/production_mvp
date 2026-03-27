"""
OCR service — extracts text from images using OpenRouter vision model.
"""

import base64
from pathlib import Path
from app.services.ai import client, _track_tokens, _ensure_cache, get_cached_setting, get_next_api_key, get_fallback_api_key, record_api_key_error
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()


async def extract_text_from_image(
    db: AsyncSession,
    user_id,
    image_path: str,
) -> str:
    """
    Extract text from an image using a vision-capable model via OpenRouter.
    Supports handwritten and printed text.
    Uses round-robin API keys with fallback.
    """
    # Read and encode the image as base64
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(img_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Determine MIME type
    suffix = img_path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    await _ensure_cache(db)
    ocr_model = get_cached_setting("ocr_model", settings.OPENROUTER_MODEL)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert OCR system with very high accuracy. "
                "Extract EVERY SINGLE piece of text from the provided image — "
                "including headings, subheadings, body text, bullet points, "
                "numbered lists, tables, equations, captions, footnotes, "
                "fine print, and any text in margins or sidebars. "
                "Preserve the original structure, formatting, and paragraph breaks. "
                "For handwritten text, do your best to accurately transcribe it. "
                "Do NOT summarize or skip any content. "
                "Return ONLY the extracted text, nothing else."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_data}",
                    },
                },
                {
                    "type": "text",
                    "text": "Extract ALL text from this image. Include everything — headings, body, footnotes, tables, equations. Do not skip anything.",
                },
            ],
        },
    ]

    # Round-robin key
    rr_key = get_next_api_key("openrouter")
    if rr_key:
        client.api_key = rr_key

    try:
        response = await client.chat.completions.create(
            model=ocr_model,
            messages=messages,
            max_tokens=4096,
        )
    except Exception as e:
        if rr_key:
            await record_api_key_error(rr_key, str(e))
        # Try fallback
        fallback = get_fallback_api_key("openrouter")
        if fallback and fallback != rr_key:
            client.api_key = fallback
            response = await client.chat.completions.create(
                model=ocr_model,
                messages=messages,
                max_tokens=2048,
            )
        else:
            raise

    content = response.choices[0].message.content or ""
    total_tokens = response.usage.total_tokens if response.usage else 0
    await _track_tokens(db, user_id, total_tokens)
    return content.strip()
