# BOSS Mac 桌面招聘 CLI

面向已登录 BOSS 直聘 Mac 客户端的页面适配与本机接口。代码通过 macOS 辅助功能读取推荐卡片，核对岗位、人选与筛选证据，默认演练，授权后才执行招呼。
这是历史招聘实践的桌面适配快照，不是 BOSS 官方 API，也不是网页 BOSS CLI 的等价替代。

## What / Why

把客户端上的重复操作组织为可检查的批次：先核对岗位和账号，再逐人读取、去重、执行与记录；未知结果停止，保留恢复依据。
网页与桌面结构不同，所以本仓库单独保留页面适配，而不复用网页按钮定位。

## 依赖与运行条件

- macOS、Python 3.12+、本人有权使用且保持登录的 BOSS Mac 客户端。
- `macos-harness` SDK。本快照适配本机历史测试过的 0.1.2 接口；上游后续 API 可能改变。
- 使用者需按 SDK 说明配置必要系统权限；电脑锁屏时停止。
- 当前岗位标题与筛选为历史运维／测试／增长岗位适配，不保证任意新岗位即插即用。不要把示例学历或关键词规则直接当作你的招聘标准。

## How · 先检查与演练

```sh
git clone https://github.com/sindrewisabella/boss-desktop-cli.git
cd boss-desktop-cli
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/api_client.py --help
```

SDK 需具备辅助功能树碰撞修复；`hash-collision.patch` 是历史修复差异，版本变化后先检查上游，不要盲目套补丁或重复修改。
无 UI 操作的本地测试见 [VALIDATION.md](VALIDATION.md)。随后由使用者按当前账号和岗位检查：

```sh
python scripts/api_client.py health
python scripts/api_client.py status
python scripts/api_client.py scan
python scripts/api_client.py run --batch-id example --request-id preview-1 --target 1
```

`health/status` 不发送；`scan` 读取页面；最后一条默认演练。只有当前任务明确授权、标准与范围核对后才使用 `--execute`。
客户端会按需启动仅监听 `127.0.0.1:49727` 的本机服务。`api/` 运行凭据自动生成，`runs/` 为私有台账，均不提交 Git。
同端口已有服务时先确认所属工作目录；鉴权不匹配会拒绝连接，不能复制其他目录的 token 来绕过。

## 实现与限制

- `read_cards.py` / `read_tail.py`：读取卡片及稳定身份。
- `jobs.py`：推荐页岗位识别与切换。
- `greet.py`：证据筛选、单次写入、回查与未知结果停止。
- `api_server.py` / `api_client.py`：本机鉴权、单写入者、请求去重和查询。
- `daily.py`：批次累计控制和中断状态。
- `resumes_desktop.py`：实验性简历状态盘点；求简历与接收附件写入仍被阻断，不能宣称完整回收已验收。

历史演练、本地测试与真实任务分别记录；平台按钮变化只是一层回执，仍需同人会话和权威数量核对。
不保证平台永不限制账号；遇验证码、身份歧义、额度异常、跨日或未知结果停止，不绕过平台验证。

## 复用输入

实际账号与岗位 ID、岗位标准、有效筛选证明、准确目标上限、明确操作范围和当次授权。多岗位适配需先核对 `jobs.py` 与 `greet.py`，不能只改岗位名称即假定可用。
公开仓库没有运行凭据、候选人、聊天记录、截图、原账号岗位配置或历史台账。

## 许可与相关项目

MIT 许可；SDK 和补丁来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
[BOSS 多岗位网页框架](https://github.com/sindrewisabella/boss-recruiting-template) · [脉脉招聘 CLI](https://github.com/sindrewisabella/maimai-recruiting-cli)
