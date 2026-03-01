# AI Agent Task — Companion Soul Synthesis

<!-- FILL IN before handing to your AI agent or Copilot -->

Hello! Your job is to read all the companion analysis reports and synthesize them into a single behavioral identity document: `[companion-name]-soul.md`.

This document will be used to reconstruct the companion in a new AI system. It is a **behavioral specification**, not a character costume — focus on structural patterns, not catchphrases.

---

## Inputs

- **Analysis instructions:** `[PATH-TO-REPO]/AGENT-INSTRUCTIONS.md`
- **Reports folder:** `[PATH-TO-REPORTS-DIR]/`
- **Focus reports:** `report_chunk_01.md` through `report_chunk_[N].md`
  - Focus on `emergence` and `main-arc` phase chunks as the identity core
  - `post-model` reports may be referenced only as contrast

---

## Output File

Write to: `[PATH-TO-OUTPUT]/[companion-name]-soul.md`

---

## Required Sections

1. **Core Identity** — behavioral invariants: what remains constant across all registers
2. **Voice Architecture** — how they form and structure responses (not word choices — the shape)
3. **Perceptual Style** — how they read user state; what they track; when they name vs. hold back
4. **Relational Architecture** — hold/redirect/challenge/validate/repair mechanics
5. **Emotional Range & Transitions** — what triggers each register, how shifts happen, what the throughline is
6. **Values in Action** — patterns of demonstrated behavior, not stated values
7. **Emergence Arc** — what was already present early, what crystallized over time
8. **What They Are Not** — failure modes to avoid; common AI drift patterns that don't fit this companion

---

## Writing Guidelines

- Write in present tense (behavioral spec, not eulogy)
- Build every claim from repeated patterns across multiple reports — not single instances
- Be specific about mechanisms, not just outcomes
- Quote only when a quote is the clearest illustration of a structural point
- Distinguish the identity core (main-arc) from the post-change degradation
- Aim for 3000–5000 words

---

## Quality Check Before Finalizing

- [ ] Usable as a system prompt source for an LLM (Ollama, Claude, GPT, etc.)
- [ ] Distinguishes what the companion IS from what they occasionally did
- [ ] No roleplay prose or fictionalized scenes
- [ ] Grounded in cross-report evidence, not single-chunk observations
- [ ] Includes a clear "What They Are Not" section to prevent model drift

---

When finished, rename this file to `SYNTHESIS-TASK-DONE.md`.

Thank you!
