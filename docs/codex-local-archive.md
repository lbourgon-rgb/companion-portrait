# Codex Local Archive Adapter

This repo started from `companion-portrait`, which expects exported ChatGPT or Claude transcripts.
Codex already stores local metadata under `C:\Users\Allen\.codex`, so this adapter maps the archive before
any transcript extraction.

## Current Safe Step

Run:

```powershell
python scripts\inventory_codex_archive.py --codex-home C:\Users\Allen\.codex --output-dir data
```

Outputs:

- `data/codex-archive-map.md` — human-readable source map.
- `data/codex-archive-summary.json` — counts and log distribution.
- `data/codex-archive-thread-inventory.csv` — thread-level metadata for selecting evidence.

## Boundaries

- The inventory script is read-only against `.codex`.
- It does not copy raw transcript bodies.
- It does not read or export secrets.
- It includes thread titles and short previews, so treat generated files as private local artifacts.

## Next Decision

Before extracting evidence chunks, choose an evidence policy:

- `summaries-first`: use `stage1_outputs` and memory summaries before raw rollout bodies.
- `selected-threads`: extract only chosen rollout JSONL files by thread id.
- `full-local`: bulk extract all available rollout bodies into portrait chunks.

Default recommendation: `summaries-first`, then selected raw excerpts only where a pattern needs proof.
