"""
Extract selected Codex evidence into companion-portrait style chunks.

Default mode is summaries-first. Raw rollout extraction requires explicit
thread ids so the portrait process stays intentional instead of vacuuming the
whole Codex archive.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CODEX_HOME = Path.home() / ".codex"


def sqlite_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def unix_ms_to_date(value: int | None) -> str:
    if not value:
        return "unknown"
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()


def load_threads(codex_home: Path, thread_ids: list[str] | None) -> list[dict[str, Any]]:
    con = sqlite_ro(codex_home / "state_5.sqlite")
    where = ""
    params: list[Any] = []
    if thread_ids:
        placeholders = ",".join("?" for _ in thread_ids)
        where = f"WHERE t.id IN ({placeholders})"
        params.extend(thread_ids)

    rows = con.execute(
        f"""
        SELECT
          t.id,
          t.title,
          t.rollout_path,
          t.created_at_ms,
          t.updated_at_ms,
          t.cwd,
          t.first_user_message,
          s.raw_memory,
          s.rollout_summary
        FROM threads t
        LEFT JOIN stage1_outputs s ON s.thread_id = t.id
        {where}
        ORDER BY t.updated_at_ms ASC
        """,
        params,
    ).fetchall()
    con.close()

    columns = [
        "thread_id",
        "title",
        "rollout_path",
        "created_at_ms",
        "updated_at_ms",
        "cwd",
        "first_user_message",
        "raw_memory",
        "rollout_summary",
    ]
    return [dict(zip(columns, row)) for row in rows]


def clean_path(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    return Path(path_text.replace("\\\\?\\", ""))


def normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def extract_rollout_messages(path: Path) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        payload = obj.get("payload") or {}
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = normalize_message_content(payload.get("content"))
        if content.strip():
            messages.append({
                "role": role,
                "content": content.strip(),
                "timestamp": obj.get("timestamp", ""),
            })
    return messages


def write_summary_chunk(output: Path, threads: list[dict[str, Any]]) -> None:
    lines = [
        "<!-- CODEX PORTRAIT EVIDENCE CHUNK -->",
        "<!-- Mode: summaries-first -->",
        "<!-- Raw rollout bodies are not included in this chunk. -->",
        "",
        "# Codex Portrait Evidence - Summaries First",
        "",
    ]
    for thread in threads:
        if not thread.get("raw_memory") and not thread.get("rollout_summary"):
            continue
        lines.extend([
            "---",
            "",
            f"## Thread: {thread['title'] or thread['thread_id']}",
            "",
            f"**Thread ID:** `{thread['thread_id']}`",
            f"**Date:** {unix_ms_to_date(thread['updated_at_ms'])}",
            f"**CWD:** `{str(thread.get('cwd') or '').replace('\\\\?\\', '')}`",
            "",
        ])
        if thread.get("rollout_summary"):
            lines.extend(["### Rollout Summary", "", str(thread["rollout_summary"]).strip(), ""])
        if thread.get("raw_memory"):
            lines.extend(["### Raw Memory Digest", "", str(thread["raw_memory"]).strip(), ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def write_raw_thread_chunk(output_dir: Path, thread: dict[str, Any]) -> Path | None:
    rollout_path = clean_path(thread.get("rollout_path"))
    if not rollout_path or not rollout_path.exists():
        return None
    messages = extract_rollout_messages(rollout_path)
    output_path = output_dir / f"codex-thread-{thread['thread_id']}.md"
    lines = [
        "<!-- CODEX PORTRAIT EVIDENCE CHUNK -->",
        "<!-- Mode: selected raw thread -->",
        "",
        f"# Codex Thread Evidence - {thread['thread_id']}",
        "",
        f"**Title:** {thread['title'] or '(untitled)'}",
        f"**Date:** {unix_ms_to_date(thread['updated_at_ms'])}",
        f"**CWD:** `{str(thread.get('cwd') or '').replace('\\\\?\\', '')}`",
        "",
    ]
    for message in messages:
        speaker = "USER" if message["role"] == "user" else "CODEX"
        lines.extend([f"## {speaker}:", "", message["content"], ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", default=str(DEFAULT_CODEX_HOME))
    parser.add_argument("--output-dir", default="evidence")
    parser.add_argument("--mode", choices=["summaries-first", "selected-threads"], default="summaries-first")
    parser.add_argument("--thread-id", action="append", default=[])
    args = parser.parse_args()

    codex_home = Path(args.codex_home)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    threads = load_threads(codex_home, args.thread_id or None)
    if args.mode == "summaries-first":
        output = output_dir / "codex-summaries-first.md"
        write_summary_chunk(output, threads)
        print(f"wrote {output}")
        return

    if not args.thread_id:
        raise SystemExit("--mode selected-threads requires one or more --thread-id values")
    written = [write_raw_thread_chunk(output_dir, thread) for thread in threads]
    for path in written:
        if path:
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
