# v2 数据契约与命令

本地构建工作目录（发布服务可不同）：archive.config.json、data/contributions/<platform-client>.json、data/catalog.json、scripts/archive.py、assets/site-template.html；.github/workflows/pages.yml 仅为可选部署配置。原始全量导出存站点外，不能提交。

## 初始化与采集

```
python3 <skill>/scripts/archive.py init <empty-site-directory>
python3 <skill>/scripts/import_history.py chatgpt-export <conversations.json> --output <private-working-copy>/chatgpt-web.json --source chatgpt --client web --scope "用户提供的导出；截至实际导出日期"
```

先本地提取，再由 LLM 过滤/脱敏，生成适合公开网站的 contributions；不要直接把全量导入结果复制到公开站点存储。对于纯确认与待整理消息，在公开文件中可省略，本地记录排除理由与原始 ID。其他平台同理。工具不主动扫描整个硬盘。

## 来源文件

```json
{
  "schema_version": 2,
  "source": "chatgpt",
  "client": "web",
  "coverage": {"scope": "用户提供的导出，非实时全账号历史"},
  "conversations": [{
    "id": "c1",
    "messages": [
      {"id":"m1","role":"user","text":"所有聊天共用保存目录。","sent_at":"2026-10-16T12:00:00+08:00"},
      {"id":"m2","role":"user","text":"引用块无法退出，修复一下。","sent_at":null}
    ]
  }]
}
```

sent_at 为带时区 ISO 8601、YYYY-MM-DD 或 null；未知不可推断。附件为可用引用列表，不生成虚构 OCR。消息 ref 为 `json.dumps([source, conversation_id, message_id], ensure_ascii=False, separators=(',', ':'))`；同一平台同一消息在不同客户端重复读取只存一个实体。

## LLM 编写 catalog

```json
{
  "schema_version": 2,
  "categories": [{"id":"product","name":"产品开发"}],
  "projects": [{"id":"chatnote","category_id":"product","name":"ChatNote","aliases":["Chat Note"],"description":"在 AI 对话旁摘录并编辑笔记的工具。"}],
  "requirements": [
    {"id":"shared-folder","project_id":"chatnote","summary":"所有聊天默认复用已选择的保存目录","message_refs":["[\"chatgpt\",\"c1\",\"m1\"]"],"evidence_sha256":"<运行 fingerprints 后复核填入>"},
    {"id":"exit-quote","project_id":"chatnote","summary":"修复引用块无法退出到正文的问题","message_refs":["[\"chatgpt\",\"c1\",\"m2\"]"],"evidence_sha256":"<运行 fingerprints 后复核填入>"}
  ],
  "excluded_messages": []
}
```

示例数据仅作说明，不提交到用户正式网站。对于上下文变化，先重读全部关联原文再修改摘要与引用。

```
python3 <site>/scripts/archive.py fingerprints <site>
python3 <site>/scripts/archive.py build <site>
```

fingerprints 只输出候选哈希，不自动写回；Agent 语义复核后填入 evidence_sha256。build 对缺失引用、陈旧摘要指纹、重复 ID、无时区日期等报错，旧页面保持不变。未知时间会原样标注。

输出：index.html 可独立打开，tasks.json 可下载；仅包含已关联公开原文，待整理与排除文本不内嵌。统计区分项目/需求/关联消息/待整理。筛选支持类别、来源和全文关键词。

status 可选 unknown/requested/in_progress/verified/cancelled；verified/cancelled 必须有 status_evidence_ref 指向关联用户原文，LLM 必须确认其语义确为验收/取消。scheduled 独立布尔值。note 可保存重要改口/待确认情况。

## 幂等与协作

import_history 只更新指定来源文件中相同 ID，不删除旧会话。build 不替 LLM 分类、不自动重命名类别。其他平台新接入后先读取已发布 catalog 的项目和需求 ID，增量维护同一 catalog；冲突时重新读取最新版本，使用版本检查避免覆盖。公开站点存储只存已审阅来源副本，本地完整来源保留各消息和排除记录。
