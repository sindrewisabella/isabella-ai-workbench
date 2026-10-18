"""Read the header and newest loaded card subtrees, keeping fresh AX references.

Older cards are intentionally outside this scan window, not claimed as inspected.
The full reader remains the fallback when a sent person moves out of this window.
"""
from read_cards import parents_of, label, MAX_DEPTH, MAX_NODES, check_locked


def read_tail(mac, count=45):
    state = mac.ax.dump('BOSS直聘', max_depth=25, max_nodes=10000,
                        include_actions=True, include_settable=False)
    check_locked(state)
    shallow = state['nodes']
    if len(shallow) >= 10000:
        raise RuntimeError('列表外层读取达到上限')
    parents = parents_of(shallow)
    candidates = []
    for node in shallow:
        if node.get('role') != 'AXList' or node['depth'] < 20:
            continue
        children = [n for n in shallow if parents.get(n['element_index']) is node]
        if len(children) >= 5 and sum(n.get('role') == 'AXGroup' for n in children) >= 5:
            candidates.append((node, children))
    if len(candidates) != 1:
        raise RuntimeError('无法唯一定位人选列表，须用完整读取检查')
    _, roots = candidates[0]
    original = dict(mac._elements)
    selected = {n['element_index'] for n in roots[-count:]}
    fallback = set()
    # The fallback divider can precede this window: inspect one-text rows too.
    for root in roots:
        children = mac._copy_attribute(original[root['element_index']], 'AXChildren') or []
        if len(children) == 1:
            value = mac._copy_attributes(children[0], ('AXRole', 'AXTitle', 'AXValue'))
            if value['AXRole'] == 'AXStaticText' and '暂无符合牛人' in str(value.get('AXTitle') or value.get('AXValue') or ''):
                fallback.add(root['element_index'])
    selected |= fallback
    root_indices = {n['element_index'] for n in roots}
    combined, references = [], {}

    def add(node, element, depth):
        index = len(combined)
        combined.append({**node, 'element_index': index, 'depth': depth})
        references[index] = element

    skip_depth = None
    for node in shallow:
        if skip_depth is not None and node['depth'] > skip_depth:
            continue
        skip_depth = None
        index = node['element_index']
        if index in root_indices or node['depth'] == 25:
            skip_depth = node['depth']
            if index in root_indices and index not in selected:
                continue
            subtree = mac._snapshot_tree(original[index], max_depth=MAX_DEPTH - node['depth'],
                                         max_nodes=2000, include_menu_bar=False,
                                         include_actions=True, include_settable=False)
            if len(subtree) >= 2000:
                raise RuntimeError('单张人选卡片读取截断')
            elements = dict(mac._elements)
            for child in subtree:
                add(child, elements[child['element_index']], node['depth'] + child['depth'])
        else:
            add(node, original[index], node['depth'])
    if len(combined) >= MAX_NODES:
        raise RuntimeError('窗口读取达到上限')
    mac._elements = references
    state['nodes'] = combined
    state['scan_scope'] = f'last {count} loaded card rows; older rows not inspected'
    state['loaded_rows'] = len(roots)
    return state
