# GitHub Upload and Maintenance Guide

This document outlines the strategy and best practices for uploading `astrbot_plugin_ow_dashen` to GitHub and maintaining it systematically, especially in sync with the upstream `Overstats` project.

---

## 1. Initial Setup and Upload to GitHub

To publish the repository to GitHub cleanly:

### Step 1: Clean Up Secrets and Data
Ensure the local `.gitignore` is fully active so no personal tokens, local databases, or cached images are pushed.
```bash
# Add files to .gitignore if not present
data/plugin_data/
overstats/src/db/*.sqlite3
res/cache_img/
```

### Step 2: Initialize Git and Push to GitHub
If git is not yet initialized:
```bash
cd astrbot_plugin_ow_dashen-main
git init
git add .
git commit -m "feat: initial commit of astrbot overwatch dashen plugin"
git branch -M main
git remote add origin https://github.com/<your-username>/astrbot_plugin_ow_dashen.git
git push -u origin main
```

---

## 2. Upstream Synchronization Plan (Syncing with Overstats)

Since `astrbot_plugin_ow_dashen` is built on top of `Overstats`, keeping it up-to-date with upstream bug fixes and features is critical.

### Recommended Repository Design
1. **Separation of Core Logic:** Keep the `overstats` directory as pure as possible, maintaining it as a direct mirror/subtree of the upstream `Overstats` `src` and `res` contents.
2. **Subtree or Submodule Approach (Optional but complex):** If upstream is changing rapidly, you can use `git subtree` to pull changes, but since some modifications (like stripping DB write code or adapting paths) are necessary, a manual sync script or branch diff is recommended.
3. **Manual Sync Script (`sync_upstream.py`):**
   We can provide a utility script in the workspace that automatically pulls the latest `Overstats`, extracts the code, modifies imports from `src.*` to `overstats.src.*`, applies the plugin-specific light database patches, and overlays it onto the plugin.

---

## 3. GitHub Action Automation (CI/CD)

Setting up GitHub Actions ensures code quality and updates are verified automatically.

### GitHub Actions Workflow: Code Quality & Linting
Create `.github/workflows/lint.yml` to check for syntax errors:
```yaml
name: Lint and Check

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Lint with flake8
      run: |
        pip install flake8
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

---

## 4. Release and Versioning Strategy

1. **Semantic Versioning (SemVer):** Use `v1.0.0` format.
   - **Major (1.0.0 -> 2.0.0):** Breaking config schema changes or major AstrBot core API changes.
   - **Minor (1.0.0 -> 1.1.0):** Porting new features from upstream (e.g., Sameplay, Leaderboards).
   - **Patch (1.0.0 -> 1.0.1):** Upstream bug fixes, style tweaks, or NetEase Dashen API changes.
2. **AstrBot Plugin Metadata:** Update `metadata.yaml` version info on every release:
   ```yaml
   name: astrbot_plugin_ow_dashen
   desc: 守望先锋大神数据查询插件，基于 Overstats 渲染与数据服务。
   version: 1.0.1
   author: <your-name>
   ```
3. **GitHub Releases:** Use GitHub Release to document changes (Changelog) and attach the pre-compiled `match_stats_summary.json` if it ever updates.

---

## 5. Maintenance Checklist

- [ ] **API Breakages:** NetEase Dashen updates their API periodically. Keep a test account to run `/ow 自检` to check upstream status.
- [ ] **Cache Management:** Clean cached images regularly to prevent server disk bloat (supported by `/ow 清理缓存`).
- [ ] **Community Issues:** Monitor GitHub Issues for user reports about query failures (usually case-sensitivity on BattleTags or expired Dashen tokens).
