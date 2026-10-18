"""Read-only BOSS card/button inspection using the installed macOS harness."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re

from macos_harness.macos import MacOS

MAX_DEPTH = 80
MAX_NODES = 30000


def label(node):
    return str(node.get('title') or node.get('value') or node.get('description') or '')


def parents_of(nodes):
    parents, stack = {}, []
    for node in nodes:
        while stack and stack[-1]['depth'] >= node['depth']:
            stack.pop()
        parents[node['element_index']] = stack[-1] if stack else None
        stack.append(node)
    return parents


def inside(frame, window):
    if not frame or not window or frame['width'] < 20 or frame['height'] < 20:
        return False
    return (frame['x'] >= window['x'] and frame['y'] >= window['y']
            and frame['x'] + frame['width'] <= window['x'] + window['width']
            and frame['y'] + frame['height'] <= window['y'] + window['height'])


def inspect(state, target=None, internal=False):
    nodes = state['nodes']
    if len(nodes) >= MAX_NODES or any(n['depth'] >= MAX_DEPTH for n in nodes):
        raise RuntimeError('读取达到上限，不能把截断的列表用于人选判断。')
    parents = parents_of(nodes)
    fallback_start = next((n['element_index'] for n in nodes
                           if n.get('role') == 'AXStaticText' and '暂无符合牛人' in label(n)), None)
    cards = []
    for button in nodes:
        if button.get('role') != 'AXButton' or label(button) not in ('打招呼', '继续沟通'):
            continue
        card = button
        while parents.get(card['element_index']) is not None:
            parent = parents[card['element_index']]
            if parent.get('role') == 'AXList':
                break
            card = parent
        else:
            raise RuntimeError('发现招呼按钮，但无法确定所属人选列表。')
        start = nodes.index(card)
        end = start + 1
        while end < len(nodes) and nodes[end]['depth'] > card['depth']:
            end += 1
        subtree = nodes[start:end]
        related = [n for n in subtree if n.get('role') == 'AXButton'
                   and label(n) in ('打招呼', '继续沟通')]
        if len(related) != 1:
            raise RuntimeError('同一人选卡片有多个招呼按钮，停止推断。')
        texts = [label(n) for n in subtree if n.get('role') == 'AXStaticText' and label(n)]
        names = [label(n) for n in subtree if n.get('role') == 'AXImage'
                 and label(n) and label(n) in texts]
        names = list(dict.fromkeys(names))
        if len(names) != 1:
            raise RuntimeError('无法通过头像名称及卡片文字交叉确认唯一姓名。')
        if target and names[0] != target:
            continue
        ancestor = button
        while ancestor and ancestor.get('role') != 'AXWindow':
            ancestor = parents[ancestor['element_index']]
        window = ancestor.get('frame') if ancestor else None
        cards.append({
            'name': names[0],
            'card_fingerprint': hashlib.sha256('\n'.join(texts).encode()).hexdigest()[:16],
            'identity_context': list(dict.fromkeys(t for t in texts if len(t) < 100))[:80],
            'button': label(button),
            'button_depth': button['depth'],
            'supports_ax_press': 'AXPress' in button.get('actions', []),
            'fully_in_window': inside(button.get('frame'), window),
            'button_frame': button.get('frame'),
            'outside_saved_filters': fallback_start is not None and card['element_index'] > fallback_start,
        })
        if internal:
            education = []
            for i, value in enumerate(texts):
                if re.fullmatch(r'\d{4}', value) and i + 4 < len(texts) and re.fullmatch(r'\d{4}', texts[i + 1]):
                    end = next((j for j in range(i + 3, min(i + 7, len(texts)))
                                if texts[j] in ('本科', '学士', '硕士', '研究生', '博士', '专科', '大专', '高中')), None)
                    if end:
                        education.append({'start': int(value), 'end': int(texts[i + 1]),
                                          'school': texts[i + 2], 'major': ' '.join(texts[i + 3:end]),
                                          'degree': texts[end]})
            cards[-1].update(text='\n'.join(texts), education=education,
                             card_index=card['element_index'],
                             card_end_index=subtree[-1]['element_index'],
                             window_frame=window,
                             button_index=button['element_index'],
                             button_actions=button.get('actions', []))
            cards[-1]['identity'] = hashlib.sha256(json.dumps(
                [names[0], sorted(education, key=lambda e: (e['start'], e['school']))],
                ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if target and len(cards) != 1:
        raise RuntimeError(f'目标姓名匹配 {len(cards)} 张卡片，需要消除歧义。')
    return {
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'app': state['app'],
        'node_count': len(nodes),
        'max_observed_depth': max(n['depth'] for n in nodes),
        'filters': [label(n) for n in nodes if n.get('role') == 'AXStaticText'
                    and label(n).startswith('筛选')],
        'cards': cards,
        'warning': '只读结果；完整落在窗口内不代表未被弹窗遮挡。每次操作前须在同一进程重新读取并核对人选、岗位、筛选及当前遮挡。指纹仅用于本次卡片对照，不是平台人才ID。',
    }


def read_state(mac):
    state = mac.ax.dump('BOSS直聘', max_depth=MAX_DEPTH, max_nodes=MAX_NODES,
                        include_actions=True, include_settable=False)
    check_locked(state)
    return state


def check_locked(state):
    if len(state['nodes']) == 1 and state['nodes'][0].get('role') == 'AXApplication':
        from Quartz import CGSessionCopyCurrentDictionary
        if (CGSessionCopyCurrentDictionary() or {}).get('CGSSessionScreenIsLocked'):
            raise RuntimeError('Mac已锁屏，请解锁后继续；当前不可读不代表没有合适人选')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='只读核对 BOSS 客户端人选与按钮，不发送消息。')
    parser.add_argument('--target', help='按卡片完整姓名精确匹配；同名或未找到即停止。')
    args = parser.parse_args()
    print(json.dumps(inspect(read_state(MacOS()), args.target), ensure_ascii=False, indent=2))
