"""Mask credential-looking values in anything this CLI prints.

Engine messages can quote the request that caused them, a deploy request
carries an SSH password, a download URL can carry a token, and the engine's
own log lines reach the same terminal. A CI log is forever.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

_SECRET_KEYS = r"password|passwd|secret|token|api[_-]?key|private[_-]?key"
# `tokens`, `api_keys`, `passwords`: a plural field holds the same thing.
_SECRET_KEY_RE = re.compile(rf"^(?:{_SECRET_KEYS})s?$", re.I)
# key, then : or =, then a quoted value (escapes included) or a bare one.
# A bare value stops at the usual separators so the rest of a URL or command
# line stays readable.
_SECRET_RE = re.compile(
    rf"""(?P<key>["\']?\b(?:{_SECRET_KEYS})\b["\']?\s*[:=]\s*)
         (?P<value>"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|[^\s&;,"\']+)""",
    re.I | re.X,
)

REDACTED = "<REDACTED>"


def redact(text: object) -> str:
    """Mask secrets in a line of text."""
    return _SECRET_RE.sub(lambda m: f"{m.group('key')}{REDACTED}", str(text))


def redacted_json(value: Any) -> str:
    """The payload as JSON, with secrets masked and structure intact.

    Both shapes are handled: a secret inside a string (an error quoting a
    request) and a secret as a field of its own, where the key and the value
    are separate JSON nodes -- including when the value is an object, which
    is replaced whole rather than walked into.
    """

    def walk(node: Any, key: Optional[str] = None) -> Any:
        if key and _SECRET_KEY_RE.match(key) and node not in (None, ""):
            return REDACTED
        if isinstance(node, dict):
            return {k: walk(v, k) for k, v in node.items()}
        if isinstance(node, list):
            # `key` is not carried into the elements: a list under a plain
            # key holds plain values, and a list under a secret key was
            # already replaced whole above.
            return [walk(v) for v in node]
        return redact(node) if isinstance(node, str) else node

    return json.dumps(walk(value), ensure_ascii=False, indent=2)
