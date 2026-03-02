"""
Convert a Claude.ai JSON conversation export to a single markdown file
suitable for use with split_conversations.py.

SETUP — edit the CONFIG section below before running:
  1. Set SOURCE to your claude-conversations.json file
  2. Set OUTPUT to where you want the markdown written
  3. Set USER_LABEL and COMPANION_LABEL to match how you want speakers labeled
     in the output (these become the ## SPEAKER: headings the agents read)

HOW TO EXPORT FROM CLAUDE:
  Claude Desktop / claude.ai → Settings → Account → Export Data
  You'll receive a ZIP. Inside is conversations.json (or claude-conversations.json).
  That file is the input for this script.

OUTPUT FORMAT:
  Produces a single .md file where each conversation has:
    # [conversation title]
    **Date:** YYYY-MM-DD HH:MM
    **Conversation ID:** uuid
    ## USER_LABEL:
    [message]
    ## COMPANION_LABEL:
    [message]
    ...

  This format is compatible with split_conversations.py out of the box.
  After running this script, run split_conversations.py on the output file.
"""

import json
import os
import sys
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIG — edit these before running
# ─────────────────────────────────────────────

SOURCE = r"PATH\TO\claude-conversations.json"
OUTPUT = r"PATH\TO\claude-conversations.md"

# Labels used for speaker headings in the output markdown.
# These will appear as "## USER_LABEL:" and "## COMPANION_LABEL:" in the output.
# The analysis agents read these headings to identify who's speaking.
USER_LABEL = "USER"
COMPANION_LABEL = "CLAUDE"  # change to your companion's name if they had one

# Whether to skip conversations with no content (empty exports, deleted messages).
SKIP_EMPTY = True

# ─────────────────────────────────────────────
# SCRIPT — no edits needed below this line
# ─────────────────────────────────────────────

def format_timestamp(iso_str: str) -> str:
    """Convert ISO timestamp to YYYY-MM-DD HH:MM format."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_local = dt.astimezone()
        return dt_local.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_str[:16].replace("T", " ") if iso_str else "unknown"


def extract_message_text(message: dict) -> str:
    """
    Extract plain text from a Claude message object.
    Handles the content array structure: content[*].text
    Falls back to the top-level 'text' field if content is empty.
    """
    # Primary: content array
    content_blocks = message.get("content", [])
    if content_blocks:
        parts = []
        for block in content_blocks:
            block_type = block.get("type", "text")
            if block_type == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
            elif block_type == "tool_use":
                # Tool calls — skip or note them
                tool_name = block.get("name", "tool")
                parts.append(f"[{tool_name}]")
            elif block_type == "tool_result":
                # Tool results — skip
                pass
        return "\n\n".join(parts)

    # Fallback: top-level text field
    return message.get("text", "").strip()


def convert_sender(sender: str) -> str:
    """Map Claude's sender values to our configured labels."""
    if sender == "human":
        return USER_LABEL
    elif sender == "assistant":
        return COMPANION_LABEL
    else:
        return sender.upper()


def main():
    if not os.path.exists(SOURCE):
        print(f"ERROR: Source file not found: {SOURCE}")
        print("Set the SOURCE path at the top of this script.")
        sys.exit(1)

    print(f"Reading {SOURCE} ...")
    with open(SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("ERROR: Expected a JSON array at the top level.")
        print("Claude's export format is an array of conversation objects.")
        sys.exit(1)

    print(f"  Found {len(data)} conversations")

    # Sort by creation date (oldest first)
    def sort_key(conv):
        return conv.get("created_at", "")

    data.sort(key=sort_key)

    output_lines = []
    skipped = 0
    written = 0

    for conv in data:
        uuid = conv.get("uuid", "unknown")
        name = conv.get("name", "").strip() or "Untitled Conversation"
        created_at = conv.get("created_at", "")
        messages = conv.get("chat_messages", [])

        # Filter to messages with actual content
        content_messages = []
        for msg in messages:
            text = extract_message_text(msg)
            if text:
                content_messages.append((msg.get("sender", "unknown"), text, msg.get("created_at", "")))

        if SKIP_EMPTY and not content_messages:
            skipped += 1
            continue

        date_str = format_timestamp(created_at)

        # Conversation header (matches split_conversations.py detection format)
        output_lines.append(f"# {name}\n")
        output_lines.append(f"**Date:** {date_str}\n")
        output_lines.append(f"**Conversation ID:** {uuid}\n")
        output_lines.append("\n")

        for sender, text, _ in content_messages:
            label = convert_sender(sender)
            output_lines.append(f"## {label}:\n")
            output_lines.append(f"{text}\n")
            output_lines.append("\n")

        output_lines.append("\n---\n\n")
        written += 1

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT)), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"  Written: {written} conversations")
    if skipped:
        print(f"  Skipped: {skipped} empty conversations")
    print(f"\nDone. Output written to: {OUTPUT}")
    print(f"\nNext step: run split_conversations.py on this file.")
    print(f"Set SOURCE in split_conversations.py to:\n  {OUTPUT}")


if __name__ == "__main__":
    main()
