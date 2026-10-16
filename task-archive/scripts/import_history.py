#!/usr/bin/env python3
"""Import explicit exports/local JSONL; never probes signed-in browser sessions."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()
    return value


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        parts = content.get('parts', [])
    else:
        parts = content or []
    return '\n'.join(p if isinstance(p, str) else p.get('text', '') for p in parts if isinstance(p, (str, dict))).strip()


def chatgpt(path):
    doc = json.loads(path.read_text())
    if isinstance(doc, dict):
        doc = doc.get('conversations', [doc])
    result = []
    for conv in doc:
        cid = conv.get('id') or conv.get('conversation_id')
        if not cid:
            raise ValueError('导出缺少稳定会话 ID')
        messages = []
        for node_id, node in conv.get('mapping', {}).items():
            m = node.get('message') or {}
            if m.get('author', {}).get('role') != 'user':
                continue
            text = text_of(m.get('content'))
            # Do not invent OCR for opaque multimodal parts.
            attachments = [p for p in m.get('content', {}).get('parts', []) if isinstance(p, dict) and not p.get('text')]
            if not text and attachments:
                text = '[附件消息：正文未提供，需结合附件理解]'
            if text:
                messages.append({'id': str(m.get('id') or node_id), 'role': 'user', 'text': text,
                                 'sent_at': timestamp(m.get('create_time')), 'attachments': attachments})
        result.append({'id': str(cid), 'title': conv.get('title', ''), 'messages': messages})
    return result


def codex(path):
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    meta = next((r.get('payload', {}) for r in records if r.get('type') == 'session_meta'), {})
    cid = meta.get('id')
    if not cid:
        raise ValueError('Codex JSONL 缺少 session_meta.id')
    if meta.get('source') in ('subagent', 'review') or isinstance(meta.get('source'), dict) and 'subagent' in meta['source']:
        return []
    messages = []
    for i, record in enumerate(records):
        payload = record.get('payload', {})
        if record.get('type') != 'response_item' or payload.get('type') != 'message' or payload.get('role') != 'user':
            continue
        text = text_of(payload.get('content'))
        if not text or text.lstrip().startswith(('<environment_context>', '<permissions instructions>', '# AGENTS.md instructions')):
            continue
        mid = payload.get('id') or hashlib.sha256((str(cid)+':'+str(i)).encode()).hexdigest()[:24]
        messages.append({'id': str(mid), 'role': 'user', 'text': text, 'sent_at': timestamp(record.get('timestamp'))})
    return [{'id': str(cid), 'messages': messages}]


def merge(old, incoming):
    conversations = {c['id']: c for c in old}
    for conv in incoming:
        if conv['id'] not in conversations:
            conversations[conv['id']] = conv
            continue
        previous = conversations[conv['id']]
        messages = {m['id']: m for m in previous['messages']}
        messages.update({m['id']: m for m in conv['messages']})
        previous.update({k:v for k,v in conv.items() if k!='messages'})
        previous['messages'] = list(messages.values())
    return list(conversations.values())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('format', choices=['chatgpt-export', 'codex-jsonl', 'normalized'])
    p.add_argument('input')
    p.add_argument('--output', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--client', default='unknown')
    p.add_argument('--scope', required=True, help='真实可读范围，例如用户导出截至某日期')
    args = p.parse_args()
    path = Path(args.input)
    if args.format == 'chatgpt-export':
        convs = chatgpt(path)
    elif args.format == 'codex-jsonl':
        convs = codex(path)
    else:
        convs = json.loads(path.read_text())['conversations']
    target = Path(args.output)
    old = json.loads(target.read_text()) if target.exists() else {}
    if old and (old['source'] != args.source or old.get('client', 'unknown') != args.client):
        raise ValueError('不得覆盖另一个来源或客户端的文件')
    output = {'schema_version': 2, 'source': args.source, 'client': args.client,
              'coverage': {'scope': args.scope}, 'conversations': merge(old.get('conversations', []), convs)}
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    temp.replace(target)
    print(json.dumps({'conversations':len(output['conversations']), 'messages':sum(len(c['messages']) for c in output['conversations'])}))


if __name__ == '__main__':
    main()
