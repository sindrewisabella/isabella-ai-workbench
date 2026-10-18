# 脉脉招聘 CLI · Maimai Recruiting CLI

把搜索、候选人资料补读、原文证据审阅、联系前预检和结果导出串成一个可检查的本地流程。
这是个人招聘实践中的核心适配代码快照，基于已登录的 Ego 浏览器页面工作；不是脉脉官方产品。

## What / Why

岗位、资料、联系历史和沟通额度分散在多个页面。工具保存当前页面证据，按岗位标准生成待审阅文件，防止把关键词命中直接当成合适人选。
代码与数据分开，换岗位时修改配置与要求，不携带原账号、Cookie、候选人或历史发送台账。

## 当前范围

- `search` / `collect`：读取当前岗位的搜索列表。
- `detail`：补读确定 UID 的在线资料，不下载附件。
- `screen`：提取检索线索，所有结论默认待审阅。
- `preflight`：打开并关闭联系弹窗，核对人选、岗位、额度和自动求简历开关，不发送。
- `prepare` / `approval` / `send`：检查完整批次、内容指纹、有效期、历史和预算。`send` 会真实发送，不自动重试。
- `recover`：读取“我发起”中已加载的列表；不等于全量聊天核对或附件简历回收。
- `posts` / `export`：社区样本读取与 CSV 导出。

这次发布只包含通用核心。内部按日期、特定名单写的调度和发送脚本未发布。
页面结构会变化；本地逻辑测试不证明当前网站适配或真实送达。没有平台认可的“永不封号”保证。

## How · 先配置，再只读试用

需要 Python 3.10+、已安装并配置的 Ego 浏览器（以其当前安装渠道为准），以及本人有权访问的脉脉招聘账号。
`ego-browser nodejs`、`taskSpace()` 等接口来自运行环境，不包含在本仓库；普通 Chrome 或 Node 不会自动提供它们。

```sh
git clone https://github.com/sindrewisabella/maimai-recruiting-cli.git
cd maimai-recruiting-cli
cp config.example.json config.json
python3 maimai_hr.py --help
python3 -m unittest discover -v
```

在 `config.json` 填入本次有效的浏览器任务空间、页面标签、真实岗位 ID 和标题，不能照抄示例。
浏览器须保持登录；同一页面只运行一个操作命令，执行中不要手动切换人选或岗位。

```sh
python3 maimai_hr.py search '你的关键词' --limit 10 --out data/search.json
python3 maimai_hr.py screen data/search.json --out data/reviews.draft.json
python3 maimai_hr.py export data/search.json --out data/search.csv
```

进一步操作见 [工作流说明](docs/workflow.md)、[Skill](SKILL.md)、[验证范围](VALIDATION.md)。

## 复用时由人提供

岗位 ID 与标题、筛选标准和证据要求、账号与浏览器访问、联系人范围、准确文案、当次预算及明确授权。
验证码、登录失效、身份变化、额度异常或结果未知时停止；发送结果不明先核对原会话，不能换文件重发。

## 来源与许可

MIT 许可适用于本仓库发布的代码。参考项目和运行依赖见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
本仓库不代表脉脉或其关联方；平台功能、账号权益和使用条款由平台决定。

相关作品：[BOSS 多岗位框架](https://github.com/sindrewisabella/boss-recruiting-template) · [BOSS Mac 桌面适配](https://github.com/sindrewisabella/boss-desktop-cli)
