# Task archive contributor contract

This is the public task archive. Preserve every existing task and original user message.

- Data from local Codex is generated in `data/codex.json`. Do not edit it from other platforms.
- Add/update your own platform's files in `data/contributions/`. Use one stable file per platform or task.
- Read `CONTRIBUTING.md` before writing. Use stable source/task/message IDs. Update an existing task in place.
- Include real user requests only, not agent responses, tool calls, system prompts, or internal sub-agent work.
- The first message is the task itself; later messages are sub-tasks. Preserve non-consecutive repeats.
- Categories: 做产品 / 查询知识 / 生活攻略 / 工具配置 / 账号与支持 / 记录整理 / 定时自动化.
- Use the task's product/topic as `group`; scheduled is an independent boolean.
- Run `python3 scripts/build.py` before pushing or opening a PR. It merges ALL platforms into the single generated root `index.html`. Include that file when committing. The archive workflow rebuilds this same file after source changes; existing hosting configuration is preserved. Never replace it with a platform-only page.
- Do not manually edit generated `index.html` or `dist/` files. Do not add credentials, authentication exports, or local databases.
- Never overwrite another platform's contribution file or rewrite repository history.

- Task titles summarize ALL user messages in one sentence. Refresh `data/curation.json` task_summaries when messages change; follow CONTRIBUTING.md. Never use only the first message as the display title.
