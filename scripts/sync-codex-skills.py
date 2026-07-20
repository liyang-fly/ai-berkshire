#!/usr/bin/env python3
"""Generate skill packages from AI Berkshire Claude command files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / "skills"
CODEX_SKILLS = ROOT / "codex-skills"


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :].lstrip("\n")


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def yaml_quote(value: str) -> str:
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'


def metadata_for(name: str, source_name: str, source_text: str) -> str:
    existing, body = split_frontmatter(source_text)
    if existing:
        has_name = re.search(r"(?m)^name:\s*", existing) is not None
        has_description = re.search(r"(?m)^description:\s*", existing) is not None
        lines = []
        if not has_name:
            lines.append(f"name: {name}")
        if not has_description:
            title = first_heading(body, name)
            lines.append(
                "description: "
                + yaml_quote(f"AI Berkshire skill: {title}. Source: skills/{source_name}.")
            )
        lines.append(existing.rstrip())
        return "---\n" + "\n".join(lines) + "\n---\n\n"

    title = first_heading(source_text, name)
    description = f"AI Berkshire skill: {title}. Source: skills/{source_name}."
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {yaml_quote(description)}\n"
        "---\n\n"
    )


def codex_body(name: str, source_name: str, source_text: str) -> str:
    _, body = split_frontmatter(source_text)
    note = (
        "## Codex adapter note\n\n"
        f"This skill is generated from `skills/{source_name}` so Claude Code "
        "and Codex users share one canonical workflow.\n\n"
        "- Treat `$ARGUMENTS` as the user's request in the current Codex thread.\n"
        "- When the source mentions Claude-only surfaces such as Task, Agent, "
        "WebSearch, Bash, Read, or Write, use the closest Codex capability "
        "available in this session: subagents when available, web search when "
        "needed, shell commands for local tools, and normal file edits for "
        "workspace files.\n"
        "- Use shared project tools from `tools/` in this repository. Prefer "
        "running commands from the repository root with paths like "
        "`python3 tools/financial_rigor.py ...`; if the current thread starts "
        "outside the repo, locate the actual checkout path first instead of "
        "assuming a fixed home-directory path.\n"
        "- Before starting research, run the `date` command to confirm "
        "today's date; treat it as the baseline for \"latest\" data and state "
        "the data cutoff date in the report header. Never assume the current "
        "date from training data.\n"
        "- Preserve the research quality rules from `AGENTS.md`: cross-check "
        "financial data, use exact arithmetic tools for valuation/math, and "
        "clearly label uncertainty and source gaps.\n\n"
    )
    return note + body.rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate skill packages from skills/*.md."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify generated output is current without rewriting files.",
    )
    parser.add_argument(
        "--skill",
        dest="skills",
        action="append",
        help="Only sync the named skill. Repeat to sync multiple skills.",
    )
    parser.add_argument(
        "--output-dir",
        help="Write generated skills under this directory. Relative paths resolve from the repo root.",
    )
    return parser.parse_args()


def resolve_output_dir(raw_output_dir: str | None) -> Path:
    if raw_output_dir is None:
        return CODEX_SKILLS

    output_dir = Path(raw_output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    return output_dir


def describe_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def collect_sources(selected_skills: set[str] | None) -> list[Path]:
    sources: list[Path] = []
    for source in sorted(CLAUDE_SKILLS.glob("*.md")):
        if selected_skills is not None and source.stem not in selected_skills:
            continue
        sources.append(source)

    if selected_skills is not None:
        found = {source.stem for source in sources}
        missing = sorted(selected_skills - found)
        if missing:
            joined = ", ".join(missing)
            raise SystemExit(f"Unknown skill(s): {joined}")

    return sources


def main() -> None:
    args = parse_args()
    output_dir = resolve_output_dir(args.output_dir)
    selected_skills = set(args.skills) if args.skills else None
    sources = collect_sources(selected_skills)

    if not args.check:
        output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    stale: list[str] = []
    for source in sources:
        name = source.stem
        source_text = source.read_text(encoding="utf-8")
        target_dir = output_dir / name
        target = target_dir / "SKILL.md"
        content = metadata_for(name, source.name, source_text) + codex_body(
            name, source.name, source_text
        )
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                stale.append(describe_path(target))
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        count += 1

    output_label = describe_path(output_dir)

    if args.check:
        if stale:
            print("Skill packages are out of date:")
            for path in stale:
                print(f"  {path}")
            raise SystemExit(1)
        print(f"Checked {count} skill package(s) in {output_label}")
        return

    print(f"Generated {count} skill package(s) in {output_label}")


if __name__ == "__main__":
    main()
