# YuwanLabWriter.Skills

Official Skill catalog for YuwanLabWriter native Agents.

This repository is the trusted catalog source. YuwanLabWriter applications read
Skills from the `main` branch only. User and author submissions should arrive as
pull requests, pass validation, and merge into `main` before they become visible
in the Skill Market.

## Layout

```text
marketplace.json
skills/
  GitHubUser@skill-name/
    skill.yaml
    SKILL.md
    README.md
    examples/
    assets/
schemas/
scripts/
.github/workflows/
```

## Trust Boundary

V1 marketplace Skills are instruction packages only:

- no runtime scripts
- no project filesystem access
- no database access
- no automatic document mutation
- no hidden network calls

The application installs approved Skills into the user's local Skill library.
Native Agents can read only the Skills explicitly attached to that Agent.

## Validate

```bash
python3 scripts/validate_marketplace.py
```

## Build Manifest

```bash
python3 scripts/build_marketplace.py
```

