"""Navigate observed BOSS recommendation jobs; never sends a greeting."""
import re
from collections import Counter
import subprocess
import time
from urllib.parse import urlparse, parse_qs

from read_cards import label, parents_of, read_state, check_locked

JOB = re.compile(
    r'^(?:(?:运维|测试)工程师（外包）(?:-厦门)?|增长工程师（[^）]+）)'
    r'\s*_\s*\S+\s+\d+-\d+K$'
)


def shallow(mac):
    state = mac.ax.dump('BOSS直聘', max_depth=25, max_nodes=10000,
                        include_actions=True, include_settable=False)
    check_locked(state)
    return state


def context(state):
    if any(n.get('role') == 'AXWebArea' and '/web/frame/c-resume/' in str(n.get('url', '')) for n in state['nodes']):
        raise RuntimeError('简历弹层尚未关闭，不能操作背后的人选按钮')
    frames = [n for n in state['nodes'] if n.get('role') == 'AXWebArea'
              and '/web/frame/recommend/' in str(n.get('url', ''))]
    headers = [label(n) for n in state['nodes'] if n.get('role') == 'AXStaticText'
               and JOB.fullmatch(label(n))]
    if len(frames) != 1 or len(headers) != 1:
        raise RuntimeError('当前岗位不符或推荐页未就绪，不能据此判断无人符合')
    ids = parse_qs(urlparse(frames[0]['url']).query).get('jobid', [])
    if len(ids) != 1 or not ids[0]:
        raise RuntimeError('无法读取当前岗位编号')
    return {'job_id': ids[0], 'title': headers[0]}


def open_recommendations(mac):
    state = shallow(mac)
    if not any(n.get('role') == 'AXWindow' for n in state['nodes']):
        subprocess.run(['osascript', '-e', 'tell application "/Applications/BOSS直聘.app" to activate'], check=True, capture_output=True)
        for _ in range(20):
            time.sleep(.5)
            state = shallow(mac)
            if any(n.get('role') == 'AXWindow' for n in state['nodes']):
                break
    try:
        return context(state)
    except RuntimeError:
        pass
    links = [n for n in state['nodes'] if n.get('role') == 'AXLink' and label(n) == '推荐']
    if len(links) != 1:
        raise RuntimeError('无法唯一定位推荐入口；检查客户端窗口或登录状态')
    mac.ax.perform(links[0]['element_index'], 'AXPress')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        state = shallow(mac)
        try:
            return context(state)
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError('推荐页面未就绪或岗位不符')


def dropdown(mac):
    """Read the live job dropdown, retrying menu expansion after redraws."""
    last = None
    for attempt in range(4):
        try:
            state = read_state(mac)
            matches = [n for n in state['nodes'] if n.get('role') == 'AXStaticText' and JOB.fullmatch(label(n))]
            parents = parents_of(state['nodes'])
            # When the menu is already open, options are additional job titles.
            if len(matches) > 1:
                return state, [(label(n), parents[n['element_index']]) for n in matches[1:]]
            current = context(state)
            header = next(n for n in state['nodes'] if n.get('role') == 'AXStaticText' and label(n) == current['title'])
            parent = parents[header['element_index']]
            if 'AXPress' not in parent.get('actions', []):
                raise RuntimeError('岗位选择控件不可操作')
            mac.ax.perform(parent['element_index'], 'AXPress')
            time.sleep(0.8 + attempt * 0.4)
            state = read_state(mac)
            parents = parents_of(state['nodes'])
            matches = [n for n in state['nodes'] if n.get('role') == 'AXStaticText' and JOB.fullmatch(label(n))]
            if len(matches) >= 2:
                return state, [(label(n), parents[n['element_index']]) for n in matches[1:]]
            last = '岗位下拉列表未能读取'
        except RuntimeError as e:
            last = str(e)
            time.sleep(0.8 + attempt * 0.4)
    raise RuntimeError(last or '岗位下拉列表未能读取')

def select_job(mac, position, expected_titles):
    state, options = dropdown(mac)
    observed = [t for t, _ in options]
    # Titles are not unique: two Shenzhen operations jobs can have identical
    # text while carrying different job ids.  Compare the observed menu as a
    # multiset and choose by the freshly observed option position.
    expected_options = list(expected_titles[1:]) if len(expected_titles) == len(observed) + 1 else list(expected_titles)
    if Counter(observed) != Counter(expected_options):
        raise RuntimeError('岗位列表内容发生变化，停止选择以免发到错误岗位')
    if position >= len(options):
        raise RuntimeError('目标岗位不在当前下拉列表')
    title, node = options[position]
    if node is None:
        raise RuntimeError('目标岗位不在当前下拉列表')
    if 'AXPress' not in node.get('actions', []):
        raise RuntimeError('岗位选项不可操作')
    mac.ax.perform(node['element_index'], 'AXPress')
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        time.sleep(.5)
        try:
            result = context(shallow(mac))
            # A successful switch must load a recommendation frame and a
            # non-empty job id.  For duplicate titles, the id change is the
            # authoritative identity check.
            previous = getattr(mac, '_boss_expected_job', None)
            if result['title'] == title and (not previous or result['job_id'] != previous.get('job_id')):
                mac._boss_expected_job = result
                mac._boss_expected_filter = None
                return result
        except RuntimeError:
            pass
    raise RuntimeError('岗位切换未能读回确认')


def list_jobs(mac):
    state, options = dropdown(mac)
    # Select the first observed option to close the menu deterministically.
    mac.ax.perform(options[0][1]['element_index'], 'AXPress')
    time.sleep(1)
    context(shallow(mac))
    return [t for t, _ in options]
