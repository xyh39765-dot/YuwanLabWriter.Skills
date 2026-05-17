#!/usr/bin/env python3
"""Build marketplace.json from skills/*/skill.yaml."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def main() -> None:
    entries = []
    for folder in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        meta_path = folder / "skill.yaml"
        if not meta_path.exists():
            continue
        meta = load_skill_yaml(meta_path)
        entry = str(meta.get("entry") or "SKILL.md")
        entry_path = folder / entry
        checksum = sha256_file(entry_path)
        meta["checksum_sha256"] = checksum
        write_skill_yaml(meta_path, meta)
        entries.append(
            {
                "id": meta["id"],
                "name": meta["name"],
                "display_name": meta["display_name"],
                "version": str(meta["version"]),
                "author_github": meta["author"]["github"],
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
                "license": meta.get("license", ""),
                "path": folder.relative_to(ROOT).as_posix(),
                "entry": entry,
                "checksum_sha256": checksum,
            }
        )
    marketplace = {
        "schema_version": "1.0.0",
        "generated_at": "1970-01-01T00:00:00Z",
        "skills": entries,
    }
    (ROOT / "marketplace.json").write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


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


def write_skill_yaml(path: Path, meta: dict) -> None:
    tags = "\n".join(f"  - {tag}" for tag in meta.get("tags", []))
    text = f"""id: {meta["id"]}
name: {meta["name"]}
display_name: {meta["display_name"]}
version: {meta["version"]}
author:
  github: {meta["author"]["github"]}
description: {meta.get("description", "")}
tags:
{tags}
license: {meta.get("license", "")}
entry: {meta.get("entry", "SKILL.md")}
visibility: {meta.get("visibility", "public")}
runtime:
  kind: {meta.get("runtime_kind", "instruction-only")}
checksum:
  sha256: {meta.get("checksum_sha256", "")}
updated_at: "{meta.get("updated_at", "")}"
"""
    path.write_text(text, encoding="utf-8")


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


if __name__ == "__main__":
    main()
