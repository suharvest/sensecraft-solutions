"""
Multilingual Markdown Parser for Solution Documentation.

This module provides parsing utilities for multilingual markdown format.
Uses separate files (guide.md, guide_zh.md, guide_ja.md, ...) with structure validation.

Format specification:
- Deployment steps use H2 headers with metadata: `## Step N: Title {#step_id type=xxx required=true}`
- Preset sections: `## Preset: Name {#preset_id}` / `## 套餐: 名称 {#preset_id}`
- Sub-sections: `### Prerequisites`, `### Wiring`, `### Troubleshooting`
- Success section starts with `# Deployment Complete` / `# 部署完成`

Language file naming convention:
- guide.md       -> English (default)
- guide_zh.md    -> Chinese
- guide_ja.md    -> Japanese
- guide_fr.md    -> French
- etc.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import markdown

from . import md_ast
from .localized import Localized

logger = logging.getLogger(__name__)


class ParseErrorType(Enum):
    """Types of parsing errors."""

    INVALID_STEP_FORMAT = "invalid_step_format"
    DUPLICATE_STEP_ID = "duplicate_step_id"
    INVALID_STEP_TYPE = "invalid_step_type"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_TARGET_FORMAT = "invalid_target_format"
    PARSE_FAILURE = "parse_failure"
    # Structure validation errors (for separate bilingual files)
    PRESET_COUNT_MISMATCH = "preset_count_mismatch"
    PRESET_ID_MISMATCH = "preset_id_mismatch"
    STEP_COUNT_MISMATCH = "step_count_mismatch"
    STEP_ID_MISMATCH = "step_id_mismatch"
    STEP_TYPE_MISMATCH = "step_type_mismatch"
    STEP_REQUIRED_MISMATCH = "step_required_mismatch"
    STEP_CONFIG_MISMATCH = "step_config_mismatch"


@dataclass
class ParseError:
    """Represents a parsing error with location and suggestion."""

    error_type: ParseErrorType
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        loc = f" (line {self.line_number})" if self.line_number else ""
        sug = f"\n  Suggestion: {self.suggestion}" if self.suggestion else ""
        return f"{self.message}{loc}{sug}"


@dataclass
class ParseWarning:
    """Represents a non-fatal parsing warning."""

    message: str
    line_number: Optional[int] = None


@dataclass
class WiringInfo:
    """Wiring diagram information extracted from markdown."""

    image: Optional[str] = None
    steps: Localized[list[str]] = field(default_factory=lambda: Localized())


@dataclass
class TargetInfo:
    """Target information for docker_deploy type devices."""

    id: str
    name: Localized[str] = field(default_factory=lambda: Localized())
    config_file: Optional[str] = None
    default: bool = False
    target_type: str = "local"  # "local" or "remote"
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # Plain text for selector
    description_html: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML for content area
    troubleshoot: Localized[str] = field(default_factory=lambda: Localized())  # HTML
    post_deploy: Localized[str] = field(default_factory=lambda: Localized())  # HTML
    wiring: Optional["WiringInfo"] = None
    # Optional device-target separation fields
    device: Optional[str] = None  # e.g. "rk3576" / "rk3588"
    device_name: Optional[str] = None  # Human-readable device label
    method: Optional[str] = None  # Deployment method, mirrors target_type


@dataclass
class ModeInfo:
    """Mode information for verify type steps with multi-mode switching."""

    id: str
    name: Localized[str] = field(default_factory=lambda: Localized())
    config_file: Optional[str] = None
    default: bool = False
    description: Localized[str] = field(default_factory=lambda: Localized())
    description_html: Localized[str] = field(default_factory=lambda: Localized())
    troubleshoot: Localized[str] = field(default_factory=lambda: Localized())


@dataclass
class SectionContent:
    """Section content compatible with existing frontend structure."""

    title: Localized[str] = field(default_factory=lambda: Localized())
    subtitle: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # Plain text extracted from first paragraph (for header subtitle)
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    troubleshoot: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    post_deploy: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    wiring: Optional[WiringInfo] = None


@dataclass
class DeploymentStep:
    """A parsed deployment step from the markdown."""

    id: str
    title: Localized[str] = field(default_factory=lambda: Localized())
    type: str = ""
    required: bool = True
    config_file: Optional[str] = None
    section: SectionContent = field(default_factory=SectionContent)
    targets: list[TargetInfo] = field(default_factory=list)
    modes: Optional[list["ModeInfo"]] = None
    # When true, the step's effective category is "verify" regardless of
    # its deployer type. Lets a `type=manual` step that genuinely IS the
    # verification (e.g. "Try the voice assistant", "Demo & Testing") be
    # counted as the preset's verify step instead of forcing a redundant
    # web_dashboard step alongside it. Set via `verify=true` in the
    # step header attributes: `{#demo type=manual verify=true}`.
    verify_override: bool = False
    # ID of an upstream step whose selectedTarget this step should follow
    # (auto-select the same local/remote method on initial render and stay
    # in sync when the upstream is switched). Used when multiple deploy
    # steps target the same machine — avoids re-picking local/remote on
    # every step. Set via `target_inherit_from=<step_id>` in step attrs.
    target_inherit_from: Optional[str] = None


@dataclass
class PresetGuide:
    """A parsed preset guide section."""

    id: str
    name: Localized[str] = field(default_factory=lambda: Localized())
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    steps: list[DeploymentStep] = field(default_factory=list)
    completion: Optional["SuccessContent"] = None
    is_default: bool = False


@dataclass
class SuccessContent:
    """Parsed success/completion content."""

    content: Localized[str] = field(default_factory=lambda: Localized())  # HTML content


@dataclass
class ParseResult:
    """Result of parsing a deployment guide markdown file."""

    overview: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    presets: list[PresetGuide] = field(default_factory=list)
    steps: list[DeploymentStep] = field(
        default_factory=list
    )  # Steps without preset context
    success: Optional[SuccessContent] = None
    warnings: list[ParseWarning] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class StructureValidationResult:
    """Result of validating structure consistency between EN and ZH guide files."""

    valid: bool = True
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    en_presets: list[str] = field(default_factory=list)  # List of preset IDs in EN
    zh_presets: list[str] = field(default_factory=list)  # List of preset IDs in ZH
    en_steps_by_preset: dict = field(
        default_factory=dict
    )  # preset_id -> list of step IDs
    zh_steps_by_preset: dict = field(default_factory=dict)


# Valid deployment types — built dynamically from the deployer registry.
# "docker_deploy" is a meta-type (not a deployer) but valid in guide.md.
#
# The set of concrete deployer types is engine-specific knowledge, so this
# package does not hard-code it. The host engine injects a provider via
# ``register_step_type_provider`` at import time. When no provider is
# registered (parser used standalone), only the meta-type
# ``docker_deploy`` is known. This package never imports the engine.
_STEP_TYPE_PROVIDER = None


def register_step_type_provider(provider):
    """Register a callable returning the set of valid concrete step types.

    The host engine calls this so guide.md ``type=`` values can be validated
    against the live deployer registry without this package importing the
    engine. ``"docker_deploy"`` (a meta-type, not a deployer) is always added
    on top of whatever the provider returns.
    """
    global _STEP_TYPE_PROVIDER
    _STEP_TYPE_PROVIDER = provider


def _get_valid_step_types():
    if _STEP_TYPE_PROVIDER is not None:
        return set(_STEP_TYPE_PROVIDER()) | {"docker_deploy"}
    # Standalone (no host engine registered): only the meta-type is known.
    # Concrete deployer types are injected by the host via
    # ``register_step_type_provider`` (engine) or from ``capabilities.json``
    # (open-source validation flow). This package never imports the engine.
    return {"docker_deploy"}


# Regex patterns for guide.md heading keywords.
# Canonical keyword list: docs/guide-heading-keywords.md
# When adding keywords here, update that doc AND the skill templates.
STEP_HEADER_PATTERN = re.compile(
    # EN: "## Step 1: Name {#id ...}"  ZH: "## 步骤 1: 名称 {#id ...}"
    r"^##\s+(?:Step\s+\d+:\s*|步骤\s*\d+[：:]\s*)?(.+?)\s*\{#(\w+)([^}]*)\}\s*$",
    re.IGNORECASE,
)
PRESET_HEADER_PATTERN = re.compile(
    # EN: "## Preset: Name {#id}"
    r"^##\s+Preset:\s*(.+?)\s*\{#(\w+)\}\s*$",
    re.IGNORECASE,
)
PRESET_HEADER_ZH_PATTERN = re.compile(
    # ZH: "## 套餐: 名称 {#id}"
    r"^##\s+套餐[：:]\s*(.+?)\s*\{#(\w+)\}\s*$",
    re.IGNORECASE,
)
TARGET_HEADER_PATTERN = re.compile(
    # EN: "### Target: Name {#id ...}" or "### Target {#id ...}" (no name)
    # ZH: "### 部署目标: 名称 {#id ...}" or "### 部署目标 {#id ...}" (no name)
    #
    # Name is optional — frontend resolves display name from i18n based on
    # `type=local`/`type=remote` + `device_name=` (see i18n.deploy.methodLabels).
    # When omitted, the parser captures an empty string for group(1).
    r"^###\s+(?:Target|部署目标)(?:[：:]?\s*(.*?))?\s*\{#(\w+)([^}]*)\}\s*$",
    re.IGNORECASE,
)
MODE_HEADER_PATTERN = re.compile(
    # EN: "### Mode: Name {#id ...}"  ZH: "### 模式: 名称 {#id ...}"
    r"^###\s+(?:Mode|模式)[：:]?\s*(.+?)\s*\{#(\w+)([^}]*)\}\s*$",
    re.IGNORECASE,
)
SUCCESS_HEADER_PATTERN = re.compile(
    # EN: "# Deployment Complete"  ZH: "# 部署完成"
    r"^#\s+(Deployment\s+Complete|部署完成)\s*$",
    re.IGNORECASE,
)
SUBSECTION_PATTERNS = {
    # EN: "### Prerequisites"  ZH: "### 前置条件"
    "prerequisites": re.compile(r"^###\s+(Prerequisites|前置条件)\s*$", re.IGNORECASE),
    # EN: "### Wiring"  ZH: "### 接线"
    "wiring": re.compile(r"^###\s+(Wiring|接线)\s*$", re.IGNORECASE),
    # EN: "### Troubleshooting"  ZH: "### 故障排查" / "### 故障排除"
    "troubleshoot": re.compile(
        r"^###\s+(Troubleshooting|故障排查|故障排除)\s*$", re.IGNORECASE
    ),
    # EN: "### Deployment Complete"  ZH: "### 部署完成"
    "post_deploy": re.compile(
        r"^###\s+(Deployment\s+Complete|部署完成)\s*$", re.IGNORECASE
    ),
}
ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.+)$")


def parse_step_attributes(attr_string: str) -> dict:
    """Parse step attributes from the header metadata string.

    Example: "type=docker_deploy required=true config=devices/docker.yaml"
    Returns: {"type": "docker_deploy", "required": True, "config": "devices/docker.yaml"}
    """
    attrs = {}
    # Match key=value pairs, where value can be quoted or unquoted
    pattern = re.compile(r'(\w+)=(?:"([^"]+)"|([^\s]+))')
    for match in pattern.finditer(attr_string):
        key = match.group(1)
        value = match.group(2) if match.group(2) else match.group(3)
        # Convert boolean strings
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        attrs[key] = value
    return attrs


UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.+)$")
TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|\s*$")
# A markdown table delimiter row: |---|:--:|---| etc. (only -, :, |, spaces).
TABLE_DELIM_PATTERN = re.compile(r"^\|[\s:\-|]+\|\s*$")


def _split_table_row(line: str) -> list[str]:
    """Split a ``| a | b | c |`` row into trimmed cell strings (markers kept)."""
    inner = line.strip()
    # Drop the leading/trailing pipe before splitting so empty edge cells
    # aren't produced.
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def extract_wiring_for_lang(content: str) -> tuple[Optional[str], list[str]]:
    """Extract wiring image and steps from content for a single language.

    Stage-2 (AST-migration) behavior: steps are collected from ordered lists,
    unordered lists AND tables, in document order. Previously only ordered
    lists were collected; unordered lists and tables were silently dropped.

    Collection rules (see project guide / stage-2 spec):

    * **Ordered list** item -> one step. Text is the raw markdown line after the
      ``N.`` marker, preserving inline markup (``**bold**``, ``code``, links).
      This is byte-identical to the legacy ordered-list extraction so existing
      golden snapshots for ordered-only wiring do not change.
    * **Unordered list** item -> one step (same raw-line preservation).
    * **Nested sub-list** items are merged into their parent step's text,
      joined with ``"; "`` (parent and first child joined with a single space).
    * **Table** body row -> one step; cells joined with ``" — "``. The header
      row and the ``|---|`` delimiter row are skipped.
    * **Block quotes** (``> ...``) are excluded by design: in the real corpus
      these are ``> **Note:** ...`` warnings, not steps.
    * Content inside fenced code blocks is ignored (a ``1.`` inside a fence is
      not a step).

    Raw-line extraction (not ``md_ast.flatten_text``) is used deliberately:
    flatten_text drops ``**``/backtick markers, but wiring step text must keep
    them for the frontend to render. The AST (``md_ast.parse``) is consulted to
    detect the presence of unordered lists / tables in document order; the
    actual step text is sliced from the raw markdown lines.

    Args:
        content: Markdown content for one language

    Returns:
        Tuple of (image_path, steps_list)
    """
    image = None

    # Extract image (first image in document order, via AST)
    imgs = md_ast.extract_images(md_ast.parse(content))
    if imgs:
        image = imgs[0]

    steps = _extract_wiring_steps(content)
    return image, steps


def _extract_wiring_steps(content: str) -> list[str]:
    """Collect wiring step strings from raw markdown lines, in document order.

    Fence-aware (skips fenced code blocks). Preserves inline markdown markers
    by working from the raw source lines rather than the flattened AST text.
    """
    lines = content.split("\n")
    steps: list[str] = []
    i = 0
    n = len(lines)
    # Fence-aware filter shared with md_ast (skips ``` / ~~~ blocks and the
    # fence delimiter lines themselves).
    unfenced_idx = {idx for idx, _ in md_ast.iter_unfenced_lines(lines)}

    while i < n:
        if i not in unfenced_idx:
            i += 1
            continue
        raw = lines[i]
        stripped = raw.strip()

        indent = len(raw) - len(raw.lstrip())

        # Top-level (non-indented) ordered or unordered list item -> a step.
        # Nested (indented) list items belong to the preceding step and are
        # merged below.
        ordered = ORDERED_LIST_PATTERN.match(stripped)
        unordered = UNORDERED_LIST_PATTERN.match(stripped)
        if indent == 0 and (ordered or unordered):
            text = (ordered or unordered).group(1)
            nested: list[str] = []
            j = i + 1
            while j < n:
                nxt = lines[j]
                nxt_stripped = nxt.strip()
                if not nxt_stripped:
                    # Blank line: peek ahead — a following indented list item
                    # keeps the nested block open; otherwise stop.
                    k = j + 1
                    while k < n and not lines[k].strip():
                        k += 1
                    if k < n:
                        k_indent = len(lines[k]) - len(lines[k].lstrip())
                        k_stripped = lines[k].strip()
                        if k_indent > 0 and (
                            ORDERED_LIST_PATTERN.match(k_stripped)
                            or UNORDERED_LIST_PATTERN.match(k_stripped)
                        ):
                            j = k
                            continue
                    break
                nxt_indent = len(nxt) - len(nxt.lstrip())
                sub_ordered = ORDERED_LIST_PATTERN.match(nxt_stripped)
                sub_unordered = UNORDERED_LIST_PATTERN.match(nxt_stripped)
                if nxt_indent > 0 and (sub_ordered or sub_unordered):
                    nested.append((sub_ordered or sub_unordered).group(1))
                    j += 1
                    continue
                break
            if nested:
                text = text + " " + "; ".join(nested)
            steps.append(text)
            i = j
            continue

        # Table: a header row followed by a delimiter row, then body rows.
        if TABLE_ROW_PATTERN.match(stripped):
            # Need a delimiter row on the next non-... line to qualify as table.
            if i + 1 < n and TABLE_DELIM_PATTERN.match(lines[i + 1].strip()):
                j = i + 2  # skip header + delimiter
                while j < n and TABLE_ROW_PATTERN.match(lines[j].strip()):
                    cells = _split_table_row(lines[j])
                    steps.append(" — ".join(cells))
                    j += 1
                i = j
                continue

        i += 1

    return steps


def extract_wiring(content: str, content_zh: str = "") -> Optional[WiringInfo]:
    """Extract wiring information from content (legacy bilingual interface).

    Args:
        content: English content
        content_zh: Chinese content (optional)

    Returns:
        WiringInfo with Localized steps, or None if no wiring content
    """
    image, steps_en = extract_wiring_for_lang(content)

    if not image and not steps_en:
        return None

    wiring = WiringInfo(image=image, steps=Localized({"en": steps_en}))

    # Extract Chinese steps if provided
    if content_zh:
        _, steps_zh = extract_wiring_for_lang(content_zh)
        if steps_zh:
            wiring.steps.set("zh", steps_zh)

    return wiring


def extract_wiring_multilang(lang_contents: Dict[str, str]) -> Optional[WiringInfo]:
    """Extract wiring information from multiple language contents.

    Args:
        lang_contents: Dict mapping language code to content

    Returns:
        WiringInfo with Localized steps for all languages
    """
    # Use first available content to get image
    image = None
    all_steps: Dict[str, list[str]] = {}

    for lang, content in lang_contents.items():
        lang_image, lang_steps = extract_wiring_for_lang(content)
        if lang_image and image is None:
            image = lang_image
        if lang_steps:
            all_steps[lang] = lang_steps

    if not image and not all_steps:
        return None

    return WiringInfo(image=image, steps=Localized(all_steps))


def md_to_html(content: str) -> str:
    """Convert markdown content to HTML."""
    if not content.strip():
        return ""
    return markdown.markdown(content, extensions=["tables", "fenced_code", "nl2br"])


def extract_subtitle(raw_markdown: str) -> str:
    """Extract the first paragraph of plain text from raw markdown.

    Convenience wrapper around :func:`extract_subtitle_and_strip` for
    callers that only need the subtitle text.
    """
    subtitle, _ = extract_subtitle_and_strip(raw_markdown)
    return subtitle


def extract_subtitle_and_strip(raw_markdown: str) -> tuple[str, str]:
    """Extract the first prose paragraph as a subtitle AND return the
    markdown content with that paragraph removed.

    Step renderers show the subtitle in the collapsed-section header and
    the rest of the main content as the expanded body. Without this
    stripping the first paragraph gets rendered twice (once as subtitle,
    once at the top of the body), which users have reported as confusing
    duplication on docker_deploy / robot_inspect / manual steps.

    Returns ``("", raw_markdown)`` when no prose paragraph is found
    (e.g. the step body only has images/lists/tables).
    """
    lines = raw_markdown.split("\n")

    # Locate the first prose paragraph: a non-blank line that isn't a
    # heading / list / table / image. Collect every subsequent non-blank
    # line until the paragraph ends at a blank line or EOF.
    para_start = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("![", "#", "|", "- ", "* ", "> ")) or re.match(
            r"^\d+\.", stripped
        ):
            continue
        para_start = i
        break

    if para_start < 0:
        return "", raw_markdown

    para_end = para_start
    while para_end < len(lines) and lines[para_end].strip() != "":
        para_end += 1

    paragraph = " ".join(line.strip() for line in lines[para_start:para_end])
    # Strip inline markdown: [text](url) → text, **bold** → bold, `code` → code
    subtitle = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", paragraph)
    subtitle = re.sub(r"[*_`]+", "", subtitle).strip()

    if not subtitle:
        return "", raw_markdown

    # Build the remaining markdown without the subtitle paragraph. Drop
    # the leading blank lines so the rendered description doesn't open
    # with empty whitespace.
    remaining_lines = lines[:para_start] + lines[para_end:]
    while remaining_lines and not remaining_lines[0].strip():
        remaining_lines.pop(0)
    return subtitle, "\n".join(remaining_lines)


def _match_subsection_name(heading_text: str) -> Optional[str]:
    """Return the subsection bucket name for a ``### Heading`` raw text, or None.

    ``heading_text`` is the AST raw_text (ATX hashes already stripped). The
    SUBSECTION_PATTERNS expect a full ``### ...`` line, so we re-prefix.
    """
    line = f"### {heading_text}"
    for section_name, pattern in SUBSECTION_PATTERNS.items():
        if pattern.match(line):
            return section_name
    return None


def parse_subsections(content: str) -> dict[str, str]:
    """Parse subsections (Prerequisites, Wiring, Troubleshooting) from step content.

    Returns dict with keys: 'main', 'prerequisites', 'wiring', 'troubleshoot'

    AST-based: splits on real ``###`` headings (fence-aware via mistune, so a
    ``### Wiring`` inside a fenced code block is NOT a boundary — fixed by AST
    migration). Only the 4 SUBSECTION_PATTERNS headings switch buckets; other
    ``###`` headings are accumulated as ordinary content into the current bucket.
    Content from the first Target/Mode heading onward is discarded.
    """
    result = {
        "main": "",
        "prerequisites": "",
        "wiring": "",
        "troubleshoot": "",
        "post_deploy": "",
    }

    tokens = md_ast.parse(content)
    sections = md_ast.split_by_heading(content, tokens, levels={3})

    section_content: dict[str, list[str]] = {k: [] for k in result}
    current_section = "main"

    for section in sections:
        heading = section.heading_text

        # Target/Mode heading => stop accumulating, discard the rest.
        if heading is not None and (
            TARGET_HEADER_PATTERN.match(f"### {heading}")
            or MODE_HEADER_PATTERN.match(f"### {heading}")
        ):
            break

        if heading is None:
            # Pre-first-heading (leading) content -> current bucket ('main').
            section_content[current_section].append(section.raw_md)
            continue

        bucket = _match_subsection_name(heading)
        if bucket is not None:
            # A recognized subsection header: switch buckets, drop the header
            # line itself, keep only the body.
            current_section = bucket
            body = _strip_leading_heading_line(section.raw_md)
            if body:
                section_content[current_section].append(body)
        else:
            # An unrecognized ### heading is ordinary content (old behavior
            # accumulated the header line + body into the current bucket).
            section_content[current_section].append(section.raw_md)

    for key, parts in section_content.items():
        result[key] = "".join(parts).strip()

    return result


def _strip_leading_heading_line(raw_md: str) -> str:
    """Drop the leading ``###`` heading line from a section's raw_md, keep the body."""
    newline = raw_md.find("\n")
    if newline == -1:
        return ""
    return raw_md[newline + 1 :]


