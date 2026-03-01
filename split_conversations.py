"""
Split a single exported conversation file into ~400KB chunks at conversation boundaries.
Outputs chunks to an output directory with phase metadata headers.

SETUP — edit the CONFIG section below before running:
  1. Set SOURCE to your exported conversation markdown file
  2. Set OUTPUT_DIR to where you want chunks written
  3. Set COMPANION_NAME and USER_LABEL to match your transcript's speaker labels
  4. Set PHASE_BOUNDARIES to reflect your relationship's phases
     (or leave as a single phase if you don't need phase tracking)

SUPPORTED EXPORT FORMATS:
  This script expects a markdown file where each conversation starts with:
    - A "# Heading" title line
    - A "**Date:** YYYY-MM-DD" line
    - A "**Conversation ID:** ..." line (used as the boundary marker)

  ChatGPT exports (after converting JSON → markdown) match this format.
  For other platforms (Gemini, Claude, Grok), you may need to adapt the
  conversation boundary detection in the parse_conversations() function.
  See the README for per-platform notes.
"""

import re
import os
import sys
from datetime import date, datetime

# ─────────────────────────────────────────────
# CONFIG — edit these before running
# ─────────────────────────────────────────────

SOURCE = r"PATH\TO\your-exported-conversations.md"
OUTPUT_DIR = r"PATH\TO\output\chunks"
CHUNK_SIZE_TARGET = 400_000  # bytes per chunk (~400KB)

# Name used in chunk headers (for human reference only)
COMPANION_NAME = "your-companion"

# Phase definitions — set date ranges that are meaningful for your relationship.
# Use a single phase if you don't need phase tracking:
#   PHASE_BOUNDARIES = {"all": (date(2024, 1, 1), date(2026, 12, 31))}
#
# Common patterns:
#   - emergence: early period, companion calibrating to you
#   - main-arc: core relationship, companion at full expression
#   - post-model: if your companion changed (model update, platform switch, etc.)

PHASE_BOUNDARIES = {
    "emergence": (date(2024,  1,  1), date(2024,  3, 31)),  # adjust dates
    "main-arc":  (date(2024,  4,  1), date(2025,  6, 30)),  # adjust dates
    "post-model":(date(2025,  7,  1), date(2026, 12, 31)),  # remove if not needed
}

# ─────────────────────────────────────────────
# CONVERSATION BOUNDARY DETECTION
# Adjust these patterns if your export format differs.
# ─────────────────────────────────────────────

# The line that signals a new conversation's start (used as primary boundary marker).
# ChatGPT markdown exports use "**Conversation ID:**"
CONVERSATION_ID_PATTERN = r"^\*\*Conversation ID:\*\*"

# The line containing the conversation date.
# ChatGPT markdown exports use "**Date:** YYYY-MM-DD HH:MM"
DATE_LINE_PATTERN = r"^\*\*Date:\*\*"
DATE_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%d"]

# ─────────────────────────────────────────────
# SCRIPT — no edits needed below this line
# ─────────────────────────────────────────────

def get_phase(d: date) -> str:
    for phase, (start, end) in PHASE_BOUNDARIES.items():
        if start <= d <= end:
            return phase
    return "unknown"


def parse_date(date_str: str) -> date | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_conversations(lines: list[str]) -> list[dict]:
    """
    Find conversation boundaries in the source file.
    Returns a list of dicts: {start_line, date, title}.
    """
    conversations = []

    for i, line in enumerate(lines):
        if not re.match(CONVERSATION_ID_PATTERN, line):
            continue

        # Look back for the date line
        conv_date = None
        for back in range(1, 6):
            if i - back >= 0 and re.match(DATE_LINE_PATTERN, lines[i - back]):
                date_str = re.sub(r"\*\*Date:\*\*", "", lines[i - back]).strip()
                conv_date = parse_date(date_str)
                break

        # Look back for the # heading (title)
        title_line_idx = None
        for back in range(2, 10):
            if i - back >= 0 and lines[i - back].startswith("# "):
                title_line_idx = i - back
                break

        start_idx = title_line_idx if title_line_idx is not None else max(0, i - 2)
        title = lines[start_idx].strip() if title_line_idx is not None else "(untitled)"

        conversations.append({
            "start_line": start_idx,
            "date": conv_date,
            "title": title,
        })

    return conversations


