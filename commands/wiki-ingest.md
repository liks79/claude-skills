Ingest a source file or URL into the LLM wiki: $ARGUMENTS

## Usage

```
/wiki-ingest <file-path-or-url>

# File path
/wiki-ingest raw/ai-ml/ai-agent-evaluation-2026.md
/wiki-ingest notes/claude-code/discord/claude-code-discord-productivity-2026.md

# Web URL scraping
/wiki-ingest https://example.com/some-article
/wiki-ingest https://arxiv.org/abs/1706.03762

# YouTube video
/wiki-ingest https://www.youtube.com/watch?v=VIDEO_ID
/wiki-ingest https://youtu.be/VIDEO_ID
```

## Procedure

Resolve wiki base: use `${BASE_DIR:+$BASE_DIR/}wiki` as the wiki root (falls back to `wiki/` in the current working directory if `$BASE_DIR` is not set).

First, read `${BASE_DIR:+$BASE_DIR/}wiki/CLAUDE.md` using the Read tool to confirm the schema and templates.

1. **Read source**
   - If `$ARGUMENTS` contains `youtube.com` or `youtu.be`, use **YouTube mode**:
     - Extract the video ID from the URL (`watch?v=VIDEO_ID` or `youtu.be/VIDEO_ID`)
     - Run the following Python script via Bash to fetch the transcript and metadata:
       ```bash
       uv run python -c "
       from youtube_transcript_api import YouTubeTranscriptApi
       api = YouTubeTranscriptApi()
       transcript = api.fetch('VIDEO_ID', languages=['ko', 'en', 'en-US'])
       print(' '.join([t.text for t in transcript]))
       "
       ```
     - If transcript extraction fails (`TranscriptsDisabled`, `NoTranscriptFound`): notify the user and stop
     - Supplement title, channel, and other metadata via WebFetch from `https://www.youtube.com/watch?v=VIDEO_ID`
     - Record source metadata (`url`, `fetched_at`, `video_id`) in the frontmatter `sources:` field
   - If `$ARGUMENTS` starts with `http://` or `https://`, use **web URL mode**:
     - Fetch the full page content via WebFetch
     - Extract only the main content — remove headers, footers, ads, and navigation
     - Record source metadata (`url`, `fetched_at`) in the frontmatter `sources:` field
     - If WebFetch returns a redirect, retry with the redirect URL
   - If `$ARGUMENTS` starts with `raw/`, use it as a file path directly
   - Otherwise, read using the Read tool as an absolute or relative path

2. **Analyze**
   - Identify 5–15 key concepts: abstract concepts that can be defined
   - Identify 3–8 entities: people, organizations, tools, frameworks
   - Identify relationships between concepts and entities

3. **Update wiki/compiled/**
   - Create/update `${BASE_DIR:+$BASE_DIR/}wiki/compiled/concepts/<PascalCase>.md`
   - Create/update `${BASE_DIR:+$BASE_DIR/}wiki/compiled/entities/<PascalCase>.md`
   - Do not overwrite existing pages — merge content and update the `updated:` date
   - Automatically add `[[wikilink]]` cross-references
   - Follow the Page Template format in `${BASE_DIR:+$BASE_DIR/}wiki/CLAUDE.md`

4. **Update index.md**
   - Add new pages to the Concepts / Entities / Syntheses sections in `${BASE_DIR:+$BASE_DIR/}wiki/index.md`
   - Update the total page count

5. **Record in log.md** (append at the top)
   ```
   YYYY-MM-DD HH:MM  INGEST: <source> → <N> concepts, <M> entities created/updated
   ```
   File: `${BASE_DIR:+$BASE_DIR/}wiki/log.md`

6. **Print change summary**
   - List of created pages
   - List of updated pages
   - Number of `[[wikilink]]` references added
