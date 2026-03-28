# GitHub Infrastructure Design

**Date:** 2026-03-28
**Status:** Approved
**Repo:** Flo976/garmin-data-bridge

## Overview

Add CI/CD, releases, issue templates, packaging, and repo polish to the garmin-data-bridge project. The project is functionally mature (parsers, tests, CLI, systemd) but lacks GitHub infrastructure.

## 1. File Structure

```
.github/
├── workflows/
│   ├── ci.yml
│   └── release.yml
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml
│   └── feature_request.yml
└── pull_request_template.md

pyproject.toml
```

Modified files: `README.md`, `.gitignore`

## 2. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:** push on `master`, all PRs.

**Matrix:** Python 3.11, 3.12, 3.13 on `ubuntu-latest`.

**Jobs (all run in parallel):**

| Job | Tool | Command |
|-----|------|---------|
| lint | ruff | `ruff check src/ tests/` + `ruff format --check src/ tests/` |
| test | pytest | `pytest` on each Python version in the matrix |
| security | bandit + pip-audit | `bandit -r src/` + `pip-audit` |
| build | build | `python -m build` to verify pyproject.toml produces a valid package |

Each job is independent. Branch protection (configured manually in GitHub Settings) blocks merge if any job fails.

## 3. Release Workflow (`.github/workflows/release.yml`)

**Trigger:** push of a tag matching `v*` (e.g., `v1.0.0`).

**Steps:**
1. Checkout code
2. Create GitHub Release using `softprops/action-gh-release` with `generate_release_notes: true`
3. GitHub auto-generates changelog grouped by commit type (feat, fix, etc.)
4. Tarball and zip are attached automatically by GitHub

**Release process:**
```bash
git tag v1.0.0
git push --tags
# → GitHub Actions creates the Release automatically
```

**Versioning:** Manual Semantic Versioning. The version in `pyproject.toml` should be bumped in the same commit as the tag.

## 4. Issue Templates

### Bug Report (`.github/ISSUE_TEMPLATE/bug_report.yml`)

YAML form with fields:
- **Description** (textarea, required)
- **Steps to reproduce** (textarea, required)
- **Expected behavior** (textarea, required)
- **Environment** (dropdowns): OS, Python version, Raspberry Pi model
- **Logs** (textarea, optional)

### Feature Request (`.github/ISSUE_TEMPLATE/feature_request.yml`)

YAML form with fields:
- **Description** (textarea, required)
- **Use case / motivation** (textarea, required)
- **Alternatives considered** (textarea, optional)

## 5. PR Template (`.github/pull_request_template.md`)

Sections:
- **Changes** — what was changed
- **Why** — motivation
- **Checklist:** tests pass, lint OK, conventional commits

## 6. Packaging (`pyproject.toml`)

Minimal `pyproject.toml` for local installation only (no PyPI publishing).

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "garmin-data-bridge"
version = "1.0.0"
description = "Sync Garmin Connect health data to any webhook via browser automation"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "patchright>=1.58,<2",
    "requests>=2.31,<3",
    "python-dotenv>=1.0,<2",
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "bandit", "pip-audit", "build"]
```

- No CLI entry point (project is used via `run.sh` / `python -m src.sync`)
- `requirements.txt` and `requirements-dev.txt` remain for backward compatibility with `setup.sh`
- Dev install: `pip install -e ".[dev]"`

## 7. Repo Polish

### README.md

Add two dynamic badges after existing badges:
- CI status: `![CI](https://github.com/Flo976/garmin-data-bridge/actions/workflows/ci.yml/badge.svg)`
- Latest release: `https://img.shields.io/github/v/release/Flo976/garmin-data-bridge?style=flat-square`

### .gitignore

Add:
```
dist/
*.egg-info/
```

### GitHub Settings (manual)

- **Description:** "Sync Garmin Connect health data to any webhook — bypasses Cloudflare via browser automation"
- **Topics:** garmin, garmin-connect, health-data, webhook, playwright, raspberry-pi, python
- **Branch protection on master:** require CI status checks to pass before merge

## 8. First Release

After all infrastructure is in place, tag `v1.0.0` to create the inaugural release. This represents the current feature-complete state of the project.
