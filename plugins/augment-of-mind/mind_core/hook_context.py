"""Build bounded semantic context for the MIND prompt hook."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

MAX_ASSOCIATION_CONTEXT_CHARACTERS = 6_000
MAX_CURRENT_PROMPT_CHARACTERS = 3_600
MAX_TRANSCRIPT_READ_BYTES = 256_000
MAX_TRANSCRIPT_MESSAGES = 6
MAX_TRANSCRIPT_MESSAGE_CHARACTERS = 900
MAX_LEXICAL_HINTS = 16
MAX_HINT_CHARACTERS = 256

_TOKEN = re.compile(r"\$?[A-Za-z0-9][A-Za-z0-9_$:+.-]*")

def _clip_middle(value: str, maximum: int) -> str:
    text = " ".join(value.split())
    if len(text) <= maximum:
        return text
    marker = " … "
    remaining = maximum - len(marker)
    head = (remaining * 2) // 3
    tail = remaining - head
    return text[:head].rstrip() + marker + text[-tail:].lstrip()


def lexical_hints(text: str) -> list[str]:
    """Retain explicit identity-shaped cues as a second association channel."""

    originals = _TOKEN.findall(text)[:256]
    candidates: list[str] = []
    for original in originals:
        normalized = original.lower().lstrip("$").strip("._:+-")
        if not normalized:
            continue
        if (
            original.startswith("$")
            or "-" in original
            or ":" in original
            or (original.isupper() and len(original) >= 3)
            or any(character.isdigit() for character in original)
        ):
            candidates.append(normalized)

    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate[:MAX_HINT_CHARACTERS].strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
        if len(result) == MAX_LEXICAL_HINTS:
            break
    return result


def _content_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list):
        return ""
    fragments: list[str] = []
    for item in value:
        if isinstance(item, str):
            fragments.append(item)
            continue
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            fragments.append(text)
    return "\n".join(fragment.strip() for fragment in fragments if fragment.strip())


def _message_records(value: object) -> list[tuple[str, str]]:
    """Find user/assistant message text inside a rollout record without fixing its wrapper schema."""

    if isinstance(value, list):
        result: list[tuple[str, str]] = []
        for item in value:
            result.extend(_message_records(item))
        return result
    if not isinstance(value, dict):
        return []

    role = value.get("role")
    if role in {"user", "assistant"}:
        text = _content_text(value.get("content"))
        if text:
            return [(role, text)]

    result: list[tuple[str, str]] = []
    for child in value.values():
        if isinstance(child, (dict, list)):
            result.extend(_message_records(child))
    return result


def _read_tail(path: Path, maximum_bytes: int) -> str:
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        start = max(0, size - maximum_bytes)
        stream.seek(start)
        payload = stream.read(maximum_bytes)
    if start:
        separator = payload.find(b"\n")
        payload = payload[separator + 1 :] if separator >= 0 else b""
    return payload.decode("utf-8", errors="replace")


def recent_transcript_messages(event: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Read a bounded recent conversation window; transcript access is optional."""

    raw_path = event.get("transcript_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return []
    path = Path(raw_path).expanduser()
    if not path.is_file():
        return []
    try:
        text = _read_tail(path, MAX_TRANSCRIPT_READ_BYTES)
    except OSError:
        return []

    messages: list[tuple[str, str]] = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        for role, content in _message_records(record):
            normalized = " ".join(content.split())
            if not normalized:
                continue
            candidate = (role, normalized)
            if not messages or messages[-1] != candidate:
                messages.append(candidate)

    prompt = event.get("prompt")
    current = " ".join(prompt.split()) if isinstance(prompt, str) else ""
    if current:
        messages = [item for item in messages if item[1] != current]
    return messages[-MAX_TRANSCRIPT_MESSAGES:]


def association_context(event: Mapping[str, Any]) -> str:
    """Build one bounded semantic anchor from the current prompt and recent context."""

    prompt = event.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt_missing")

    current = _clip_middle(prompt, MAX_CURRENT_PROMPT_CHARACTERS)
    sections = [f"CURRENT USER PROMPT\n{current}"]

    cwd = event.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        sections.append(f"WORKSPACE\n{_clip_middle(cwd, 320)}")

    recent = recent_transcript_messages(event)
    retained: list[str] = []
    remaining = MAX_ASSOCIATION_CONTEXT_CHARACTERS - sum(
        len(section) + 2 for section in sections
    )
    for role, text in reversed(recent):
        item = f"{role.upper()}\n{_clip_middle(text, MAX_TRANSCRIPT_MESSAGE_CHARACTERS)}"
        cost = len(item) + 2
        if cost > remaining:
            continue
        retained.append(item)
        remaining -= cost
    if retained:
        sections.insert(0, "RECENT CONVERSATION\n" + "\n\n".join(reversed(retained)))

    context = "\n\n".join(sections)
    return _clip_middle(context, MAX_ASSOCIATION_CONTEXT_CHARACTERS)