def parse_deployment_step(
    header_line: str, content_en: str, content_zh: str, line_number: int
) -> tuple[Optional[DeploymentStep], list[ParseError], list[ParseWarning]]:
    """Parse a single deployment step from header and content (legacy bilingual).

    Returns (step, errors, warnings).
    """
    errors = []
    warnings = []

    # Parse header
    match = STEP_HEADER_PATTERN.match(header_line.strip())
    if not match:
        errors.append(
            ParseError(
                error_type=ParseErrorType.INVALID_STEP_FORMAT,
                message=f"Invalid step header format: {header_line}",
                line_number=line_number,
                suggestion="Use format: ## Step N: Title {#step_id type=xxx required=true}",
            )
        )
        return None, errors, warnings

    title = match.group(1).strip()
    step_id = match.group(2)
    attrs_str = match.group(3)
    attrs = parse_step_attributes(attrs_str)

    # Validate type
    step_type = attrs.get("type", "")
    if not step_type:
        errors.append(
            ParseError(
                error_type=ParseErrorType.MISSING_REQUIRED_FIELD,
                message=f"Step '{step_id}' missing required 'type' attribute",
                line_number=line_number,
                suggestion=f"Add type=xxx where xxx is one of: {', '.join(sorted(_get_valid_step_types()))}",
            )
        )
        return None, errors, warnings

    if step_type not in _get_valid_step_types():
        errors.append(
            ParseError(
                error_type=ParseErrorType.INVALID_STEP_TYPE,
                message=f"Invalid step type '{step_type}' for step '{step_id}'",
                line_number=line_number,
                suggestion=f"Valid types: {', '.join(sorted(_get_valid_step_types()))}",
            )
        )
        return None, errors, warnings

    # Parse content subsections
    subsections_en = parse_subsections(content_en)
    subsections_zh = parse_subsections(content_zh)

    # Check for translation warning
    if not content_zh.strip():
        warnings.append(
            ParseWarning(
                message=f"Step '{step_id}' missing Chinese translation",
                line_number=line_number,
            )
        )

    # Build section content with Localized fields. The subtitle is the
    # first prose paragraph of `main`; we strip it from the body markdown
    # so it isn't rendered twice (once as the collapsed-card subtitle and
    # once at the top of the expanded body).
    en_subtitle, en_main_stripped = extract_subtitle_and_strip(subsections_en["main"])
    section = SectionContent(
        title=Localized({"en": title}),
        subtitle=Localized({"en": en_subtitle} if en_subtitle else {}),
        description=Localized(
            {
                "en": md_to_html(en_main_stripped),
            }
        ),
        troubleshoot=Localized(
            {
                "en": md_to_html(subsections_en.get("troubleshoot", "")),
            }
        ),
        post_deploy=Localized(
            {
                "en": md_to_html(subsections_en.get("post_deploy", "")),
            }
        ),
    )

    # Add Chinese content if available
    if subsections_zh.get("main"):
        zh_subtitle, zh_main_stripped = extract_subtitle_and_strip(
            subsections_zh["main"]
        )
        section.description.set("zh", md_to_html(zh_main_stripped))
        if zh_subtitle:
            section.subtitle.set("zh", zh_subtitle)
    if subsections_zh.get("troubleshoot"):
        section.troubleshoot.set("zh", md_to_html(subsections_zh["troubleshoot"]))
    if subsections_zh.get("post_deploy"):
        section.post_deploy.set("zh", md_to_html(subsections_zh["post_deploy"]))

    # Extract wiring if present
    if subsections_en.get("wiring"):
        section.wiring = extract_wiring(
            subsections_en["wiring"], subsections_zh.get("wiring", "")
        )

    step = DeploymentStep(
        id=step_id,
        title=Localized({"en": title}),
        type=step_type,
        required=attrs.get("required", True),
        config_file=attrs.get("config"),
        section=section,
        verify_override=bool(attrs.get("verify", False)),
        target_inherit_from=(attrs.get("target_inherit_from") or None),
    )

    # Parse targets (for docker_deploy and recamera_cpp types)
    if step_type in ("docker_deploy", "recamera_cpp"):
        targets = parse_targets(content_en, content_zh)
        if targets:
            step.targets = targets

    # Parse modes (any step type can have modes for multi-mode switching)
    modes = parse_modes(content_en, content_zh)
    if modes:
        step.modes = modes

    return step, errors, warnings


