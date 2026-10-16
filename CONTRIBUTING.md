# 让其他 Agent 更新这个网站

把本仓库链接交给其他平台，并把下面这段话作为任务：

> 读取此仓库的 AGENTS.md 和 CONTRIBUTING.md。把我在当前平台发布的真实任务及后续消息写入 data/contributions/ 下属于本平台的 JSON 文件，保留其他平台已有数据。运行 python3 scripts/build.py 验证，它会合并所有平台并更新根目录 index.html；把平台数据与生成的 index.html 一起推送 main（有写权限）或提交 Pull Request。合并后工作流再次核对并重建同一个档案文件，托管由已有工作流处理，本步骤不更改托管配置。不得用单个平台HTML覆盖统一入口。

## 文件格式

例如 `data/contributions/zcode.json`：

```json
{
  "schema_version": 1,
  "source": "zcode",
  "tasks": [
    {
      "id": "replace-with-real-stable-task-id",
      "category": "做产品",
      "group": "实际产品名",
      "created_at": "2026-10-16T12:00:00+08:00",
      "updated_at": "2026-10-16T13:00:00+08:00",
      "status": "completed",
      "scheduled": false,
      "archived": false,
      "messages": [
        {"id": "m1", "time": "2026-10-16T12:00:00+08:00", "text": "用户的第一条原始需求"},
        {"id": "m2", "time": "2026-10-16T13:00:00+08:00", "text": "用户后续真实发送的补充"}
      ]
    }
  ]
}
```

以上仅为格式示例，不要把示例任务提交到正式数据。

- `source` 使用稳定的小写英文标识；`codex` 已保留给本机同步。可使用 `zcode`、`chatgpt` 等。
- 同一平台的任务 `id` 必须唯一且稳定。构建时自动加平台前缀，避免与其他平台冲突。
- 时间须为带时区的 ISO 8601。标题必须综合第一条需求和全部后续子任务，用一句话概括整段会话的工作范围，不能直接采用第一句或最后一句；没有原文的任务允许 `messages: []` 并提供 `title`，页面会注明缺原文。
- 状态允许 `completed`、`failed`、`inProgress`、`interrupted`、`unknown`。它表示执行状态，不表示用户验收。
- 已有任务追加消息时，更新原记录及 `updated_at`，不要创建第二份任务。
- 不同平台可使用不同文件；同一任务不能在两个文件中重复。
- 需要组描述时，修改 `data/curation.json` 的 `groups` 映射。

公开读取不需要登录。写入需要平台支持 GitHub 写权限，或通过 PR 提交并合并；只提供一个网址，不会自动授权平台读取聊天历史或写仓库。

## 数据接口

固定入口：[index.html](https://github.com/zhaoqingxia06/AllTaskforAI/blob/main/index.html)。它内嵌所有平台数据，可独立打开并下载全部任务 JSON。构建的 dist/tasks.json 和 dist/feed.json 可供本地工具核对数量与内容摘要。

## 任务标题总结

- 阅读任务的全部用户消息，提炼“做了什么、涉及哪些核心工作”，用一句话命名；不要因执行状态为完成就声称已经验收。
- 总结保存在 `data/curation.json` 的 `task_summaries`，以构建后的稳定任务 ID 为键；不修改任何平台的用户原文。
- 每项为 `{"text": "一句话总结", "messages_sha256": "摘要"}`。摘要计算方法：对按顺序排列的所有消息正文列表执行 `hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()`，其中 `texts` 取构建归一化后的 `messages`。
- 追加或修改子任务后，重新阅读全部消息并更新总结与摘要；构建会使过期总结失效，暂按全会话中的工作类型生成概括并标记 `summary_needs_review`，供下次整理复核。此兜底是规则提取，不是大模型语义总结。
- `source_title` 保留原始索引标题，`messages` 保留全部正文；页面与下载数据使用统一的总结标题。
