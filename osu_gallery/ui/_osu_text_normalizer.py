"""Discord-collapsed .osu text normalizer.

Restores proper line structure to .osu file content that has been
collapsed by Discord's copy-paste behavior, where newlines are removed.
"""

from __future__ import annotations

import re

SECTION_HEADERS = (
    "[General]",
    "[Editor]",
    "[Metadata]",
    "[Difficulty]",
    "[Events]",
    "[TimingPoints]",
    "[Colours]",
    "[HitObjects]",
)

_SECTION_HEADER_RE = re.compile(
    r"(\[(?:General|Editor|Metadata|Difficulty|Events|TimingPoints|Colours|HitObjects)\])"
)

_HIT_OBJECT_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)"
    r","
    r"(-?\d+(?:\.\d+)?)"
    r","
    r"(\d+)"
    r","
    r"(\d+)"
    r","
    r"(\d+)"
)


def normalize_osu_text(content: str) -> str:
    """Normalize Discord-collapsed .osu text back to proper line-delimited format.

    Discord sometimes removes line breaks when copying code blocks. This function
    detects and restores:
    - Section headers ([General], [HitObjects], etc.) on their own lines
    - Newlines between consecutive hit-object records

    Args:
        content: Raw .osu file content (possibly collapsed into fewer lines).

    Returns:
        Normalized .osu content with proper section headers and hit-object newlines.
        If the content cannot be normalized (no recognizable structure), returns
        the content with only line-ending normalization applied.
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()

    if not content:
        return content

    if _is_properly_formatted(content):
        if any(content == header for header in SECTION_HEADERS):
            return content + "\n"
        return content

    content = _restore_structure(content)
    content = _split_hit_objects(content)

    return content


def _is_properly_formatted(content: str) -> bool:
    """Check if the content has proper line structure.

    A properly formatted .osu file has each section header on its own line,
    the format line on its own line, and hit objects (if present) on
    separate lines.

    Args:
        content: The .osu file content to check.

    Returns:
        True if the content appears to be properly formatted.
    """
    format_match = re.search(r"osu file format v\d+", content)
    if format_match:
        end_idx = format_match.end()
        if end_idx < len(content) and content[end_idx] != "\n":
            return False

    for header in SECTION_HEADERS:
        idx = content.find(header)
        if idx == -1:
            continue
        end_idx = idx + len(header)
        if end_idx >= len(content):
            has_previous_headers = any(
                content.find(h) != -1 and content.find(h) < idx
                for h in SECTION_HEADERS
                if h != header
            )
            if not has_previous_headers:
                return False
            continue
        if content[end_idx] != "\n":
            return False

    hitobjects_idx = content.find("[HitObjects]")
    if hitobjects_idx == -1:
        return True

    remaining = content[hitobjects_idx + len("[HitObjects]\n"):]
    next_section = re.search(r"^\[", remaining, re.MULTILINE)
    objects_part = remaining[:next_section.start()] if next_section else remaining

    for line in objects_part.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue
        matches = list(_HIT_OBJECT_RE.finditer(stripped))
        if len(matches) > 1:
            return False

    return True


def _restore_structure(content: str) -> str:
    """Restore section headers and format line to their own lines.

    Inserts \\n after ``osu file format vN`` and after each section header
    when they are immediately followed by non-newline content.

    Args:
        content: The .osu content.

    Returns:
        Content with proper line structure for headers.
    """
    format_match = re.search(r"osu file format v\d+", content)
    if format_match:
        end = format_match.end()
        if end < len(content) and content[end] != "\n":
            content = content[:end] + "\n" + content[end:]

    def _replace_header(match: re.Match[str]) -> str:
        start = match.start()
        end = match.end()
        header = match.group(1)

        result = "\n" + header if start > 0 and content[start - 1] != "\n" else header

        if end >= len(content) or content[end] != "\n":
            result += "\n"

        return result

    content = _SECTION_HEADER_RE.sub(_replace_header, content)
    return content


def _split_hit_objects(content: str) -> str:
    """Split space-separated hit object records onto separate lines.

    Only processes the [HitObjects] section to avoid matching timing points
    or other numeric data in other sections.

    Args:
        content: The .osu content with hit objects section.

    Returns:
        Content with hit objects split onto separate lines.
    """
    hitobjects_idx = content.find("[HitObjects]")
    if hitobjects_idx == -1:
        return content

    remaining = content[hitobjects_idx + len("[HitObjects]\n"):]
    next_section = re.search(r"^\[", remaining, re.MULTILINE)
    objects_part = remaining[:next_section.start()] if next_section else remaining
    tail = remaining[next_section.start():] if next_section else ""

    objects_part = _split_hit_objects_in_text(objects_part)

    return content[:hitobjects_idx + len("[HitObjects]\n")] + objects_part + tail


def _split_hit_objects_in_text(text: str) -> str:
    """Split space-separated hit object records in a text block.

    Finds all hit object patterns in the text and inserts newlines before
    those that are not already preceded by newlines. Leading whitespace
    (spaces/tabs) between records is replaced by the newline.

    Args:
        text: The text to process (should be the [HitObjects] section content).

    Returns:
        Text with hit objects split onto separate lines.
    """
    result: list[str] = []
    last_end = 0

    for match in _HIT_OBJECT_RE.finditer(text):
        start = match.start()
        if start > 0 and text[start - 1] != "\n":
            leading_start = start
            while leading_start > 0 and text[leading_start - 1] in " \t":
                leading_start -= 1
            result.append(text[last_end:leading_start])
            result.append("\n")
        else:
            result.append(text[last_end:start])
        result.append(match.group(0))
        last_end = match.end()

    result.append(text[last_end:])

    return "".join(result)
