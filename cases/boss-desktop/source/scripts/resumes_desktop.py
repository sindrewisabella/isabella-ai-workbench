"""Desktop resume workflow. Only verified today's test-role conversations qualify.

Live UI capability must be calibrated before enabling this adapter. Pure decision
logic is usable for read-only inspection and does not infer receipt from a click.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import time

from greet import BASE, ROLE
from read_cards import label, parents_of, read_state
from desktop_ui import press_text


def decision(text, *, request_enabled=False):
    if re.search(r'对方想发送附件简历.*(?:是否同意|给您)', text):
        return 'accept_attachment'
    if re.search(r'简历已接收|已接收附件简历|点击预览附件简历', text):
        return 'already_received'
    if re.search(r'简历请求已发送|方便发一份简历过来吗', text):
        return 'already_requested'
    return 'request_resume' if request_enabled else 'unavailable'


def subtree(nodes, root):
    start = nodes.index(root)
    end = start + 1
    while end < len(nodes) and nodes[end]['depth'] > root['depth']:
        end += 1
    return nodes[start:end]


def rows(state, date):
    nodes = state['nodes']
    parents = parents_of(nodes)
    found = []
    for node in nodes:
        parent = parents.get(node['element_index'])
        if node.get('role') != 'AXGroup' or not parent or parent.get('role') != 'AXList':
            continue
        contents = subtree(nodes, node)
        texts = [label(n) for n in contents if n.get('role') == 'AXStaticText' and label(n)]
        names = {label(n) for n in contents if n.get('role') == 'AXImage' and label(n) in texts}
        if len(names) != 1:
            continue
        name = names.pop()
        text = '\n'.join(texts)
        # Scope is today's updated conversations, never every historical role.
        is_today = any(re.fullmatch(r'(?:今天\s*)?\d{1,2}:\d{2}', t) or t == date for t in texts)
        if not is_today or ROLE not in text:
            continue
        key = hashlib.sha256((name + '\n' + ROLE).encode()).hexdigest()
        found.append(dict(identity=key, name=name, element_index=node['element_index']))
    counts = Counter(r['name'] for r in found)
    return [r for r in found if counts[r['name']] == 1]


def chat_panel(state, name):
    nodes = state['nodes']
    candidates = []
    for node in nodes:
        if node.get('role') != 'AXGroup':
            continue
        contents = subtree(nodes, node)
        texts = [label(n) for n in contents if n.get('role') == 'AXStaticText']
        if name not in texts or not any(ROLE in t for t in texts):
            continue
        if any(n.get('role') == 'AXList' for n in contents):
            continue
        if not any(label(n) == '求简历' for n in contents):
            continue
        candidates.append(contents)
    if not candidates:
        raise RuntimeError('当前会话身份和应聘岗位无法在独立聊天区域交叉确认')
    return min(candidates, key=len)


def consent_button(panel):
    candidates = []
    for node in panel:
        if node.get('role') != 'AXGroup':
            continue
        contents = subtree(panel, node)
        text = ' '.join(label(n) for n in contents if n.get('role') == 'AXStaticText')
        if not re.search(r'对方想发送附件简历.*(?:是否同意|给您)', text):
            continue
        buttons = [n for n in contents if label(n) == '同意' and 'AXPress' in n.get('actions', []) and n.get('enabled', True)]
        if len(buttons) == 1:
            candidates.append((len(contents), buttons[0]))
    if not candidates:
        raise RuntimeError('附件简历请求未能唯一绑定同意按钮')
    return min(candidates, key=lambda pair: pair[0])[1]


def process_chat(mac, row, execute, audit):
    state = read_state(mac)
    panel = chat_panel(state, row['name'])
    text = ' '.join(label(n) for n in panel if n.get('role') == 'AXStaticText')
    request = [n for n in panel if label(n) == '求简历' and 'AXPress' in n.get('actions', []) and n.get('enabled', True)]
    action = decision(text, request_enabled=len(request) == 1)
    if not execute or action in ('already_received', 'already_requested', 'unavailable'):
        return action
    # This adapter is gated until a real desktop conversation has been verified;
    # an offline test or browser implementation is not proof of desktop binding.
    raise RuntimeError('桌面求简历/收简历按钮尚未完成单会话实测，保留盘点结果，不盲点')


def collect(mac, *, date, execute=False, status_path=None):
    result = dict(date=date, checked=0, requested=0, received=0, pending_found=0,
                  scanned_to_bottom=False, verified_no_remaining=False, counts={})
    counts, seen = Counter(), set()
    try:
        state = read_state(mac)
        links = [n for n in state['nodes'] if n.get('role') == 'AXLink' and
                 str(n.get('url', '')).endswith('/web/client/index')]
        if len(links) != 1:
            raise RuntimeError('无法唯一定位桌面消息入口')
        mac.ax.perform(links[0]['element_index'], 'AXPress')
        time.sleep(1)
        for page in range(120):
            state = read_state(mac)
            current = rows(state, date)
            for row in current:
                if row['identity'] in seen:
                    continue
                # Reread before selecting; row indices never cross snapshots.
                refreshed = [r for r in rows(read_state(mac), date) if r['identity'] == row['identity']]
                if len(refreshed) != 1:
                    raise RuntimeError('会话重排后无法唯一定位同一人选')
                mac.ax.perform(refreshed[0]['element_index'], 'AXPress')
                time.sleep(.5)
                action = process_chat(mac, row, execute, None)
                counts[action] += 1
                seen.add(row['identity'])
                result['checked'] += 1
                result['counts'] = dict(counts)
            state = read_state(mac)
            # Without a successfully parsed conversation, an end label alone
            # cannot prove that the parser traversed the real conversation list.
            if seen and any(label(n) == '没有更多了' for n in state['nodes']):
                result['scanned_to_bottom'] = True
                break
            footers = [n for n in state['nodes'] if label(n) == '滚动加载更多' and 'AXScrollToVisible' in n.get('actions', [])]
            if len(footers) != 1:
                raise RuntimeError('会话列表或翻页入口未完成桌面校准，不能宣称无遗漏')
            mac.ax.perform(footers[0]['element_index'], 'AXScrollToVisible')
            time.sleep(1)
        result['pending_found'] = counts['accept_attachment']
        result['state'] = 'preview_only'
        if execute:
            raise RuntimeError('桌面简历回收仍需解锁后的实际会话校准；未把只读盘点当作回收完成')
        return result
    finally:
        result['checked_at'] = datetime.now().astimezone().isoformat()
        if status_path:
            Path(status_path).write_text(json.dumps(result, ensure_ascii=False, indent=2))
