#!/usr/bin/env python3
"""Validate source snapshots and build the public, standalone task archive."""
from __future__ import annotations
import hashlib
import collections
import json
from pathlib import Path
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from renderer import CATEGORIES, STATUS, render

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')


def read(path):
    return json.loads(path.read_text())


def safe_text(value):
    if not isinstance(value, str):
        raise ValueError('正文和标题必须是字符串')
    return re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b', '[凭据已隐藏]', value)


def date(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('时间必须包含时区')
    return parsed.astimezone(TZ).isoformat(timespec='seconds')


def normalize(entry, source, ids):
    local_id = str(entry['id'])
    if source == 'codex':
        tid = local_id
    else:
        tid = local_id if local_id.startswith(source + ':') else source + ':' + local_id
    if tid in ids:
        raise ValueError(f'任务ID冲突：{tid}。请更新原文件，不要复制同一任务。')
    ids.add(tid)
    category = entry.get('category', '做产品')
    if category not in CATEGORIES:
        raise ValueError(f'未知分类：{category}')
    status = entry.get('status', 'unknown')
    if status not in STATUS:
        raise ValueError(f'未知执行状态：{status}')
    for key in ('scheduled', 'archived'):
        if key in entry and type(entry[key]) is not bool:
            raise ValueError(f'{key}必须是JSON布尔值')
    created = date(entry['created_at'])
    updated = date(entry.get('updated_at', created))
    messages, mids = [], set()
    for i, m in enumerate(entry.get('messages', [])):
        mid = str(m.get('id', f'{tid}:m{i + 1}'))
        if mid in mids:
            raise ValueError(f'消息ID冲突：{tid} / {mid}')
        mids.add(mid)
        text = safe_text(m['text'])
        if not text.strip():
            raise ValueError('消息正文不能为空')
        when = date(m.get('time', created))
        attachments = m.get('attachments', [])
        repeat = m.get('repeat', 1)
        if type(repeat) is not int or repeat < 1:
            raise ValueError('repeat必须是正整数')
        item = dict(id=mid, text=text, time=when, attachments=attachments,
                    repeat=repeat, merged_ids=m.get('merged_ids', [mid]), last_time=date(m.get('last_time', when)))
        if messages and messages[-1]['text'] == text and messages[-1]['attachments'] == attachments:
            messages[-1]['repeat'] += repeat
            messages[-1]['last_time'] = item['last_time']
            messages[-1]['merged_ids'].extend(item['merged_ids'])
        else:
            messages.append(item)
    title = safe_text(messages[0]['text'].splitlines()[0] if messages else entry.get('title', '原文缺失'))
    title = re.sub(r'^#+\s*', '', title)
    title = re.sub(r'\[([^\]]+)\]\([^\n]+?\)', r'\1', title)
    # Only fields required by the public archive are exported.
    return dict(id=tid, source=source, title=title, created_at=created, updated_at=updated,
                category=category, group=safe_text(entry.get('group', '其他')),
                scheduled=bool(entry.get('scheduled', False)), archived=bool(entry.get('archived', False)),
                status=status, status_label=STATUS[status][1], messages=messages,
                children=max(0, len(messages) - 1), metadata_only=not bool(messages))


def collect():
    codex = read(ROOT / 'data/codex.json')
    ids, tasks = set(), []
    for entry in codex['tasks']:
        tasks.append(normalize(entry, 'codex', ids))
    for path in sorted((ROOT / 'data/contributions').glob('*.json')):
        document = read(path)
        source = document.get('source', '')
        if source == 'codex' or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', source):
            raise ValueError(f'{path.name} 的source不合法或使用了保留名称codex')
        for entry in document['tasks']:
            tasks.append(normalize(entry, source, ids))
    tasks.sort(key=lambda t: (t['created_at'], t['id']))
    coverage = codex['coverage'].copy()
    coverage['classification_pending'] = sum(t['group'] == '其他' for t in tasks)
    return tasks, coverage, codex


def page_data(page):
    match = re.search(r'<script id="archive-data" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError('正式HTML缺少内嵌档案数据')
    return json.loads(match[1])


def content_key(page):
    data = page_data(page)
    data.pop('generated_at', None)
    data.pop('comparison', None)
    page = re.sub(r'(<script id="archive-data" type="application/json">).*?(</script>)',
                  lambda m: m[1] + json.dumps(data, ensure_ascii=False, sort_keys=True) + m[2], page, flags=re.S)
    page = re.sub(r'(<div class="edition">最近整理<time>)[^<]*(</time>)', r'\1CHECK_TIME\2', page, count=1)
    return re.sub(r'(<div class="comparison">)[^<]*(<br>)', r'\1RUN_DELTA\2', page, count=1)


def main():
    tasks, coverage, codex = collect()
    entry = ROOT / 'index.html'
    previous_page = entry.read_text() if entry.exists() else None
    previous = page_data(previous_page) if previous_page else {}
    current_ids = {t['id'] for t in tasks}
    if {t['id'] for t in previous.get('tasks', [])} - current_ids:
        raise ValueError('合并任务减少，保留旧入口；先核实来源文件是否缺失')
    public, data = render(tasks, coverage, previous, read(ROOT / 'data/curation.json'))
    if public.count('class="task" data-id=') != len(tasks):
        raise ValueError('任务行数不匹配')
    # One canonical entry, shared by every source and the local copy. Keep the
    # previous bytes when only check time / comparison text changed.
    if previous_page and content_key(public) == content_key(previous_page):
        public, data = previous_page, previous
    else:
        temporary = entry.with_suffix('.html.tmp')
        temporary.write_text(public)
        temporary.replace(entry)
    data['source_updated_at'] = max((t['updated_at'] for t in tasks), default=codex['generated_at'])
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    (dist / 'index.html').write_text(public)
    (dist / '.nojekyll').write_text('')
    (dist / 'tasks.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    digest = hashlib.sha256(json.dumps(tasks, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    feed = dict(schema_version=1, generated_at=data['generated_at'], source_updated_at=codex['generated_at'],
                tasks=data['stats']['tasks'], children=data['stats']['children'], messages=data['stats']['messages'],
                sources=sorted(set(t['source'] for t in tasks)),
                source_counts=dict(collections.Counter(t['source'] for t in tasks)),
                content_sha256=digest, data_url='./tasks.json')
    (dist / 'feed.json').write_text(json.dumps(feed, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(feed, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError) as e:
        sys.exit(f'构建失败，保留上一线上版本：{e}')
