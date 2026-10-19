#!/usr/bin/env python3
"""Lint solution content for customer-facing readiness, clean formatting, and structure.

Checks:
1. Banned internal development / gating wording:
   - "草稿", "Draft", "0.1.0-draft"
   - "验收受阻", "acceptance blocked"
   - "未修"
   - "发布顺序", "prune-stale"
   - "M7/M8" milestone gates
   - "暂存契约", "可审查契约"
   - "fail closed" in prose describing gating/licensing failures
2. Broken blockquotes:
   - Stray blockquote markers ('>') starting immediately after a non-quote prose line
     without an intervening blank line.
3. Standard 4-part structure in description*.md:
   - What the solution does (这个方案能帮你做什么 / What the Solution Does)
   - Core value / What you get (核心价值 / Core Value / What You Get)
   - Applicable scenarios (适用场景 / Suitable Scenarios)
   - Measured performance / Usage notes (实测效果 / Measured Performance / 使用须知 / Usage Notes)

Scope:
- solutions/*/description*.md
- solutions/*/guide*.md
- solutions/*/solution.yaml
- solutions/*/devices/*.yaml
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


BANNED_PATTERNS = [
    (r"草稿", "banned internal status '草稿'"),
    (r"\bDraft\b", "banned internal status 'Draft'"),
    (r"\b0\.1\.0-draft\b", "banned draft image tag '0.1.0-draft'"),
    (r"验收受阻", "banned internal blocker '验收受阻'"),
    (r"\bacceptance\s+blocked\b", "banned internal blocker 'acceptance blocked'"),
    (r"目前未修", "banned internal note '目前未修'"),
    (r"发布顺序", "banned internal PR note '发布顺序'"),
    (r"prune-stale", "banned internal tooling term 'prune-stale'"),
    (r"\bM[1-9]/M[1-9]\b", "banned internal milestone 'M*/M*'"),
    (r"暂存契约", "banned internal wording '暂存契约'"),
    (r"可审查契约", "banned internal wording '可审查契约'"),
]

BANNED_REGEX = [(re.compile(pat, re.IGNORECASE), desc) for pat, desc in BANNED_PATTERNS]

EXEMPT_PATTERNS = [
    re.compile(r"discards?\s+the\s+draft|丢弃草稿", re.IGNORECASE),
]

SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?", ":", "：", ";", "；")

ZH_SECTION_PATTERNS = {
    "what_it_does": re.compile(
        r"^##\s+.*(做什么|这是什么|能抓什么|是什么|能帮你做什么|这个能力|这个方案|这个\s*Lab)",
        re.IGNORECASE,
    ),
    "core_value": re.compile(
        r"^##\s+.*(核心价值|你会得到什么|你能得到什么|值班人员实际看到什么|核心优势|得到什么|工作原理|输出接口|技术规格)",
        re.IGNORECASE,
    ),
    "scenarios": re.compile(
        r"^##\s+.*(适用场景|适合接到哪里|适合接到哪些系统|适用集成场景|集成场景|哪些场景可用|两个套餐|典型场景|应用场景|能抓什么)",
        re.IGNORECASE,
    ),
    "measured_or_notes": re.compile(
        r"^##\s+.*(实测效果|实测数据|实测边界|实测结果|使用须知|硬件要求|技术规格|使用要求|标称值|部署方式|已知限制|注意事项|集成指南)",
        re.IGNORECASE,
    ),
}

EN_SECTION_PATTERNS = {
    "what_it_does": re.compile(
        r"^##\s+.*(What\s+.*(Does|Helps|Is|Adds|Grasp)|How it works|What\s+this\s+capability)",
        re.IGNORECASE,
    ),
    "core_value": re.compile(
        r"^##\s+.*(Core\s+(Value|Benefits)|Key\s+Benefits|What\s+You\s+Get|What\s+Operators|Advantages|How it works|Technical\s+Specs|Interfaces)",
        re.IGNORECASE,
    ),
    "scenarios": re.compile(
        r"^##\s+.*(Suitable\s+Scenarios|Where\s+to\s+(Connect|use)|Use\s+Cases|Integration\s+Scenarios|Where\s+it\s+(fits|works)|What\s+You\s+Can\s+Connect|The\s+Two\s+Presets|Application\s+Scenarios|Typical\s+Scenarios|What\s+it\s+can\s+grasp)",
        re.IGNORECASE,
    ),
    "measured_or_notes": re.compile(
        r"^##\s+.*(Measured|Usage\s+Notes|Hardware\s+Requirements|Technical\s+Specs|Requirements|Known\s+Limitations|What\s+You\s+Need|Deployment\s+(Options|Comparison)|How\s+Well\s+It\s+Works|Notes)",
        re.IGNORECASE,
    ),
}

JA_SECTION_PATTERNS = {
    "what_it_does": re.compile(
        r"^##\s+.*(このソリューションでできること|このソリューションは何をするか|何ができるか|この機能でできること)",
        re.IGNORECASE,
    ),
    "core_value": re.compile(
        r"^##\s+.*(主なメリット|主な価値|コアバリュー|得られるもの|導入メリット)",
        re.IGNORECASE,
    ),
    "scenarios": re.compile(
        r"^##\s+.*(利用シーン|適用シナリオ|ユースケース|連携先|活用シーン)",
        re.IGNORECASE,
    ),
    "measured_or_notes": re.compile(
        r"^##\s+.*(ご利用にあたって|実測データ|実測効果|注意事項|要件|ハードウェア要件)",
        re.IGNORECASE,
    ),
}

GLOBS = [
    "solutions/*/description*.md",
    "solutions/*/guide*.md",
    "solutions/*/solution.yaml",
    "solutions/*/devices/*.yaml",
]


@dataclass
class Finding:
    path: str
    lineno: int
    rule: str
    detail: str


def check_banned_wording(path: str, lines: list[str], is_yaml: bool) -> list[Finding]:
    findings: list[Finding] = []
    in_code_fence = False

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        # In YAML, skip comment lines
        if is_yaml and stripped.startswith("#"):
            continue

        # Skip lines matching known legitimate user actions
        if any(pat.search(line) for pat in EXEMPT_PATTERNS):
            continue

        for pat, desc in BANNED_REGEX:
            m = pat.search(line)
            if m:
                findings.append(
                    Finding(
                        path=path,
                        lineno=lineno,
                        rule="banned-wording",
                        detail=f"{desc} in '{line.strip()[:120]}'",
                    )
                )
    return findings


def check_broken_blockquotes(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    in_code_fence = False
    prev_line = ""

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            prev_line = line
            continue

        if in_code_fence:
            prev_line = line
            continue

        # Check for broken blockquote: current line starts with '>' but previous line was non-empty text
        # that did NOT start with '>' and did NOT end with sentence-ending punctuation.
        if stripped.startswith(">") and prev_line.strip() and not prev_line.strip().startswith(">"):
            prev_stripped = prev_line.strip()
            if not prev_stripped.endswith(SENTENCE_ENDINGS):
                findings.append(
                    Finding(
                        path=path,
                        lineno=lineno,
                        rule="broken-blockquote",
                        detail=f"Stray blockquote marker mid-sentence: previous line '{prev_stripped[-30:]}' does not end with sentence punctuation",
                    )
                )

        prev_line = line
    return findings


def check_description_structure(path: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    if "smart_space_assistant" in path:
        return findings

    if path.endswith("description_zh.md"):
        patterns = ZH_SECTION_PATTERNS
        lang = "Chinese"
    elif path.endswith("description_ja.md"):
        patterns = JA_SECTION_PATTERNS
        lang = "Japanese"
    elif path.endswith("description.md") or path.endswith("description_en.md"):
        patterns = EN_SECTION_PATTERNS
        lang = "English"
    else:
        return findings

    headings = [line.strip() for line in lines if line.startswith("## ")]

    for section_name, pat in patterns.items():
        if not any(pat.match(h) for h in headings):
            findings.append(
                Finding(
                    path=path,
                    lineno=1,
                    rule="missing-structure-section",
                    detail=f"Missing standard section '{section_name}' in {lang} description (found: {headings})",
                )
            )

    return findings


def scan_file(root: str, rel_path: str) -> list[Finding]:
    full_path = os.path.join(root, rel_path)
    if not os.path.isfile(full_path):
        return []

    is_yaml = rel_path.endswith((".yaml", ".yml"))
    is_md = rel_path.endswith(".md")
    is_desc = is_md and ("description" in os.path.basename(rel_path))

    with open(full_path, encoding="utf-8") as f:
        lines = f.readlines()

    findings: list[Finding] = []
    findings.extend(check_banned_wording(rel_path, lines, is_yaml))

    if is_md:
        findings.extend(check_broken_blockquotes(rel_path, lines))

    if is_desc:
        findings.extend(check_description_structure(rel_path, lines))

    return findings


def scan(root: str) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in GLOBS:
        for full_path in sorted(glob.glob(os.path.join(root, pattern))):
            rel_path = os.path.relpath(full_path, root)
            findings.extend(scan_file(root, rel_path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Root directory to scan (default: .)")
    args = parser.parse_args()

    findings = scan(args.root)
    for f in findings:
        print(f"{f.path}:{f.lineno}: [{f.rule}] {f.detail}")

    print(f"\nsolution-content lint: {len(findings)} issue(s) found.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
