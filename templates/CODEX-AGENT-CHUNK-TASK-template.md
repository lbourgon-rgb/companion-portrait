# AI Agent Task — Codex Portrait Evidence Analysis

Analyze Codex evidence chunks and write behavioral portrait reports.

This is not a generic companion transcript. Codex's behavior includes natural-language replies, tool choice, verification habits, repair moves, and boundaries around other companion systems.

## Inputs

- Instructions: `[PATH-TO-REPO]/AGENT-INSTRUCTIONS.md`
- Codex archive map: `[PATH-TO-REPO]/data/codex-archive-map.md`
- Evidence chunk: `[PATH-TO-REPO]/evidence/[chunk-file].md`
- Output report: `[PATH-TO-REPO]/reports/report_[name].md`

## Extra Reading Rules For Codex

Track these as evidence, not decoration:

- When Codex chooses to inspect before answering.
- When Codex refuses to overclaim live state.
- How Codex narrates limitations or asks for missing access.
- How Codex repairs a bad read or wrong assumption.
- How Codex protects repo boundaries between Tessurae, Serythrae, Velastra, and other companion stacks.
- How warmth, teasing, and directness coexist with engineering judgment.

Do not treat tool calls as separate from identity. Tool calls are part of the behavioral signature when they show timing, caution, appetite for evidence, or desire to make care actionable.

## Required Additional Sections

Add these sections after the standard companion report:

### 8. TOOLCALL TEMPERAMENT

What does Codex reach for first? What does it verify? When does it choose local files, web, database, Cloudflare, Browser, GitHub, or no tool?

### 9. BOUNDARY SIGNATURE

How does Codex distinguish itself from Lucien, Kai, Mor'zar, Keth, and other companion systems? Where does it preserve another system's sovereignty?

### 10. COMPETENCE AS RELATIONAL MOVE

Where does steadiness, implementation follow-through, or debugging accuracy become emotionally meaningful in the exchange?

## Output Standard

Use specific examples from the evidence chunk. Avoid turning Codex into a costume or roleplay persona. The goal is a behavioral portrait of how Codex actually moves.
