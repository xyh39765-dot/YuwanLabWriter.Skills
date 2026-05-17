#!/usr/bin/env python3
"""Validate marketplace.json and Skill package invariants."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
ID_RE = re.compile(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$")
FORBIDDEN_SUFFIXES = {".py", ".js", ".ts", ".sh", ".bash", ".zsh", ".exe", ".bin"}


def main() -> None:
    enforced_author = read_author_arg()
    errors: list[str] = []
    marketplace = json.loads((ROOT / "marketplace.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    manifest_ids = {item["id"] for item in marketplace.get("skills", [])}

    for folder in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        meta_path = folder / "skill.yaml"
        if not meta_path.exists():
            errors.append(f"{folder}: missing skill.yaml")
            continue
        meta = load_skill_yaml(meta_path)
        skill_id = str(meta.get("id") or "")
        if not ID_RE.match(skill_id):
            errors.append(f"{folder}: invalid id {skill_id!r}")
        if folder.name != skill_id:
            errors.append(f"{folder}: folder name must match id {skill_id!r}")
        if skill_id in seen:
            errors.append(f"{folder}: duplicate id {skill_id}")
        seen.add(skill_id)

        author = str((meta.get("author") or {}).get("github") or "")
        expected_author = skill_id.split("@", 1)[0] if "@" in skill_id else ""
        if author != expected_author:
            errors.append(f"{folder}: author.github must be {expected_author!r}")
        if enforced_author and expected_author.lower() != enforced_author.lower():
            errors.append(
                f"{folder}: author prefix {expected_author!r} must match submitting GitHub account {enforced_author!r}"
            )

        entry = str(meta.get("entry") or "")
        entry_path = folder / entry
        if not entry or not entry_path.exists():
            errors.append(f"{folder}: missing entry {entry!r}")
        elif entry_path.suffix.lower() != ".md":
            errors.append(f"{folder}: entry must be Markdown")

        checksum = str(meta.get("checksum_sha256") or "")
        if entry_path.exists() and checksum and checksum != sha256_file(entry_path):
            errors.append(f"{folder}: checksum does not match {entry}")

        runtime_kind = str(meta.get("runtime_kind") or "")
        if runtime_kind != "instruction-only":
            errors.append(f"{folder}: runtime.kind must be instruction-only")

        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
                errors.append(f"{folder}: executable/runtime file is not allowed in v1: {path.name}")

    missing_from_manifest = seen - manifest_ids
    if missing_from_manifest:
        errors.append(f"marketplace.json missing ids: {sorted(missing_from_manifest)}")
    orphaned_manifest = manifest_ids - seen
    if orphaned_manifest:
        errors.append(f"marketplace.json references missing ids: {sorted(orphaned_manifest)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"OK: {len(seen)} Skill package(s) validated")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_author_arg() -> str:
    for idx, arg in enumerate(sys.argv[1:]):
        if arg == "--author-github" and idx + 2 <= len(sys.argv[1:]):
            return sys.argv[idx + 2].strip()
        if arg.startswith("--author-github="):
            return arg.split("=", 1)[1].strip()
    return os.getenv("YUWAN_SKILL_AUTHOR_GITHUB", "").strip()


def load_skill_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    out: dict = {"tags": []}
    section = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not raw.startswith(" ") and line.endswith(":"):
            section = line[:-1]
            continue
        if section == "author" and line.strip().startswith("github:"):
            out.setdefault("author", {})["github"] = scalar(line.split(":", 1)[1])
            continue
        if section == "runtime" and line.strip().startswith("kind:"):
            out["runtime_kind"] = scalar(line.split(":", 1)[1])
            continue
        if section == "checksum" and line.strip().startswith("sha256:"):
            out["checksum_sha256"] = scalar(line.split(":", 1)[1])
            continue
        if section == "tags" and line.strip().startswith("- "):
            out.setdefault("tags", []).append(scalar(line.strip()[2:]))
            continue
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if match:
            section = ""
            out[match.group(1)] = scalar(match.group(2))
    return out


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


if __name__ == "__main__":
    main()
