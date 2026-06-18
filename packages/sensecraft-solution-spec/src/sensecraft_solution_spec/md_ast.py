"""Thin wrapper around mistune's AST renderer.

Structure-understanding primitives for guide.md parsing (``markdown_parser``
consumes these; HTML rendering stays on python-markdown).

Key design points:

* A single module-level mistune instance is reused (verified reentrant: each
  ``md(content)`` call builds a fresh ``state`` so there is no cross-call leak).
* ``parse`` registers a ``before_render_hook`` that copies each heading token's
  pre-inline ``text`` field (ATX-stripped raw source of the heading line) into
  ``attrs["raw_text"]``. mistune drops ``text`` from the final AST, so we
  capture it while it is still present.
* mistune's AST carries no source positions, so ``split_by_heading`` re-slices
  the original ``content`` losslessly by matching the AST heading sequence
  against ATX-heading candidate lines using a forward-only cursor. The
  invariant ``''.join(s.raw_md for s in sections) == content`` always holds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

import mistune

# ATX heading candidate matcher. Operates on a single line with trailing
# newline already stripped. group(1) = hashes, group(2) = title text (may still
# carry a trailing closing-# sequence, stripped separately).
_ATX_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
# Trailing ATX closer, e.g. "Title ##" -> "Title".
_ATX_CLOSE_RE = re.compile(r"[ \t]+#+[ \t]*$")
# Code-fence opener (``` or ~~~, indented up to 3 spaces). Used to skip
# fence-internal lines: a fake heading inside a fence is absent from the AST,
# but without this filter its source line could still win the cursor match
# and misplace a section boundary.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _capture_heading_raw(md, state):  # noqa: ANN001 - mistune hook signature
    for tok in state.tokens:
        if tok.get("type") == "heading":
            tok.setdefault("attrs", {})["raw_text"] = tok.get("text")
    return state


def _build_markdown():
    md = mistune.create_markdown(renderer="ast", plugins=["table", "strikethrough"])
    md.before_render_hooks.append(_capture_heading_raw)
    return md


# Module-level reusable instance (reentrant: fresh state per call).
_MD = _build_markdown()


def parse(content: str) -> list[dict]:
    """Parse markdown into mistune's AST token list.

    Each heading token gains ``attrs["raw_text"]`` holding the ATX-stripped
    raw source of the heading (before inline expansion).
    """
    return _MD(content)


@dataclass
class Section:
    heading_text: str | None  # heading raw_text; None for pre-first-heading content
    level: int | None
    raw_md: str  # lossless original slice, including the heading line itself
    start_line: int  # 1-based line number of the heading line in the original
    # content (matching the legacy regex state machine's line_num counter). For
    # the pre-first-heading (leading) section, this is 1 (the content's first line).


def _atx_title(line_text: str) -> str:
    """Extract the comparable title from a candidate ATX line body (group 2)."""
    return _ATX_CLOSE_RE.sub("", line_text).strip()


def iter_unfenced_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield ``(index, line-without-trailing-newline)`` for lines outside
    fenced code blocks.

    Tracks ``\\`\\`\\``` / ``~~~`` fences (up to 3-space indent); a fence closes
    only on a matching marker (same char, >= opener length, nothing but
    whitespace after). Fence delimiter lines themselves are not yielded.
    An unclosed fence swallows the rest of the document — same as the AST view.
    """
    fence_close: tuple[str, int] | None = None  # (char, min_len) of open fence
    for i, raw_line in enumerate(lines):
        stripped = raw_line.rstrip("\r\n")
        fm = _FENCE_RE.match(stripped)
        if fence_close is not None:
            if (
                fm
                and fm.group(1)[0] == fence_close[0]
                and len(fm.group(1)) >= fence_close[1]
                and not stripped[fm.end() :].strip()
            ):
                fence_close = None
            continue
        if fm:
            fence_close = (fm.group(1)[0], len(fm.group(1)))
            continue
        yield i, stripped


def split_by_heading(
    content: str, tokens: list[dict], levels: set[int]
) -> list[Section]:
    """Split ``content`` into sections at headings whose level is in ``levels``.

    Lossless: ``''.join(s.raw_md for s in sections) == content``.

    The AST ``tokens`` provide the authoritative sequence of *real* headings
    (fake headings inside fenced code blocks are absent from the AST). We map
    each such heading onto an ATX candidate line via a forward-only cursor so
    repeated heading texts are consumed in order.
    """
    lines = content.splitlines(keepends=True)

    # Precompute ATX candidate lines: index -> (level, title). Fence-internal
    # lines are skipped, mirroring the AST's view.
    candidates: list[tuple[int, int, str]] = []  # (line_index, level, title)
    for i, stripped in iter_unfenced_lines(lines):
        m = _ATX_RE.match(stripped)
        if m:
            candidates.append((i, len(m.group(1)), _atx_title(m.group(2))))

    # Collect target headings from the AST in document order.
    targets: list[tuple[int, str]] = []  # (level, raw_text)
    for tok in tokens:
        if tok.get("type") != "heading":
            continue
        level = (tok.get("attrs") or {}).get("level")
        if level in levels:
            raw = (tok.get("attrs") or {}).get("raw_text")
            targets.append((level, (raw or "").strip()))

    # Forward-only cursor over candidate lines to find each target's line index.
    heading_line_indices: list[int] = []
    cursor = 0
    for level, raw_text in targets:
        found = -1
        j = cursor
        while j < len(candidates):
            c_line, c_level, c_title = candidates[j]
            if c_level == level and c_title == raw_text:
                found = c_line
                cursor = j + 1
                break
            j += 1
        if found == -1:
            raise ValueError(
                "split_by_heading: could not locate source line for AST heading "
                f"(level={level}, raw_text={raw_text!r}); cursor at candidate "
                f"index {cursor} of {len(candidates)} candidates."
            )
        heading_line_indices.append(found)

    # Build sections by slicing the line table at heading boundaries.
    sections: list[Section] = []

    if not heading_line_indices:
        # No headings matched -> single leading section with all content.
        if content:
            sections.append(
                Section(heading_text=None, level=None, raw_md=content, start_line=1)
            )
        return sections

    # Leading (pre-first-heading) section.
    first_h = heading_line_indices[0]
    if first_h > 0:
        sections.append(
            Section(
                heading_text=None,
                level=None,
                raw_md="".join(lines[:first_h]),
                start_line=1,
            )
        )

    # One section per heading.
    for idx, start in enumerate(heading_line_indices):
        end = (
            heading_line_indices[idx + 1]
            if idx + 1 < len(heading_line_indices)
            else len(lines)
        )
        level, raw_text = targets[idx]
        sections.append(
            Section(
                heading_text=raw_text,
                level=level,
                raw_md="".join(lines[start:end]),
                start_line=start + 1,
            )
        )

    return sections


def extract_images(tokens: list[dict]) -> list[str]:
    """Recursively collect image URLs in document order."""
    urls: list[str] = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
            return
        if not isinstance(node, dict):
            return
        if node.get("type") == "image":
            url = (node.get("attrs") or {}).get("url")
            if url is not None:
                urls.append(url)
        children = node.get("children")
        if children:
            walk(children)

    walk(tokens)
    return urls
