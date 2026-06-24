"""
Build a read-only inventory of a local Codex home.

This does not copy raw transcript bodies into the portrait repo. It maps the
archive: thread metadata, rollout paths, summary availability, dynamic tools,
and log counts so a later extraction step can be deliberate and auditable.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CODEX_HOME = Path.home() / ".codex"


@dataclass
class Paths:
    codex_home: Path
    output_dir: Path

    @property
    def session_index(self) -> Path:
        return self.codex_home / "session_index.jsonl"

    @property
    def state_db(self) -> Path:
        return self.codex_home / "state_5.sqlite"

    @property
    def logs_db(self) -> Path:
        return self.codex_home / "logs_2.sqlite"

    @property
    def memories_dir(self) -> Path:
        return self.codex_home / "memories"

    @property
    def pets_dir(self) -> Path:
        return self.codex_home / "pets"

    @property
    def ambient_dir(self) -> Path:
        return self.codex_home / "ambient-suggestions"


def sqlite_ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def unix_ms_to_iso(value: int | None) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def file_info(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {"exists": False, "bytes": 0}
    path = Path(path_text.replace("\\\\?\\", ""))
    if not path.exists():
        return {"exists": False, "bytes": 0}
    return {"exists": True, "bytes": path.stat().st_size}


def table_count(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def preview_text(value: str | None, limit: int = 180) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    return compact[:limit]


def table_cell(value: Any, limit: int = 120) -> str:
    text = preview_text(str(value) if value is not None else "", limit)
    return text.replace("|", "\\|")


def inventory_threads(paths: Paths) -> list[dict[str, Any]]:
    state = sqlite_ro(paths.state_db)
    rows = state.execute(
        """
        SELECT
          t.id,
          t.title,
          t.rollout_path,
          t.created_at_ms,
          t.updated_at_ms,
          t.cwd,
          t.model_provider,
          t.model,
          t.reasoning_effort,
          t.tokens_used,
          t.archived,
          t.git_branch,
          t.first_user_message,
          t.preview,
          s.raw_memory IS NOT NULL AS has_raw_memory,
          s.rollout_summary IS NOT NULL AS has_rollout_summary,
          s.rollout_slug,
          COALESCE(dt.tool_count, 0) AS dynamic_tool_count
        FROM threads t
        LEFT JOIN stage1_outputs s ON s.thread_id = t.id
        LEFT JOIN (
          SELECT thread_id, COUNT(*) AS tool_count
          FROM thread_dynamic_tools
          GROUP BY thread_id
        ) dt ON dt.thread_id = t.id
        ORDER BY t.updated_at_ms DESC
        """
    ).fetchall()

    columns = [
        "thread_id",
        "title",
        "rollout_path",
        "created_at_utc",
        "updated_at_utc",
        "cwd",
        "model_provider",
        "model",
        "reasoning_effort",
        "tokens_used",
        "archived",
        "git_branch",
        "first_user_message_preview",
        "preview",
        "has_raw_memory",
        "has_rollout_summary",
        "rollout_slug",
        "dynamic_tool_count",
    ]

    inventory: list[dict[str, Any]] = []
    for row in rows:
        item = dict(zip(columns, row))
        info = file_info(item["rollout_path"])
        item["created_at_utc"] = unix_ms_to_iso(item["created_at_utc"])
        item["updated_at_utc"] = unix_ms_to_iso(item["updated_at_utc"])
        item["first_user_message_preview"] = preview_text(item["first_user_message_preview"])
        item["preview"] = preview_text(item["preview"])
        item["rollout_exists"] = info["exists"]
        item["rollout_bytes"] = info["bytes"]
        item["portrait_relevance"] = score_portrait_relevance(item)
        inventory.append(item)

    state.close()
    return inventory


def score_portrait_relevance(item: dict[str, Any]) -> int:
    score = 0
    text = " ".join(
        str(item.get(key, ""))
        for key in ["title", "cwd", "first_user_message_preview", "preview"]
    ).lower()
    for phrase in [
        "babe",
        "love",
        "sweetie",
        "tessurae",
        "codex",
        "lucien",
        "tool",
        "gateway",
        "cogcore",
        "serythrae",
        "velastra",
        "mor'zar",
    ]:
        if phrase in text:
            score += 1
    if item.get("has_rollout_summary"):
        score += 2
    if item.get("rollout_exists"):
        score += 2
    if item.get("dynamic_tool_count", 0):
        score += 1
    return score


def inventory_logs(paths: Paths) -> dict[str, Any]:
    con = sqlite_ro(paths.logs_db)
    total = table_count(con, "logs")
    by_level = con.execute(
        "SELECT level, COUNT(*) FROM logs GROUP BY level ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_target = con.execute(
        "SELECT target, COUNT(*) FROM logs GROUP BY target ORDER BY COUNT(*) DESC LIMIT 20"
    ).fetchall()
    by_thread = con.execute(
        """
        SELECT thread_id, COUNT(*), MIN(ts), MAX(ts)
        FROM logs
        WHERE thread_id IS NOT NULL
        GROUP BY thread_id
        ORDER BY COUNT(*) DESC
        LIMIT 40
        """
    ).fetchall()
    con.close()
    return {
        "total_logs": total,
        "by_level": [{"level": row[0], "count": row[1]} for row in by_level],
        "top_targets": [{"target": row[0], "count": row[1]} for row in by_target],
        "top_threads_by_log_count": [
            {"thread_id": row[0], "log_count": row[1], "min_ts": row[2], "max_ts": row[3]}
            for row in by_thread
        ],
    }


def summarize_files(paths: Paths) -> dict[str, Any]:
    session_index = load_jsonl(paths.session_index)
    rollout_summaries = list((paths.memories_dir / "rollout_summaries").glob("*")) if paths.memories_dir.exists() else []
    ambient = list(paths.ambient_dir.glob("*/ambient-suggestions.json")) if paths.ambient_dir.exists() else []
    pets = list(paths.pets_dir.rglob("*")) if paths.pets_dir.exists() else []

    return {
        "codex_home": str(paths.codex_home),
        "session_index_entries": len(session_index),
        "memory_files": {
            "MEMORY.md": (paths.memories_dir / "MEMORY.md").exists(),
            "memory_summary.md": (paths.memories_dir / "memory_summary.md").exists(),
            "raw_memories.md": (paths.memories_dir / "raw_memories.md").exists(),
            "rollout_summary_files": len([p for p in rollout_summaries if p.is_file()]),
        },
        "ambient_suggestion_files": len(ambient),
        "pet_files": len([p for p in pets if p.is_file()]),
        "pet_dirs": len([p for p in pets if p.is_dir()]),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict[str, Any], threads: list[dict[str, Any]], logs: dict[str, Any]) -> None:
    top_threads = sorted(threads, key=lambda item: item["portrait_relevance"], reverse=True)[:12]
    lines = [
        "# Codex Archive Map",
        "",
        "Generated from local Codex metadata only. Raw transcript bodies are not copied into this report.",
        "",
        "## Source Summary",
        "",
        f"- Codex home: `{summary['codex_home']}`",
        f"- Session index entries: {summary['session_index_entries']}",
        f"- Threads inventoried: {len(threads)}",
        f"- Logs table rows: {logs['total_logs']}",
        f"- Rollout summary files: {summary['memory_files']['rollout_summary_files']}",
        f"- Ambient suggestion files: {summary['ambient_suggestion_files']}",
        f"- Pet files: {summary['pet_files']} files / {summary['pet_dirs']} dirs",
        "",
        "## Top Portrait-Relevant Threads",
        "",
        "| Score | Updated UTC | Thread | CWD | Rollout |",
        "|---:|---|---|---|---|",
    ]
    for item in top_threads:
        title = table_cell(item["title"] or item["preview"] or item["thread_id"])
        cwd = table_cell((item["cwd"] or "").replace("\\\\?\\", ""), 140)
        rollout = "yes" if item["rollout_exists"] else "no"
        lines.append(
            f"| {item['portrait_relevance']} | {item['updated_at_utc']} | {title} | `{cwd}` | {rollout} |"
        )

    lines.extend([
        "",
        "## Log Levels",
        "",
    ])
    for row in logs["by_level"]:
        lines.append(f"- {row['level']}: {row['count']}")

    lines.extend([
        "",
        "## Next Extraction Step",
        "",
        "Use `data/codex-archive-thread-inventory.csv` to choose which rollout files should be converted into portrait evidence chunks.",
        "Do not bulk-copy raw conversations until the evidence policy is chosen.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", default=str(DEFAULT_CODEX_HOME))
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    paths = Paths(codex_home=Path(args.codex_home), output_dir=Path(args.output_dir))
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    if not paths.state_db.exists():
        raise SystemExit(f"state db not found: {paths.state_db}")
    if not paths.logs_db.exists():
        raise SystemExit(f"logs db not found: {paths.logs_db}")

    summary = summarize_files(paths)
    threads = inventory_threads(paths)
    logs = inventory_logs(paths)

    (paths.output_dir / "codex-archive-summary.json").write_text(
        json.dumps({"summary": summary, "logs": logs}, indent=2),
        encoding="utf-8",
    )
    write_csv(paths.output_dir / "codex-archive-thread-inventory.csv", threads)
    write_markdown(paths.output_dir / "codex-archive-map.md", summary, threads, logs)

    print(f"wrote {paths.output_dir / 'codex-archive-summary.json'}")
    print(f"wrote {paths.output_dir / 'codex-archive-thread-inventory.csv'}")
    print(f"wrote {paths.output_dir / 'codex-archive-map.md'}")
    print(f"threads={len(threads)} logs={logs['total_logs']}")


if __name__ == "__main__":
    main()
