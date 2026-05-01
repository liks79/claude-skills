Query the LLM wiki and synthesize an answer: $ARGUMENTS

## Usage

```
/wiki-query <question>
/wiki-query "What is the difference between RAG and an LLM Wiki?"
/wiki-query "How to integrate Claude Code with Discord"
/wiki-query "How to use Bitwarden on a Linux server"
```

## Procedure

Resolve wiki base: use `${BASE_DIR:+$BASE_DIR/}wiki` as the wiki root (falls back to `wiki/` in the current working directory if `$BASE_DIR` is not set).

1. **Browse index.md**
   - Read `${BASE_DIR:+$BASE_DIR/}wiki/index.md`
   - Identify Concepts / Entities / Syntheses related to the `$ARGUMENTS` keywords

2. **Read pages**
   - Read relevant `${BASE_DIR:+$BASE_DIR/}wiki/compiled/concepts/` pages
   - Read relevant `${BASE_DIR:+$BASE_DIR/}wiki/compiled/entities/` pages
   - Read relevant `${BASE_DIR:+$BASE_DIR/}wiki/compiled/syntheses/` pages (if available)
   - Reference `${BASE_DIR:+$BASE_DIR/}wiki/raw/` original sources if needed

3. **Write answer**
   - Cite sources using `[[wikilink]]` references
   - Synthesize information from multiple pages into a coherent answer
   - For uncertain content, note "not in wiki — add with `/wiki-ingest`"

4. **Suggest saving synthesis**
   - If the answer has value as a standalone guide, suggest saving it:
     `Save to ${BASE_DIR:+$BASE_DIR/}wiki/compiled/syntheses/<Title>.md?`

5. **Record in log.md** (append at the top)
   ```
   YYYY-MM-DD HH:MM  QUERY: "<question>" → <N> pages referenced
   ```
   File: `${BASE_DIR:+$BASE_DIR/}wiki/log.md`
