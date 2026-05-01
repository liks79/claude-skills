Validate wiki consistency and generate an issue report.

## Usage

```
/wiki-lint
```

## Procedure

Resolve wiki base: use `${BASE_DIR:+$BASE_DIR/}wiki` as the wiki root (falls back to `wiki/` in the current working directory if `$BASE_DIR` is not set).

1. **Check broken wikilinks**
   - Collect all `[[...]]` patterns from the entire `${BASE_DIR:+$BASE_DIR/}wiki/compiled/` directory
   - Check whether each link target file exists under `compiled/`
   - If not found → add to the broken links list

2. **Identify orphaned pages**
   - Collect a list of all pages in `${BASE_DIR:+$BASE_DIR/}wiki/compiled/`
   - Pages not in `${BASE_DIR:+$BASE_DIR/}wiki/index.md` → add to the orphaned list
   - Pages not linked via `[[link]]` from any other page → add to the orphaned list

3. **Check missing frontmatter**
   - List pages missing `sources:`
   - List pages missing `updated:` or last updated more than 90 days ago

4. **Validate index.md consistency**
   - Items registered in `${BASE_DIR:+$BASE_DIR/}wiki/index.md` but whose files do not exist
   - Files that exist but are not in `index.md`

5. **Print report**

   ```
   ## /wiki-lint Report — YYYY-MM-DD

   ### Broken Links (<N>)
   - compiled/concepts/Foo.md → [[Bar]] (not found)

   ### Orphaned Pages (<N>)
   - compiled/concepts/Unused.md

   ### Stale Pages (<N>) — last updated > 90 days
   - compiled/entities/OldTool.md (updated: YYYY-MM-DD)

   ### Missing from index.md (<N>)
   - compiled/concepts/NewConcept.md

   ### Action Items
   - [ ] Fix broken links
   - [ ] Run /wiki-ingest to refresh stale pages
   - [ ] Add orphaned pages to index.md or delete
   ```

6. **Record in log.md** (append at the top)
   ```
   YYYY-MM-DD HH:MM  LINT: <N> issues found (broken:<a>, orphaned:<b>, stale:<c>)
   ```
   File: `${BASE_DIR:+$BASE_DIR/}wiki/log.md`