def _parse_target_content(
    content_lines: list[str],
) -> tuple[str, list[str], Optional[str], str, str]:
    """Parse target content into description, wiring steps, wiring image, troubleshoot, and post_deploy.

    Returns: (description, wiring_steps, wiring_image, troubleshoot, post_deploy)
    """
    # Join lines and use parse_subsections for consistent parsing
    content = "\n".join(content_lines)

    # Truncate at separator or next target
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped == "---" or TARGET_HEADER_PATTERN.match(stripped):
            content = "\n".join(content_lines[:i])
            break

    subsections = parse_subsections(content)

    # Extract wiring info. Reuse extract_wiring_for_lang so target wiring
    # benefits from the same stage-2 enhancement (ordered/unordered lists,
    # nested merge, tables; block quotes excluded).
    wiring_steps = []
    wiring_image = None
    wiring_content = subsections.get("wiring", "")
    if wiring_content:
        wiring_image, wiring_steps = extract_wiring_for_lang(wiring_content)

    # Main content is description
    description = subsections.get("main", "").strip()

    # Troubleshoot content (as markdown, will be converted to HTML later)
    troubleshoot = subsections.get("troubleshoot", "").strip()

    # Post-deploy content (as markdown, will be converted to HTML later)
    post_deploy = subsections.get("post_deploy", "").strip()

    return description, wiring_steps, wiring_image, troubleshoot, post_deploy


