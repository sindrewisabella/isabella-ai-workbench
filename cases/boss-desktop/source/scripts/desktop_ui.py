"""Observed desktop controls; no fixed screen coordinates or hidden endpoints."""
import re
import time

from read_cards import label, parents_of, read_state


def press_text(mac, text, *, role=None, prefix=False):
    state = read_state(mac)
    nodes = state['nodes']
    matches = [n for n in nodes if (label(n).startswith(text) if prefix else label(n) == text)
               and (role is None or n.get('role') == role)]
    if len(matches) != 1:
        raise RuntimeError(f'无法唯一定位控件：{text}')
    node = matches[0]
    parents = parents_of(nodes)
    target = node
    while target and 'AXPress' not in target.get('actions', []):
        target = parents.get(target['element_index'])
        if target and target.get('role') in ('AXWebArea', 'AXWindow'):
            target = None
    if target is None:
        # Raw click is reserved for these navigation controls, never a send.
        if text not in ('账号权益', '确定'):
            raise RuntimeError(f'控件未提供可执行动作：{text}')
        f = node.get('frame')
        if not f or f['width'] < 8 or f['height'] < 8:
            raise RuntimeError('导航控件尚未完整显示')
        mac.click(f['x'] + f['width'] / 2, f['y'] + f['height'] / 2,
                  app='BOSS直聘', coordinate_space='screen')
    else:
        mac.ax.perform(target['element_index'], 'AXPress')


def close_filter(mac):
    state = read_state(mac)
    if not state['nodes'] or not any(n.get('role') == 'AXWindow' for n in state['nodes']):
        raise RuntimeError('Mac已锁屏或BOSS窗口不可读，请解锁后继续')
    if not any(label(n) == '筛选条件' for n in state['nodes']):
        return
    press_text(mac, '确定', role='AXStaticText')
    time.sleep(.5)
    state = read_state(mac)
    if any(label(n) == '筛选条件' for n in state['nodes']):
        # The group AXPress is sometimes a no-op in this WebView. Use the newly
        # observed navigation label once; never reuse an old coordinate.
        n = next(n for n in state['nodes'] if label(n) == '确定' and n.get('role') == 'AXStaticText')
        f = n['frame']
        mac.click(f['x'] + f['width'] / 2, f['y'] + f['height'] / 2,
                  app='BOSS直聘', coordinate_space='screen')
        time.sleep(.5)
    if any(label(n) == '筛选条件' for n in read_state(mac)['nodes']):
        raise RuntimeError('筛选窗未能关闭，请在BOSS点击确定后继续')


def parse_quota(state):
    labels = [label(n).strip() for n in state['nodes'] if n.get('role') == 'AXStaticText']
    # A chat/CV can also contain 0/400: accept only an explicit entitlement
    # surface and the greeting/communication row directly beside its count.
    if not any(t in ('账号权益', '我的权益', '今日权益') for t in labels):
        raise RuntimeError('未打开账号权益面板')
    found = []
    for i, text in enumerate(labels):
        if not re.search(r'今日.*(?:沟通|招呼)|(?:沟通|招呼).*(?:今日|额度|次数)', text):
            continue
        nearby = ' '.join(labels[i:i + 5])
        match = re.search(r'(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)', nearby)
        if not match:
            match = re.search(r'(?<!\d)(\d+)\s*个?\s*[（(]\s*共\s*(\d+)\s*个?\s*[）)]', nearby)
        if match:
            found.append((int(match[1]), int(match[2])))
    values = set(found)
    if len(values) != 1:
        raise RuntimeError('未读到唯一的今日沟通已用/总额度，不能猜400或600')
    used, total = values.pop()
    if not 0 <= used <= total or total <= 0:
        raise RuntimeError('今日沟通额度数值无效')
    return dict(used=used, total=total, source='BOSS desktop entitlement panel')


def read_quota(mac):
    state = read_state(mac)
    try:
        return parse_quota(state)
    except RuntimeError:
        press_text(mac, '账号权益', role='AXStaticText')
    deadline = time.monotonic() + 12
    previous, stable = None, 0
    while time.monotonic() < deadline:
        state = read_state(mac)
        try:
            result = parse_quota(state)
            stable = stable + 1 if result == previous else 1
            previous = result
            if stable >= 2:
                return result
        except RuntimeError:
            pass
        time.sleep(1)
    raise RuntimeError('未能读取今日沟通总额度；请打开BOSS账号权益后重试，不购买权益')
