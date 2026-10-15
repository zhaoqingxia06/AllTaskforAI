# 任务档案

公开的个人跨平台任务档案。分类 → 主题/产品 → 任务，保留用户原始需求与后续补充，支持搜索、全文阅读与手机浏览。

## 更新方式

| 来源 | 写入位置 | 更新时机 |
| --- | --- | --- |
| 本机 Codex | `data/codex.json` | 每日北京时间 12:00，由本机已有自动化刷新并推送 |
| zcode 等其他平台 | `data/contributions/*.json` | 平台推送更新，或 PR 合并后 |
| 网页 | GitHub Pages | main 分支更新后由 Actions 自动部署 |

本机同步仅写 Codex 数据，不覆盖其他平台文件。设备离线时不产生新的 Codex 快照；已发布网站仍可访问。

给其他 Agent 的操作规范见 [CONTRIBUTING.md](CONTRIBUTING.md)，仓库级约束见 [AGENTS.md](AGENTS.md)。平台需要 GitHub 写入能力或 PR 能力；网址本身不是写入授权。

## 本地构建

Python 3.9+，仅标准库：

```sh
python3 scripts/build.py
python3 -m http.server 8080 --directory dist
```

`dist/index.html` 是可独立浏览的单文件；`dist/tasks.json` 是完整数据接口；`dist/feed.json` 是更新摘要。修改源码或数据即可，勿直接修改生成文件。

## 覆盖边界

Codex 数据来自一台 Mac 上可读取的会话（包含归档）。ChatGPT 网页历史和其他平台历史只有在另行导入后才出现。系统提示、心跳、子代理会话及内部测试不计作用户任务。执行状态与需求验收分开标注。

用户已明确选择公开全部任务及子任务原文；识别到的凭据继续隐藏。
