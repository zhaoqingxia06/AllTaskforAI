from __future__ import annotations
import collections
import datetime as dt
import html
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo
TZ=ZoneInfo("Asia/Shanghai")
WORK=Path(__file__).resolve().parents[1]/"web"
CATEGORIES=['做产品','查询知识','生活攻略','工具配置','账号与支持','记录整理','定时自动化']
STATUS={'completed':('done','完成'),'failed':('error','出错'),'inProgress':('running','进行中'),'interrupted':('unknown','已中断'),'unknown':('unknown','待核实')}


def esc(value):
    return html.escape(str(value), quote=True)

def message_button(t, m, i):
    label = '任务原文' if i == 0 else f'子任务 {i}'
    repeated = f' · 连续重复 {m["repeat"]} 次已合并' if m['repeat'] > 1 else ''
    when = m['time'][:16].replace('T', ' ')
    return f'''<button class="message" data-task="{esc(t['id'])}" data-index="{i}" aria-label="查看{label}全文">
      <span class="message-meta">{label}<time datetime="{esc(m['time'])}">{when}</time>{repeated}</span>
      <span class="message-text">{esc(m['text'])}</span><span class="read-more">查看全文</span></button>'''

def render(tasks, coverage, previous, curation):
    now = dt.datetime.now(TZ).isoformat(timespec='seconds')
    stats = dict(tasks=len(tasks), children=sum(t['children'] for t in tasks), messages=sum(len(t['messages']) for t in tasks))
    counts = collections.Counter(t['category'] for t in tasks)
    tab = '<button role="tab" id="tab-all" aria-controls="archive-panel" aria-selected="true" tabindex="0" data-category="all">全部 <span>' + str(len(tasks)) + '</span></button>'
    for i, cat in enumerate(CATEGORIES):
        tab += f'<button role="tab" id="tab-{i}" aria-controls="archive-panel" aria-selected="false" tabindex="-1" data-category="{cat}">{cat} <span>{counts[cat]}</span></button>'
    sections = []
    for category in CATEGORIES:
        selected = [t for t in tasks if t['category'] == category]
        if not selected:
            continue
        groups = {}
        for t in selected:
            groups.setdefault(t['group'], []).append(t)
        group_blocks = []
        for group, entries in groups.items():
            desc = curation.get('groups', {}).get(group, '尚待识别明确主题，下一次刷新继续归类。' if group == '其他' else '围绕这一主题发起的需求与后续补充。')
            rows = []
            for t in entries:
                cls, status_label = STATUS.get(t['status'], STATUS['unknown'])
                src = t.get('source', 'codex')
                src_label = {'codex': 'Codex', 'zcode': 'ZCode'}.get(src, src[:1].upper() + src[1:])
                marks = f'<span class="badge src {esc(src)}">{src_label}</span>'
                marks += ('<span class="badge scheduled">定时</span>' if t['scheduled'] else '') + ('<span class="badge">已归档</span>' if t['archived'] else '')
                marks += f'<span class="dot {cls}" role="img" aria-label="会话{status_label}" title="会话执行状态：{status_label}"></span>'
                marks += f'<span class="sub-count" title="{t["children"]} 条子任务">{t["children"]}</span><span class="chevron" aria-hidden="true">⌄</span>'
                body = ''.join(message_button(t, m, i) for i, m in enumerate(t['messages']))
                if not body:
                    body = '<p class="unavailable">仅有任务索引；未找到可读取的用户消息，标题暂用索引标题。</p>'
                created = t['created_at'][:16].replace('T', ' ')
                updated = t['updated_at'][:16].replace('T', ' ')
                rows.append(f'''<details class="task" data-id="{esc(t['id'])}"><summary class="task-row">
                <time datetime="{esc(t['created_at'])}">{created}</time><span class="task-title" title="{esc(t['title'])}">{esc(t['title'])}</span><span class="markers">{marks}</span></summary>
                <div class="task-body"><div class="task-meta"><span>更新 {updated}</span><span>会话{status_label}</span><span>{esc(t.get('source', 'codex'))}</span><span class="task-id">{esc(t['id'])}</span></div>{body}</div></details>''')
            group_blocks.append(f'<section class="group" data-group="{esc(group)}"><header class="group-heading"><div><h3>{esc(group)}<span class="group-count">{len(entries)} 条</span></h3><p>{esc(desc)}</p></div></header>{"".join(rows)}</section>')
        sections.append(f'<section class="category" data-category="{category}"><header class="category-heading"><h2>{category}</h2><span>{len(selected)} 个任务</span></header><div class="category-content">{"".join(group_blocks)}</div></section>')
    date_start = min(t['created_at'][:10] for t in tasks)
    date_end = max(max(t['updated_at'][:10], t['created_at'][:10]) for t in tasks)
    old_tasks = {t['id']: t for t in previous.get('tasks', [])}
    new_ids = {t['id'] for t in tasks} - old_tasks.keys()
    removed = old_tasks.keys() - {t['id'] for t in tasks}
    changed = [t['id'] for t in tasks if t['id'] in old_tasks and t != old_tasks[t['id']]]
    delta = {k: stats[k] - previous.get('stats', {}).get(k, 0) for k in stats}
    comparison = (f'较上次：任务 {delta["tasks"]:+d}，子任务 {delta["children"]:+d}' if previous else '随仓库更新自动发布')
    src_counts = collections.Counter(t['source'] for t in tasks)
    src_labels = {'codex': 'Codex', 'zcode': 'ZCode', 'chatgpt': 'ChatGPT'}
    sources_line = '<span class="sep range-sep">·</span>'.join(
        f'<span>{esc(src_labels.get(src, src))} <strong>{n}</strong></span>'
        for src, n in sorted(src_counts.items()))
    source_counts = dict(src_counts)
    data = dict(schema_version=1, generated_at=now, source='跨平台任务档案', timezone='Asia/Shanghai',
        source_counts=source_counts,
        stats=stats, tasks=tasks, comparison=dict(has_previous=bool(previous), delta=delta,
        new_tasks=sorted(new_ids), changed_tasks=changed, removed_tasks=sorted(removed)))
    # Escape HTML-sensitive codepoints; user text is never interpreted as markup/script.
    inline = json.dumps(data, ensure_ascii=False).replace('<', r'\u003c').replace('>', r'\u003e').replace('&', r'\u0026')
    values = {'TABS': tab, 'SECTIONS': ''.join(sections), 'DATA': inline,
        'START': date_start.replace('-', '.'), 'END': date_end.replace('-', '.'),
        'TASKS': str(stats['tasks']), 'CHILDREN': str(stats['children']),
        'UPDATED': now[:16].replace('T', ' '), 'COMPARISON': comparison, 'SOURCES': sources_line,
        'EXCLUDED': str(len(coverage['excluded'])), 'SYSTEM': str(coverage['system_messages']),
        'DUPLICATES': str(coverage['consecutive_duplicates']),
        'PENDING': str(coverage['classification_pending']),
        'METADATA': str(len(coverage['metadata_only']))}
    output = (WORK / 'template.html').read_text()
    output = re.sub(r'\{\{([A-Z]+)\}\}', lambda m: values[m[1]], output)
    if output.count('class="task" data-id=') != len(tasks):
        raise ValueError('HTML行数与任务数不相等')
    return output, data