def _parse_targets_single_lang(content: str, lang: str) -> list[TargetInfo]:
    """Parse targets from single-language content.

    Args:
        content: Markdown content for one language
        lang: Language code

    Returns:
        List of TargetInfo with single-language Localized fields
    """
    targets = []

    # AST-based split on real ``###`` headings. The legacy state machine split
    # ONLY on ``### Target`` headings and accumulated everything in between —
    # including the target's *nested* ``### Wiring`` / ``### Troubleshooting`` /
    # ``### Deployment Complete`` subsections — as that target's body. The
    # mistune splitter, however, treats every level-3 heading as a sibling
    # boundary. So we group sections: a ``### Target`` heading opens a target,
    # and all following non-Target sections (the nested subsections, which the
    # splitter has hoisted to siblings) belong to it until the next ``### Target``
    # heading. The aggregated body (each section's verbatim raw_md, headings
    # included) is fed to _parse_target_content, which re-splits it via
    # parse_subsections to recover wiring/troubleshoot/post_deploy.
    tokens = md_ast.parse(content)
    sections = md_ast.split_by_heading(content, tokens, levels={3})

    groups: list[tuple[re.Match, list[str]]] = []
    for sec in sections:
        heading = sec.heading_text
        match = (
            TARGET_HEADER_PATTERN.match(f"### {heading}")
            if heading is not None
            else None
        )
        if match:
            # Start a new target group; its body begins with this section's
            # post-heading lines.
            groups.append((match, [_strip_leading_heading_line(sec.raw_md)]))
        elif groups:
            # Non-Target section after a target heading -> nested subsection
            # belonging to the current target; keep verbatim (heading + body)
            # so parse_subsections can re-classify it.
            groups[-1][1].append(sec.raw_md)
        # Sections before the first ``### Target`` heading are ignored (legacy
        # accumulated nothing into current_content until a target opened).

    for match, raw_parts in groups:
        target_name = match.group(1).strip()
        target_id = match.group(2)
        attrs = parse_step_attributes(match.group(3))
        # Reassemble the target body as the legacy per-line accumulation would
        # have: the post-heading lines of the target section followed by each
        # nested subsection's verbatim slice. splitlines() drops the trailing
        # empty element that a keepends slice would otherwise produce.
        content_lines = "".join(raw_parts).splitlines()

        desc, wiring_steps, wiring_image, troubleshoot, post_deploy = (
            _parse_target_content(content_lines)
        )
        wiring = None
        if wiring_image or wiring_steps:
            wiring = WiringInfo(
                image=wiring_image,
                steps=Localized({lang: wiring_steps}),
            )
        target = TargetInfo(
            id=target_id,
            name=Localized({lang: target_name}),
            config_file=attrs.get("config"),
            default=attrs.get("default", False),
            target_type=attrs.get("type", "local"),
            description=Localized({lang: desc.strip() if desc else ""}),
            description_html=Localized({lang: md_to_html(desc) if desc else ""}),
            wiring=wiring,
            troubleshoot=Localized(
                {lang: md_to_html(troubleshoot) if troubleshoot else ""}
            ),
            post_deploy=Localized(
                {lang: md_to_html(post_deploy) if post_deploy else ""}
            ),
            device=attrs.get("device"),
            device_name=attrs.get("device_name"),
            method=attrs.get("type"),
        )
        targets.append(target)

    return targets


