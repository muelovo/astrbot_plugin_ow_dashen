# GitHub 上传与持续更新维护方案

本指南详细说明了如何将 `astrbot_plugin_ow_dashen` 上传至 GitHub，并实现与上游 `Overstats` 项目的同步更新以及自动化的 CI/CD 流程。

## 1. 首次上传 GitHub

### 步骤 1：清理敏感数据与缓存 (已完成)
确保本地 `.gitignore` 生效，以防将个人网易大神 token、本地 SQLite 数据库或缓存的对局图片推送到公开仓库。

### 步骤 2：初始化 Git 并推送到 GitHub (已完成)
你已经成功执行了以下命令，完成了仓库的首次推送：
```bash
git init
git add .
git commit -m "feat: initial commit of astrbot overwatch dashen plugin"
git branch -M main
git remote add origin https://github.com/muelovo/astrbot_plugin_ow_dashen.git
git push -u origin main
```

---

## 2. 上游同步方案 (与 Overstats 保持一致)

由于本插件基于 `Overstats` 项目的数据接口和渲染逻辑，因此与上游同步至关重要。

### 推荐的同步设计
1. **核心逻辑隔离**：保持插件目录下的 `overstats` 文件夹为纯净的上游镜像副本（对应上游的 `src` 和 `res` 目录）。
2. **轻量级数据库补丁**：因为插件禁用了数据库写入记录以保持轻量，对局数据的百分比统计（用于雷达图数据与颜色区分）通过 `overstats/res/match_stats_summary.json` 提供默认值。
3. **手动或脚本同步**：当上游发布新英雄或重要更新时：
   - 提取上游最新的 `src` 和 `res` 的最新代码与资源。
   - 覆盖到插件的 `overstats` 对应文件夹。
   - 修改新代码中的绝对引用（从 `src.*` 改为 `overstats.src.*`），这在 `paths.py` 以及 Python 动态导入 `try-except ModuleNotFoundError` 中已经做了兼容处理。

---

## 3. GitHub Actions 自动化构建与检查

在推送代码时自动运行语法分析和静态代码检查，确保合并的代码没有低级语法错误。

### 工作流配置（已创建）
已创建路径为 `.github/workflows/lint.yml` 的文件，内容如下：
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
        # 遇到语法错误或未定义名称时中止构建
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

---

## 4. 版本管理与 Release 策略

1. **语义化版本 (SemVer)**：遵循 `vX.Y.Z` 规范：
   - **主版本号 (Major)**：插件核心逻辑有破坏性变更，或者 AstrBot 插件接口出现重大不兼容更新。
   - **次版本号 (Minor)**：从上游同步引入了新特性或功能（例如同玩、排行榜、猜谜小游戏）。
   - **修订号 (Patch)**：上游 bug 修复，或者网易大神接口变动适配。
2. **更新插件元数据**：在发布新版本前，更新 `metadata.yaml` 中的 `version`：
   ```yaml
   name: astrbot_plugin_ow_dashen
   desc: 守望先锋大神数据查询插件，基于 Overstats 渲染与数据服务。
   version: 1.0.1
   ```
3. **GitHub Releases**：建议在发布时创建 GitHub Release，说明更新日志，并将最新的 `match_stats_summary.json` 文件打包或做补充说明。

---

## 5. 日常维护检查清单

* [ ] **接口失效风险**：网易大神接口有时会微调参数或安全机制。建议保留一个测试环境定期测试 `/ow 自检`。
* [ ] **缓存目录清理**：图片缓存会占用磁盘空间，用户端可以定期执行 `/ow 清理缓存` 以防磁盘空间过载。
* [ ] **用户问题跟踪**：关注 GitHub Issues。用户常见问题往往是 BattleTag 大小写填错、账号 token 过期失效等。
