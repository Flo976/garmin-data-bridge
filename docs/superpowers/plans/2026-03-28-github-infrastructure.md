# GitHub Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CI/CD, releases, issue/PR templates, pyproject.toml packaging, and repo polish to garmin-data-bridge.

**Architecture:** GitHub Actions workflows for CI (lint/test/security/build) and release automation (tag-triggered). YAML issue forms and markdown PR template. Minimal pyproject.toml for local install only.

**Tech Stack:** GitHub Actions, ruff, pytest, bandit, pip-audit, setuptools, softprops/action-gh-release

---

## File Structure

```
.github/
├── workflows/
│   ├── ci.yml              # CI: lint + test + security + build
│   └── release.yml         # Release: changelog + GitHub Release on v* tag
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml      # Bug report form
│   └── feature_request.yml # Feature request form
└── pull_request_template.md # PR template

pyproject.toml               # Minimal packaging (local install only)
README.md                    # Add CI + release badges
.gitignore                   # Add dist/, *.egg-info/
```

---

### Task 1: Create pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

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
dev = [
    "pytest>=8.0,<9",
    "ruff>=0.8,<1",
    "bandit>=1.7,<2",
    "pip-audit>=2.7,<3",
    "build>=1.0,<2",
]

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.bandit]
exclude_dirs = ["tests", ".venv"]
```

- [ ] **Step 2: Verify the package builds**

Run: `cd /home/florent/garmin-playwright-sync && python -m build`
Expected: `dist/` contains `garmin_data_bridge-1.0.0.tar.gz` and a `.whl` file.

- [ ] **Step 3: Update .gitignore**

Add these lines at the end of `.gitignore`:

```
dist/
*.egg-info/
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "build: add pyproject.toml for local packaging"
```

---

### Task 2: Create CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install ruff
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -v

  security:
    name: Security
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[dev]"
      - run: bandit -r src/
      - run: pip-audit

  build:
    name: Build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install build
      - run: python -m build
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow with lint, test, security, and build"
```

---

### Task 3: Create Release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: write

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow for tag-triggered GitHub Releases"
```

---

### Task 4: Create issue templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`

- [ ] **Step 1: Create directory**

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

- [ ] **Step 2: Create `.github/ISSUE_TEMPLATE/bug_report.yml`**

```yaml
name: Bug Report
description: Report a bug or unexpected behavior
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What happened?
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: How can we reproduce the issue?
      placeholder: |
        1. Run `./run.sh`
        2. ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      description: What did you expect to happen?
    validations:
      required: true
  - type: dropdown
    id: os
    attributes:
      label: Operating System
      options:
        - Raspberry Pi OS (Bookworm)
        - Raspberry Pi OS (Bullseye)
        - Ubuntu 22.04
        - Ubuntu 24.04
        - Debian 12
        - Other
    validations:
      required: true
  - type: dropdown
    id: python
    attributes:
      label: Python version
      options:
        - "3.11"
        - "3.12"
        - "3.13"
    validations:
      required: true
  - type: dropdown
    id: hardware
    attributes:
      label: Hardware
      options:
        - Raspberry Pi 4
        - Raspberry Pi 5
        - x86_64 server/desktop
        - Other
    validations:
      required: false
  - type: textarea
    id: logs
    attributes:
      label: Logs
      description: Paste any relevant log output
      render: shell
    validations:
      required: false
```

- [ ] **Step 3: Create `.github/ISSUE_TEMPLATE/feature_request.yml`**

```yaml
name: Feature Request
description: Suggest a new feature or improvement
labels: ["enhancement"]
body:
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What feature would you like?
    validations:
      required: true
  - type: textarea
    id: usecase
    attributes:
      label: Use case
      description: Why do you need this? What problem does it solve?
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Have you considered other approaches?
    validations:
      required: false
```

- [ ] **Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "docs: add bug report and feature request issue templates"
```

---

### Task 5: Create PR template

**Files:**
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Create `.github/pull_request_template.md`**

```markdown
## Changes

