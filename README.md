# 爆款文案自动抓取 - GitHub Actions 版

## 特点
- ✅ **零成本**：GitHub Actions 免费额度每月2000分钟，完全够用
- ✅ **零封号风险**：不登录任何平台，只抓公开聚合数据
- ✅ **全自动**：每天定时运行，自动提交数据到仓库
- ✅ **双备份**：本地JSON + 钉钉表格（可选）

## 快速开始

### 1. 创建仓库
在自己的 GitHub 账号下创建一个新仓库，上传这些文件：
- `.github/workflows/crawl.yml`
- `safe_crawler.py`
- `.gitignore`

### 2. 配置 Secrets（可选，用于钉钉表格）
仓库 Settings → Secrets and variables → Actions → New repository secret：

| Secret 名称 | 说明 |
|------------|------|
| `DINGTALK_APP_KEY` | 钉钉应用 AppKey |
| `DINGTALK_APP_SECRET` | 钉钉应用 AppSecret |
| `DINGTALK_SHEET_ID` | 钉钉表格 ID |
| `DINGTALK_SHEET_NAME` | 工作表名称，默认 Sheet1 |

> 不配置钉钉也完全可用，数据自动保存到 `data/` 目录。

### 3. 手动触发测试
Actions 页面 → "每日爆款文案抓取" → Run workflow

### 4. 查看数据
- `data/latest.json` — 最新汇总（固定路径，Skill 直接读取）
- `data/safe_hot_YYYYMMDD_HHMMSS.json` — 每次运行备份

## 数据格式示例

```json
{
  "platform": "小红书",
  "topic": "热榜",
  "content": "求求了这5个习惯真的让我从120斤瘦到95斤！",
  "likes": "12.5万",
  "author": "",
  "link": "https://tophub.today/...",
  "fetch_time": "2026-05-28 14:30",
  "tags": "社区",
  "hooks": "数字锚定, 情绪:求求",
  "structure": "热榜标题",
  "rank": "1"
}
```

## 接入 Claude Code Skill

Skill 直接读取固定路径的 `data/latest.json`：

```python
import json
import os

data_path = os.path.expanduser("~/.claude/skills/data/latest.json")
with open(data_path, 'r', encoding='utf-8') as f:
    hot_data = json.load(f)

# 按平台筛选
xhs_data = [d for d in hot_data if d['platform'] == '小红书']
```

## 定时设置

默认每天运行两次（北京时间 9:00 和 21:00）。

编辑 `.github/workflows/crawl.yml`：
```yaml
schedule:
  - cron: '0 1,13 * * *'  # UTC 时间 +8小时 = 北京时间
```