def parse_targets(content_en: str, content_zh: str) -> list[TargetInfo]:
    """Parse target sections from step content (legacy bilingual interface).

    Target format: ### Target: Name {#id config=xxx default=true}
    Content below each target header is the description + wiring steps.
    """
    # Parse English targets
    targets = _parse_targets_single_lang(content_en, "en")

    # Parse Chinese content and merge translations
    if content_zh and targets:
        zh_targets = _parse_targets_single_lang(content_zh, "zh")

        # Create a lookup by ID
        zh_by_id = {t.id: t for t in zh_targets}

        # Merge Chinese into English targets
        for target in targets:
            zh_target = zh_by_id.get(target.id)
            if zh_target:
                # Merge name
                target.name.set("zh", zh_target.name.get("zh"))
                # Merge description
                target.description.set("zh", zh_target.description.get("zh"))
                target.description_html.set("zh", zh_target.description_html.get("zh"))
                # Merge troubleshoot
                target.troubleshoot.set("zh", zh_target.troubleshoot.get("zh"))
                # Merge post_deploy
                target.post_deploy.set("zh", zh_target.post_deploy.get("zh"))
                # Merge wiring steps
                if target.wiring and zh_target.wiring:
                    target.wiring.steps.set("zh", zh_target.wiring.steps.get("zh"))

    return targets


def _parse_modes_single_lang(content: str, lang: str) -> list[ModeInfo]:
    """Parse modes from single-language content."""
    modes = []
    lines = content.split("\n")
    current_mode_id = None
    current_mode_name = ""
    current_attrs = {}
    current_content: list[str] = []

    for line in lines:
        stripped = line.strip()
        if TARGET_HEADER_PATTERN.match(stripped):
            break
        match = MODE_HEADER_PATTERN.match(stripped)
        if match:
            if current_mode_id:
                modes.append(
                    _build_mode(
                        current_mode_id,
                        current_mode_name,
                        current_attrs,
                        current_content,
                        lang,
                    )
                )
            current_mode_name = match.group(1).strip()
            current_mode_id = match.group(2)
            current_attrs = parse_step_attributes(match.group(3))
            current_content = []
        else:
            if current_mode_id:
                current_content.append(line)

    if current_mode_id:
        modes.append(
            _build_mode(
                current_mode_id, current_mode_name, current_attrs, current_content, lang
            )
        )

    return modes


def _build_mode(mode_id, name, attrs, content_lines, lang):
    """Build a ModeInfo from parsed content."""
    content = "\n".join(content_lines)
    subsections = parse_subsections(content)
    description = subsections.get("main", "").strip()
    troubleshoot = subsections.get("troubleshoot", "").strip()

    return ModeInfo(
        id=mode_id,
        name=Localized({lang: name}),
        config_file=attrs.get("config"),
        default=attrs.get("default", False),
        description=Localized({lang: description}),
        description_html=Localized(
            {lang: md_to_html(description) if description else ""}
        ),
        troubleshoot=Localized(
            {lang: md_to_html(troubleshoot) if troubleshoot else ""}
        ),
    )


