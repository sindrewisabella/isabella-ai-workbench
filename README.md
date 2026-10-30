# isabella · AI 个人工作台

把实际工作中的问题，做成可用、可复用的小工具。这里保存个人展示网站代码，以及按文件夹整理的案例与 Skill 使用说明。

**[打开公开网站](https://sindrewisabella.github.io/isabella-ai-workbench/) · [案例目录](cases/) · [Skill 目录](skills/)**

## 仓库里有什么

```text
website/                 完整静态网站、交互示例与公开素材
cases/<case-id>/         33 条案例各自的说明、结构化资料、流程图与演示入口
  source/                三个招聘 CLI 另附既有公开版代码与许可证
skills/<skill-id>/       25 个关联 Skill 各自的使用说明和虚构示例
scripts/                 更新公开快照与结构校验
manifest.json            案例、Skill 与 CLI 来源清单
```

首页精选 **5 个完整案例**，目录保留全部 33 条作品记录及关联模块、方法与试验；不是 33 个独立上线系统。25 个 Skill 文件夹发布的是公开使用说明，不将已安装工具或第三方方法一概算作原创源码。

## 在电脑上运行网站

需要 Python 3。下载仓库后，在仓库目录运行：

```sh
python3 -m http.server 8000 --directory website
```

浏览器打开 **http://localhost:8000/**。无需 Node 安装或构建；页面通过 HTTP 读取 JSON，请使用上面的服务方式。

若要同时浏览 `cases/*/demo.html` 入口，从仓库根目录启动：

```sh
python3 -m http.server 8000
```

然后打开 **http://localhost:8000/website/**。

## 案例怎样讲清楚

每个案例都分别写出：为什么做、原来怎么工作、现在人做什么、AI 做什么、实际效果、怎样复用。来源、个人贡献、未验收能力和虚构示例分别标注。

目前精选笔试工作台、招聘 CLI、批量简历评估、薪酬计算器与全栈招聘数据看板，其他用途说明保留在目录。网站包含 7 篇从个人分享文档摘选或整理的 AI × HR 工作手记，以及注明核查日期的行业观察。

## 可以运行到什么程度

- **网站与公开 Demo：** 静态页面直接运行；示例使用虚构数据，公开交互在访客浏览器内进行，不写入公司系统。
- **三个招聘 CLI：** 代码分别放在 `cases/cli/source/`、`cases/maimai/source/`、`cases/boss-desktop/source/`，保留原安装与验证说明。依赖平台账号、权限及浏览器环境，下载不等于已连接或获准操作。
- **公司内部工具：** 本仓库发布其公开说明与浏览器演示；不包含生产数据库、私有后端、候选人资料、登录态或账号配置。
- **Skill：** 每项独立目录给出 What / Why / How 和示例。公开使用说明不能替代原系统的运行依赖；第三方基础与个人适配分别归因。

招聘 CLI 本次录屏对应 3 个已送达招呼、2 次求简历和 5 份接收附件，来自不同会话，不能计算同批转化率。收简历视频包含 1 次完整接收与 2 个已接收会话的结果回看，不是 5 次点击实录。历史账号统计作为折叠补充，不全部归为 CLI 贡献。薪酬截图／视频的真实 AI 识别尚未完成验收，公开页使用虚构材料与预置提取结果。

## 以后怎样更新

当前网站版本为 2026-10-30。案例和 Skill 结构化资料未变时，推荐用 `--website-only` 按公开文件白名单更新 `website/`，保留 `cases/`、`skills/` 和 `manifest.json`，然后检查公开包：

```sh
python3 scripts/sync_from_public.py --website-only path/to/reviewed-static-site
python3 scripts/verify.py
```

案例或 Skill 资料有变化时，省略 `--website-only` 执行完整同步，同时更新网站、案例、Skill 和清单。完整同步的快照日期默认使用当前日期，也可用 `--snapshot-date YYYY-MM-DD` 指定。

核对变化后提交并推送 `main`。GitHub Actions 会检查公开包，并将 `website/` 自动部署到 GitHub Pages；成功后才代表网站已更新。仅发布静态导出，不上传研究目录、原始招聘录像、运行状态或本地源码依赖。部署记录见仓库 Actions 中的 `Publish personal website`。

## 许可证与来源

原创代码使用 [MIT](LICENSE)。第三方代码按各子目录原许可证；个人文稿、插画、音视频等素材的使用范围见 [NOTICE.md](NOTICE.md)。作品参考了既有工具与开源能力，不将全部底层实现视为个人原创。