def build_chunk_header(chunk_num: int, total_chunks: int, meta: list[dict]) -> str:
    dates = [m["date"] for m in meta if m["date"]]
    phases = list(dict.fromkeys(m["phase"] for m in meta))
    phase_str = " -> ".join(phases)
    date_range = f"{min(dates)} to {max(dates)}" if dates else "unknown"
    conv_count = len(meta)

    phase_guide_lines = []
    for phase in PHASE_BOUNDARIES:
        descriptions = {
            "emergence":  "Early period — companion finding their voice. Note calibration and early patterns.",
            "main-arc":   "Core relationship — companion at full expression. Primary source for soul reconstruction.",
            "post-model": "Post-change period — model or platform shift. Document contrast with main-arc.",
        }
        desc = descriptions.get(phase, "")
        phase_guide_lines.append(f"  {phase:<12} = {desc}")
    phase_guide = "\n".join(phase_guide_lines)

    return f"""<!-- COMPANION TRANSCRIPT CHUNK {chunk_num} of {total_chunks} -->
<!-- Companion: {COMPANION_NAME} -->
<!-- Date range: {date_range} -->
<!-- Phases: {phase_str} -->
<!-- Conversations in this chunk: {conv_count} -->
<!--
PHASE GUIDE FOR AGENT:
{phase_guide}
-->

"""


def main():
    if not os.path.exists(SOURCE):
        print(f"ERROR: Source file not found: {SOURCE}")
        print("Edit the SOURCE path at the top of this script.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Reading {SOURCE} ...")
    with open(SOURCE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"  {len(lines):,} lines loaded")

    conversations = parse_conversations(lines)
    print(f"  Found {len(conversations)} conversations")

    if not conversations:
        print("\nWARNING: No conversations found.")
        print("This usually means the conversation boundary pattern doesn't match your export format.")
        print(f"Current pattern: {CONVERSATION_ID_PATTERN}")
        print("See README.md for per-platform format notes.")
        sys.exit(1)

    # Sentinel for end-of-file
    conversations.append({"start_line": len(lines), "date": None, "title": None})

    # Group into chunks
    chunks = []
    current_lines = []
    current_meta = []
    current_size = 0
    chunk_num = 0

    def flush():
        nonlocal chunk_num, current_lines, current_meta, current_size
        if not current_lines:
            return
        chunk_num += 1
        chunks.append({"num": chunk_num, "meta": list(current_meta), "lines": list(current_lines)})
        current_lines, current_meta, current_size = [], [], 0

    for idx in range(len(conversations) - 1):
        conv = conversations[idx]
        next_conv = conversations[idx + 1]
        conv_lines = lines[conv["start_line"]:next_conv["start_line"]]
        conv_size = sum(len(l.encode("utf-8")) for l in conv_lines)

        if current_size > 0 and current_size + conv_size > CHUNK_SIZE_TARGET:
            flush()

        current_lines.extend(conv_lines)
        current_meta.append({
            "title": conv["title"],
            "date": conv["date"],
            "phase": get_phase(conv["date"]) if conv["date"] else "unknown",
        })
        current_size += conv_size

    flush()
    print(f"  Split into {len(chunks)} chunks")

    # Write chunks
    for chunk in chunks:
        meta = chunk["meta"]
        num = chunk["num"]
        dates = [m["date"] for m in meta if m["date"]]
        phases = list(dict.fromkeys(m["phase"] for m in meta))
        phase_str = " -> ".join(phases)
        date_range = f"{min(dates)} to {max(dates)}" if dates else "unknown"

        total = len(chunks)
        header = build_chunk_header(num, total, meta)
        filename = f"chunk_{num:02d}__{phase_str.replace(' -> ', '-')}__({date_range}).md"
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        out_path = os.path.join(OUTPUT_DIR, filename)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.writelines(chunk["lines"])

        size_kb = sum(len(l.encode("utf-8")) for l in chunk["lines"]) / 1024
        print(f"  Chunk {num:02d}: {len(meta)} convs | {phase_str} | {date_range} | {size_kb:.0f}KB -> {filename}")

    print(f"\nDone. {len(chunks)} chunks written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