def parse_modes(content_en: str, content_zh: str) -> list[ModeInfo]:
    """Parse mode sections from step content (bilingual)."""
    modes = _parse_modes_single_lang(content_en, "en")

    if content_zh and modes:
        zh_modes = _parse_modes_single_lang(content_zh, "zh")
        zh_by_id = {m.id: m for m in zh_modes}
        for mode in modes:
            zh_mode = zh_by_id.get(mode.id)
            if zh_mode:
                mode.name.set("zh", zh_mode.name.get("zh"))
                mode.description.set("zh", zh_mode.description.get("zh"))
                mode.description_html.set("zh", zh_mode.description_html.get("zh"))
                mode.troubleshoot.set("zh", zh_mode.troubleshoot.get("zh"))

    return modes


def parse_single_language_guide(content: str, lang: str = "en") -> ParseResult:
    """Parse a single-language guide file (no language markers expected).

    This is used for parsing separate EN and ZH files.

    Never raises: the parse layer models failure as ``ParseResult.errors``
    entries (the AST splitter can raise on pathological input, unlike the
    legacy line scanner), so callers don't each need their own guard.

    Args:
        content: Markdown content
        lang: Language code for this content (default: "en")

    Returns:
        ParseResult with Localized fields populated for the given language
    """
    try:
        return _parse_single_language_guide(content, lang)
    except Exception as e:
        logger.exception("Guide parsing failed (lang=%s)", lang)
        result = ParseResult()
        result.errors.append(
            ParseError(
                error_type=ParseErrorType.PARSE_FAILURE,
                message=f"Guide parsing failed: {e}",
            )
        )
        return result


def _parse_single_language_guide(content: str, lang: str = "en") -> ParseResult:
    result = ParseResult()

    if not content.strip():
        return result

    # AST-based structural split on top-level headings. levels={1,2}:
    #   * level 1 -> ``# Deployment Complete`` global success header (legacy)
    #   * level 2 -> ``## Preset:`` / ``## Step N:`` headers
    # ``### Deployment Complete`` (level 3) is NOT a
    # split boundary here, so it stays inside its enclosing step section and is
    # handled downstream by parse_subsections (post_deploy) — matching the legacy
    # state machine, which only switched to the preset_completion bucket when no
    # step was active (a case that never occurs in practice; see the
    # ``current_step_header is None`` guard in the old loop).
    tokens = md_ast.parse(content)
    sections = md_ast.split_by_heading(content, tokens, levels={1, 2})

    current_section = "overview"
    current_preset: Optional[PresetGuide] = None
    current_step_header: Optional[str] = None
    current_step_content: str = ""
    current_step_line: int = 0
    seen_step_ids: set[str] = set()

    overview_parts: list[str] = []
    success_parts: list[str] = []
    preset_completion_parts: list[str] = []
    preset_description_parts: list[str] = []

    def flush_step():
        """Process accumulated step content."""
        nonlocal current_step_header, current_step_content, current_step_line
        if current_step_header:
            step, errors, warnings = parse_deployment_step(
                current_step_header,
                current_step_content,
                "",  # No additional language content
                current_step_line,
            )
            result.errors.extend(errors)
            result.warnings.extend(warnings)
            if step:
                if step.id in seen_step_ids:
                    result.errors.append(
                        ParseError(
                            error_type=ParseErrorType.DUPLICATE_STEP_ID,
                            message=f"Duplicate step ID: {step.id}",
                            line_number=current_step_line,
                        )
                    )
                else:
                    seen_step_ids.add(step.id)
                    if current_preset:
                        current_preset.steps.append(step)
                    else:
                        result.steps.append(step)

            current_step_header = None
            current_step_content = ""

    def flush_preset_completion():
        """Process accumulated preset completion content."""
        nonlocal preset_completion_parts
        if preset_completion_parts and current_preset:
            completion_html = md_to_html("".join(preset_completion_parts).strip())
            current_preset.completion = SuccessContent(
                content=Localized({lang: completion_html})
            )
        preset_completion_parts = []

    def flush_preset_description():
        """Flush accumulated preset description."""
        nonlocal preset_description_parts
        if preset_description_parts and current_preset:
            desc_html = md_to_html("".join(preset_description_parts).strip())
            current_preset.description.set(lang, desc_html)
        preset_description_parts = []

    def accumulate(raw_md: str):
        """Append a section's raw markdown to the current content bucket.

        Empty strings are skipped so that a header with no following lines
        leaves its bucket empty (matching the legacy per-line accumulation,
        where zero intermediate lines means the bucket list stays empty).
        """
        if not raw_md:
            return
        if current_section == "overview":
            overview_parts.append(raw_md)
        elif current_section == "step":
            nonlocal current_step_content
            current_step_content += raw_md
        elif current_section == "success":
            success_parts.append(raw_md)
        elif current_section == "preset_completion":
            preset_completion_parts.append(raw_md)
        elif current_section == "preset" and not current_step_header:
            preset_description_parts.append(raw_md)

    for sec in sections:
        heading = sec.heading_text

        # Pre-first-heading (leading) content -> current bucket (overview).
        if heading is None:
            accumulate(sec.raw_md)
            continue

        if sec.level == 1:
            header_line = f"# {heading}"
            # Global success section (deprecated, kept for back-compat).
            if SUCCESS_HEADER_PATTERN.match(header_line):
                flush_step()
                flush_preset_description()
                flush_preset_completion()
                current_section = "success"
                accumulate(_strip_leading_heading_line(sec.raw_md))
                continue
            # Any other level-1 heading is ordinary content for the current
            # bucket (legacy fall-through appended the raw line).
            accumulate(sec.raw_md)
            continue

        # level == 2
        header_line = f"## {heading}"

        # Preset header (EN or ZH).
        preset_match = PRESET_HEADER_PATTERN.match(
            header_line
        ) or PRESET_HEADER_ZH_PATTERN.match(header_line)
        if preset_match:
            flush_step()
            flush_preset_description()
            flush_preset_completion()
            # Reset seen_step_ids for new preset
            seen_step_ids.clear()
            preset_name = preset_match.group(1).strip()
            current_preset = PresetGuide(
                id=preset_match.group(2),
                name=Localized({lang: preset_name}),
                description=Localized(),
            )
            result.presets.append(current_preset)
            current_section = "preset"
            preset_description_parts.clear()
            accumulate(_strip_leading_heading_line(sec.raw_md))
            continue

        # Step header.
        step_match = STEP_HEADER_PATTERN.match(header_line)
        if step_match:
            flush_step()
            flush_preset_description()
            current_step_header = header_line
            current_step_content = _strip_leading_heading_line(sec.raw_md)
            current_step_line = sec.start_line
            current_section = "step"
            continue

        # Unmatched level-2 heading -> ordinary content for the current bucket
        # (legacy fall-through appended the raw line + following body).
        accumulate(sec.raw_md)

    # Flush final step and preset completion
    flush_step()
    flush_preset_description()
    flush_preset_completion()

    # Set overview and success content
    result.overview.set(lang, md_to_html("".join(overview_parts).strip()))
    if success_parts:
        result.success = SuccessContent(
            content=Localized({lang: md_to_html("".join(success_parts).strip())})
        )

    return result


