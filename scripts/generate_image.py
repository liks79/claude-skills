#!/usr/bin/env python3
"""
NanoBanana / Imagen image generation script.

Reads GEMINI_API_KEY from environment or ~/.config/gws/.env
and generates an image using Google's image generation API.

Usage:
    uv run --with google-genai python .claude/scripts/generate_image.py \
        --prompt "A festive Christmas scene" \
        [--output ./output.png] \
        [--model nano-banana]

Models:
    nano-banana         gemini-2.5-flash-image           (NanoBanana, fast)
    nano-banana-2       gemini-3.1-flash-image-preview   (NanoBanana 2, latest)
    nano-banana-pro     gemini-3-pro-image-preview       (NanoBanana Pro, high quality)
    imagen-4            imagen-4.0-generate-001          (Imagen 4, stable)
    imagen-4-fast       imagen-4.0-fast-generate-001     (Imagen 4 Fast)
"""

import argparse
import base64
import os
import sys
from pathlib import Path

# Model alias → actual API model ID
MODEL_MAP = {
    "nano-banana": "gemini-2.5-flash-image",
    "nano-banana-2": "gemini-3.1-flash-image-preview",
    "nano-banana-pro": "gemini-3-pro-image-preview",
    "imagen-4": "imagen-4.0-generate-001",
    "imagen-4-fast": "imagen-4.0-fast-generate-001",
    # direct model IDs also accepted
    "gemini-2.5-flash-image": "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview": "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview": "gemini-3-pro-image-preview",
    "imagen-4.0-generate-001": "imagen-4.0-generate-001",
    "imagen-4.0-fast-generate-001": "imagen-4.0-fast-generate-001",
}

# Models that use generate_images() — Imagen family
IMAGEN_MODELS = {"imagen-4.0-generate-001", "imagen-4.0-fast-generate-001", "imagen-4.0-ultra-generate-001"}


def load_api_key(env_path: str | None = None) -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_CLAUDE_CODE")
    if key:
        return key

    resolved = Path(env_path) if env_path else Path.home() / ".config" / "gws" / ".env"
    if resolved.exists():
        for line in resolved.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_CLAUDE_CODE=") or line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()

    print(
        "Error: GEMINI_API_KEY not set. Add it to settings.local.json env block or "
        f"~/.config/gws/.env",
        file=sys.stderr,
    )
    sys.exit(1)


def generate_with_nanobanana(client: object, model_id: str, prompt: str, output_path: Path) -> None:
    """NanoBanana family: uses generate_content with IMAGE modality."""
    from google.genai import types

    response = client.models.generate_content(  # type: ignore[attr-defined]
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    image_bytes = None
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            data = part.inline_data.data
            # SDK returns raw bytes directly (not base64-encoded string)
            image_bytes = data if isinstance(data, bytes) else base64.b64decode(data)
            break

    if image_bytes is None:
        text = getattr(response, "text", "")
        print(f"Error: No image in response. Text: {text}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)


def generate_with_imagen(client: object, model_id: str, prompt: str, output_path: Path) -> None:
    """Imagen family: uses generate_images()."""
    from google.genai import types

    response = client.models.generate_images(  # type: ignore[attr-defined]
        model=model_id,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        ),
    )

    image_bytes = response.generated_images[0].image.image_bytes
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate images using NanoBanana / Imagen")
    parser.add_argument("--prompt", "-p", required=True, help="Image generation prompt")
    parser.add_argument(
        "--output", "-o",
        default="./image-gen/generated_image.png",
        help="Output file path (default: ./image-gen/generated_image.png)",
    )
    parser.add_argument(
        "--model", "-m",
        default="nano-banana-2",
        choices=list(MODEL_MAP.keys()),
        help="Model alias or ID (default: nano-banana-2)",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Path to .env file with GEMINI_API_KEY (default: ~/.config/gws/.env)",
    )
    args = parser.parse_args()

    try:
        from google import genai
    except ImportError:
        print("Error: Run with: uv run --with google-genai python ...", file=sys.stderr)
        sys.exit(1)

    api_key = load_api_key(args.env)
    model_id = MODEL_MAP[args.model]
    output_path = Path(args.output)

    client = genai.Client(api_key=api_key)

    print(f"Model   : {args.model} ({model_id})")
    print(f"Prompt  : {args.prompt}")
    print(f"Output  : {output_path}")

    if model_id in IMAGEN_MODELS:
        generate_with_imagen(client, model_id, args.prompt, output_path)
    else:
        generate_with_nanobanana(client, model_id, args.prompt, output_path)

    print(f"✅ Saved : {output_path.resolve()}")


if __name__ == "__main__":
    main()