<!-- What did you change? -->

## Why

<!-- Why is this change needed? -->

## Checklist

- [ ] Tests pass (`pytest -v`)
- [ ] Lint passes (`ruff check src/ tests/`)
- [ ] Commits follow [conventional commits](https://www.conventionalcommits.org/)
```

- [ ] **Step 2: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "docs: add pull request template"
```

---

### Task 6: Update README with badges and update .gitignore

**Files:**
- Modify: `README.md:9-14` (badge section)

- [ ] **Step 1: Add CI and Release badges to README.md**

Insert after line 10 (after the `</p>` closing the first badge group), add two new badges inside the second `<p align="center">` block at line 9:

In the `<p align="center">` block that starts at line 9 containing the badges, add these two badges after the existing ones (before the closing `</p>`):

```html
  <a href="https://github.com/Flo976/garmin-data-bridge/actions/workflows/ci.yml"><img src="https://github.com/Flo976/garmin-data-bridge/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/Flo976/garmin-data-bridge/releases/latest"><img src="https://img.shields.io/github/v/release/Flo976/garmin-data-bridge?style=flat-square&label=release" alt="Release" /></a>
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add CI and release badges to README"
```

---

### Task 7: Fix lint issues (if any)

**Files:**
- Modify: any files flagged by ruff

- [ ] **Step 1: Install ruff and run lint**

```bash
pip install ruff
ruff check src/ tests/
ruff format --check src/ tests/
```

- [ ] **Step 2: Auto-fix issues**

If there are lint issues:

```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

- [ ] **Step 3: Run tests to verify nothing broke**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit (only if changes were made)**

```bash
git add -u
git commit -m "style: fix lint issues for CI compliance"
```

---

### Task 8: Fix security issues (if any)

**Files:**
- Modify: any files flagged by bandit

- [ ] **Step 1: Install bandit and pip-audit, run security checks**

```bash
pip install bandit pip-audit
bandit -r src/
pip-audit
```

- [ ] **Step 2: Fix any issues found**

Address each finding. Common bandit findings:
- `B603` (subprocess call) — add `# nosec B603` if intentional
- `B101` (assert) — only in test files, already excluded

- [ ] **Step 3: Run tests to verify nothing broke**

```bash
pytest -v
```

- [ ] **Step 4: Commit (only if changes were made)**

```bash
git add -u
git commit -m "fix: address security findings from bandit/pip-audit"
```

---

### Task 9: Push and verify CI + create first release

- [ ] **Step 1: Push all commits to master**

```bash
git push origin master
```

- [ ] **Step 2: Verify CI passes**

Check GitHub Actions: `https://github.com/Flo976/garmin-data-bridge/actions`
Expected: all 4 jobs (lint, test, security, build) green.

- [ ] **Step 3: Fix any CI failures**

If CI fails, fix locally, commit, push again.

- [ ] **Step 4: Create first release tag**

```bash
git tag v1.0.0
git push --tags
```

- [ ] **Step 5: Verify release was created**

Check: `https://github.com/Flo976/garmin-data-bridge/releases`
Expected: Release v1.0.0 with auto-generated changelog.

---

### Task 10: Configure GitHub repo settings (manual)

These steps must be done manually in the GitHub web UI:

- [ ] **Step 1: Set repo description**

Go to repo Settings → General.
Description: `Sync Garmin Connect health data to any webhook — bypasses Cloudflare via browser automation`

- [ ] **Step 2: Set topics**

On the repo main page, click the gear icon next to "About".
Topics: `garmin`, `garmin-connect`, `health-data`, `webhook`, `playwright`, `raspberry-pi`, `python`

- [ ] **Step 3: Enable branch protection**

Settings → Branches → Add branch ruleset for `master`:
- Require status checks to pass: `Lint`, `Test (Python 3.11)`, `Test (Python 3.12)`, `Test (Python 3.13)`, `Security`, `Build`
