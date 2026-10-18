"""Read the BOSS desktop daily report already open in the app. No clicks."""
import json
import re
from datetime import datetime
from macos_harness.macos import MacOS
from read_cards import read_state, parents_of, label


def read_counts(state):
    nodes = state['nodes']
    if not any('/report/data-center' in str(n.get('url', '')) for n in nodes):
        raise RuntimeError('请先打开 BOSS 数据页')
    if not any(label(n).strip() == '今日数据' for n in nodes):
        raise RuntimeError('当前不是今日数据')
    if not any(label(n).startswith('全部职位') for n in nodes):
        raise RuntimeError('当前不是全部职位口径，不能直接与起点对比')
    parents = parents_of(nodes)
    headings = [n for n in nodes if n.get('role') == 'AXHeading' and label(n).startswith('我打招呼')]
    if len(headings) != 1:
        raise RuntimeError('无法唯一识别我打招呼指标')
    section = parents[headings[0]['element_index']]
    i = nodes.index(section) + 1
    values = []
    while i < len(nodes) and nodes[i]['depth'] > section['depth']:
        if nodes[i].get('role') == 'AXStaticText' and label(nodes[i]).strip().isdigit():
            values.append(int(label(nodes[i]).strip()))
        i += 1
    communications = [i for i, n in enumerate(nodes) if n.get('role') == 'AXStaticText' and re.fullmatch(r'沟通\s*>?', label(n).strip())]
    if not values or len(communications) != 1:
        raise RuntimeError('缺少招呼计数或沟通权益区域')
    used = next((int(label(n).strip()) for n in nodes[communications[0] + 1:]
                 if n.get('role') == 'AXStaticText' and label(n).strip().isdigit()), None)
    if used is None:
        raise RuntimeError('未读到沟通权益消耗')
    return {'observed_at': datetime.now().astimezone().isoformat(),
            'daily_greetings': values[0], 'communication_entitlements_used': used,
            'scope': '全部职位的今日数据；需与本轮开始时对比'}


if __name__ == '__main__':
    print(json.dumps(read_counts(read_state(MacOS())), ensure_ascii=False))