def validate_structure_consistency(
    en_result: ParseResult, zh_result: ParseResult
) -> StructureValidationResult:
    """Validate that EN and ZH guide files have consistent structure.

    Checks:
    - Same number and order of presets
    - Same preset IDs
    - Same number and order of steps within each preset
    - Same step IDs, types, required flags, and config files
    """
    validation = StructureValidationResult()

    # Extract preset IDs
    validation.en_presets = [p.id for p in en_result.presets]
    validation.zh_presets = [p.id for p in zh_result.presets]

    # Extract steps by preset
    validation.en_steps_by_preset = {
        p.id: [(s.id, s.type, s.required, s.config_file) for s in p.steps]
        for p in en_result.presets
    }
    validation.zh_steps_by_preset = {
        p.id: [(s.id, s.type, s.required, s.config_file) for s in p.steps]
        for p in zh_result.presets
    }

    # Check preset count
    if len(validation.en_presets) != len(validation.zh_presets):
        validation.valid = False
        validation.errors.append(
            ParseError(
                error_type=ParseErrorType.PRESET_COUNT_MISMATCH,
                message=f"Preset count mismatch: EN has {len(validation.en_presets)}, ZH has {len(validation.zh_presets)}",
                suggestion="Ensure both guide.md and guide_zh.md have the same number of presets",
            )
        )

    # Check preset IDs and order
    for i, (en_id, zh_id) in enumerate(
        zip(validation.en_presets, validation.zh_presets)
    ):
        if en_id != zh_id:
            validation.valid = False
            validation.errors.append(
                ParseError(
                    error_type=ParseErrorType.PRESET_ID_MISMATCH,
                    message=f"Preset ID mismatch at position {i + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                    suggestion=f"Ensure preset IDs match: {{#{en_id}}} should be the same in both files",
                )
            )

    # Check steps within each preset
    for preset_id in validation.en_presets:
        if preset_id not in validation.zh_steps_by_preset:
            continue  # Already reported as preset mismatch

        en_steps = validation.en_steps_by_preset.get(preset_id, [])
        zh_steps = validation.zh_steps_by_preset.get(preset_id, [])

        # Check step count
        if len(en_steps) != len(zh_steps):
            validation.valid = False
            validation.errors.append(
                ParseError(
                    error_type=ParseErrorType.STEP_COUNT_MISMATCH,
                    message=f"Step count mismatch in preset '{preset_id}': EN has {len(en_steps)}, ZH has {len(zh_steps)}",
                    suggestion="Ensure both files have the same number of steps in this preset",
                )
            )
            continue

        # Check each step
        for j, (en_step, zh_step) in enumerate(zip(en_steps, zh_steps)):
            en_id, en_type, en_required, en_config = en_step
            zh_id, zh_type, zh_required, zh_config = zh_step

            if en_id != zh_id:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_ID_MISMATCH,
                        message=f"Step ID mismatch in preset '{preset_id}' at step {j + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                        suggestion=f"Ensure step ID {{#{en_id}}} matches in guide_zh.md",
                    )
                )

            if en_type != zh_type:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_TYPE_MISMATCH,
                        message=f"Step type mismatch for '{en_id}' in preset '{preset_id}': EN has type={en_type}, ZH has type={zh_type}",
                        suggestion=f"Ensure type={en_type} is the same in both files",
                    )
                )

            if en_required != zh_required:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_REQUIRED_MISMATCH,
                        message=f"Step required mismatch for '{en_id}' in preset '{preset_id}': EN has required={en_required}, ZH has required={zh_required}",
                        suggestion=f"Ensure required={'true' if en_required else 'false'} is the same in both files",
                    )
                )

            if en_config != zh_config:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_CONFIG_MISMATCH,
                        message=f"Step config mismatch for '{en_id}' in preset '{preset_id}': EN has config={en_config}, ZH has config={zh_config}",
                        suggestion=f"Ensure config={en_config} is the same in both files",
                    )
                )

    return validation


def _merge_localized(base: Localized, other: Localized, lang: str) -> None:
    """Merge content from other Localized into base for the specified language."""
    value = other.get(lang)
    if value is not None:
        base.set(lang, value)


