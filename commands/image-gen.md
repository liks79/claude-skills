Generate an image using NanoBanana or Imagen via Google Gemini API. $ARGUMENTS

---

## Usage

```
/image-gen <prompt>
/image-gen <prompt> --output <path>
/image-gen <prompt> --model gemini-2.0-flash-preview-image-generation
```

## Models

| Option | Model | Characteristics |
|--------|-------|-----------------|
| `nano-banana` | `gemini-2.5-flash-image` | NanoBanana — fast |
| `nano-banana-2` (default) | `gemini-3.1-flash-image-preview` | NanoBanana 2 — latest |
| `nano-banana-pro` | `gemini-3-pro-image-preview` | NanoBanana Pro — high quality |
| `imagen-4` | `imagen-4.0-generate-001` | Imagen 4 — stable |
| `imagen-4-fast` | `imagen-4.0-fast-generate-001` | Imagen 4 Fast |

## Procedure

1. Parse the prompt and options from `$ARGUMENTS`.
   - If `--output <path>` is provided, use it as the output path
   - Otherwise use `${BASE_DIR:+$BASE_DIR/}notes/image-gen/generated_<timestamp>.png`
   - If `--model <model>` is provided, use that model
   - Use the remaining text as the prompt

2. Run the following command:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "generate_image.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/generate_image.py"
uv run --with google-genai python "$_S" \
  --prompt "<prompt>" \
  --output "<output_path>" \
  --model "<model>"
```

3. On success:
   - Report the saved file path
   - Read the image file using the `Read` tool and show it to the user

4. On failure, pass the error message as-is and explain the cause.

## Example

```
/image-gen A snowy Christmas night with a decorated tree and warm glowing lights
/image-gen New Year's fireworks over the Han River in Seoul --output notes/image-gen/fireworks.png
/image-gen cute cat wearing a santa hat --model gemini-2.0-flash-preview-image-generation
```