def parse_guide_multilang(
    lang_contents: Dict[str, str],
) -> tuple[ParseResult, StructureValidationResult]:
    """Parse multiple language guide files and validate structure consistency.

    Args:
        lang_contents: Dict mapping language code to file content
                      e.g., {"en": content_en, "zh": content_zh, "ja": content_ja}

    Returns:
        Tuple of (merged ParseResult, StructureValidationResult)
    """
    if not lang_contents:
        return ParseResult(), StructureValidationResult()

    # Parse each language file separately
    results: Dict[str, ParseResult] = {}
    for lang, content in lang_contents.items():
        results[lang] = parse_single_language_guide(content, lang)

    # Select base language (prefer "en", otherwise first available)
    base_lang = "en" if "en" in results else list(results.keys())[0]
    base_result = results[base_lang]

    # Validate structure consistency (compare all against base)
    validation = StructureValidationResult(valid=True)
    for lang, result in results.items():
        if lang != base_lang:
            lang_validation = validate_structure_consistency(base_result, result)
            if not lang_validation.valid:
                validation.valid = False
                validation.errors.extend(lang_validation.errors)
            validation.warnings.extend(lang_validation.warnings)

    # Create merged result
    merged = ParseResult(
        overview=Localized(),
        errors=sum((r.errors for r in results.values()), []),
        warnings=sum((r.warnings for r in results.values()), []),
    )

    # Merge overview from all languages
    for lang, result in results.items():
        overview_content = result.overview.get(lang)
        if overview_content:
            merged.overview.set(lang, overview_content)

    # Merge presets
    for base_preset in base_result.presets:
        merged_preset = PresetGuide(
            id=base_preset.id,
            name=Localized(),
            description=Localized(),
            is_default=base_preset.is_default,
        )

        # Merge preset names and descriptions from all languages
        for lang, result in results.items():
            lang_preset = next(
                (p for p in result.presets if p.id == base_preset.id), None
            )
            if lang_preset:
                name = lang_preset.name.get(lang)
                if name:
                    merged_preset.name.set(lang, name)
                desc = lang_preset.description.get(lang)
                if desc:
                    merged_preset.description.set(lang, desc)

        # Merge steps
        for base_step in base_preset.steps:
            merged_step = DeploymentStep(
                id=base_step.id,
                title=Localized(),
                type=base_step.type,
                required=base_step.required,
                config_file=base_step.config_file,
                section=SectionContent(
                    title=Localized(),
                    subtitle=Localized(),
                    description=Localized(),
                    troubleshoot=Localized(),
                    post_deploy=Localized(),
                    wiring=None,
                ),
            )

            # Merge step content from all languages
            for lang, result in results.items():
                lang_preset = next(
                    (p for p in result.presets if p.id == base_preset.id), None
                )
                if lang_preset:
                    lang_step = next(
                        (s for s in lang_preset.steps if s.id == base_step.id), None
                    )
                    if lang_step:
                        # Merge title
                        title = lang_step.title.get(lang)
                        if title:
                            merged_step.title.set(lang, title)
                            merged_step.section.title.set(lang, title)
                        # Merge subtitle
                        sub = lang_step.section.subtitle.get(lang)
                        if sub:
                            merged_step.section.subtitle.set(lang, sub)
                        # Merge description
                        desc = lang_step.section.description.get(lang)
                        if desc:
                            merged_step.section.description.set(lang, desc)
                        # Merge troubleshoot
                        troubleshoot = lang_step.section.troubleshoot.get(lang)
                        if troubleshoot:
                            merged_step.section.troubleshoot.set(lang, troubleshoot)
                        # Merge post_deploy
                        post_deploy = lang_step.section.post_deploy.get(lang)
                        if post_deploy:
                            merged_step.section.post_deploy.set(lang, post_deploy)
                        # Merge wiring (image from base, steps from all languages)
                        if lang_step.section.wiring:
                            if merged_step.section.wiring is None:
                                merged_step.section.wiring = WiringInfo(
                                    image=lang_step.section.wiring.image,
                                    steps=Localized(),
                                )
                            wiring_steps = lang_step.section.wiring.steps.get(lang)
                            if wiring_steps:
                                merged_step.section.wiring.steps.set(lang, wiring_steps)

            # Merge targets
            if base_step.targets:
                merged_targets = []
                for base_target in base_step.targets:
                    merged_target = TargetInfo(
                        id=base_target.id,
                        name=Localized(),
                        config_file=base_target.config_file,
                        default=base_target.default,
                        target_type=base_target.target_type,
                        description=Localized(),
                        description_html=Localized(),
                        troubleshoot=Localized(),
                        post_deploy=Localized(),
                        wiring=None,
                        device=base_target.device,
                        device_name=base_target.device_name,
                        method=base_target.method,
                    )

                    # Merge target content from all languages
                    for lang, result in results.items():
                        lang_preset = next(
                            (p for p in result.presets if p.id == base_preset.id), None
                        )
                        if lang_preset:
                            lang_step = next(
                                (s for s in lang_preset.steps if s.id == base_step.id),
                                None,
                            )
                            if lang_step:
                                lang_target = next(
                                    (
                                        t
                                        for t in lang_step.targets
                                        if t.id == base_target.id
                                    ),
                                    None,
                                )
                                if lang_target:
                                    # Merge name
                                    name = lang_target.name.get(lang)
                                    if name:
                                        merged_target.name.set(lang, name)
                                    # Merge descriptions
                                    desc = lang_target.description.get(lang)
                                    if desc:
                                        merged_target.description.set(lang, desc)
                                    desc_html = lang_target.description_html.get(lang)
                                    if desc_html:
                                        merged_target.description_html.set(
                                            lang, desc_html
                                        )
                                    # Merge troubleshoot
                                    troubleshoot = lang_target.troubleshoot.get(lang)
                                    if troubleshoot:
                                        merged_target.troubleshoot.set(
                                            lang, troubleshoot
                                        )
                                    # Merge post_deploy
                                    post_deploy = lang_target.post_deploy.get(lang)
                                    if post_deploy:
                                        merged_target.post_deploy.set(lang, post_deploy)
                                    # Merge wiring
                                    if lang_target.wiring:
                                        if merged_target.wiring is None:
                                            merged_target.wiring = WiringInfo(
                                                image=lang_target.wiring.image,
                                                steps=Localized(),
                                            )
                                        wiring_steps = lang_target.wiring.steps.get(
                                            lang
                                        )
                                        if wiring_steps:
                                            merged_target.wiring.steps.set(
                                                lang, wiring_steps
                                            )

                    merged_targets.append(merged_target)
                merged_step.targets = merged_targets

            # Merge modes (for verify type steps)
            if base_step.modes:
                merged_modes = []
                for base_mode in base_step.modes:
                    merged_mode = ModeInfo(
                        id=base_mode.id,
                        name=Localized(),
                        config_file=base_mode.config_file,
                        default=base_mode.default,
                        description=Localized(),
                        description_html=Localized(),
                        troubleshoot=Localized(),
                    )

                    for lang, result in results.items():
                        lang_preset = next(
                            (p for p in result.presets if p.id == base_preset.id), None
                        )
                        if lang_preset:
                            lang_step = next(
                                (s for s in lang_preset.steps if s.id == base_step.id),
                                None,
                            )
                            if lang_step and lang_step.modes:
                                lang_mode = next(
                                    (
                                        m
                                        for m in lang_step.modes
                                        if m.id == base_mode.id
                                    ),
                                    None,
                                )
                                if lang_mode:
                                    name = lang_mode.name.get(lang)
                                    if name:
                                        merged_mode.name.set(lang, name)
                                    desc = lang_mode.description.get(lang)
                                    if desc:
                                        merged_mode.description.set(lang, desc)
                                    desc_html = lang_mode.description_html.get(lang)
                                    if desc_html:
                                        merged_mode.description_html.set(
                                            lang, desc_html
                                        )
                                    troubleshoot = lang_mode.troubleshoot.get(lang)
                                    if troubleshoot:
                                        merged_mode.troubleshoot.set(lang, troubleshoot)

                    merged_modes.append(merged_mode)
                merged_step.modes = merged_modes

            merged_preset.steps.append(merged_step)

        # Merge preset completion
        for lang, result in results.items():
            lang_preset = next(
                (p for p in result.presets if p.id == base_preset.id), None
            )
            if lang_preset and lang_preset.completion:
                if merged_preset.completion is None:
                    merged_preset.completion = SuccessContent(content=Localized())
                content = lang_preset.completion.content.get(lang)
                if content:
                    merged_preset.completion.content.set(lang, content)

        merged.presets.append(merged_preset)

    # Merge success content
    for lang, result in results.items():
        if result.success:
            if merged.success is None:
                merged.success = SuccessContent(content=Localized())
            content = result.success.content.get(lang)
            if content:
                merged.success.content.set(lang, content)

    return merged, validation


def parse_guide_pair(
    en_content: str, zh_content: str
) -> tuple[ParseResult, StructureValidationResult]:
    """Parse a pair of EN and ZH guide files and validate structure consistency.

    This is a convenience wrapper around parse_guide_multilang for the common
    bilingual (English/Chinese) case.

    Args:
        en_content: Content of guide.md (English)
        zh_content: Content of guide_zh.md (Chinese)

    Returns:
        Tuple of (merged ParseResult, StructureValidationResult)
    """
    return parse_guide_multilang({"en": en_content, "zh": zh_content})
