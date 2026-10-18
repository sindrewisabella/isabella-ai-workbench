#!/usr/bin/env python3
"""Update the public snapshot from an explicitly selected static website directory."""
import argparse, json, shutil, html
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path, help='Static website folder containing index.html and assets/catalog.json')
a = p.parse_args(); source = a.source.resolve()
if not (source/'index.html').is_file() or not (source/'assets/catalog.json').is_file():
    p.error('Select the public static website folder; do not select a private project or home directory.')
if source != (ROOT/'website').resolve():
    shutil.copytree(source, ROOT/'website', dirs_exist_ok=True)
website = ROOT/'website'; data = json.loads((website/'assets/catalog.json').read_text())
manifest = json.loads((ROOT/'manifest.json').read_text()); manifest['caseCount'] = len(data['cases']); manifest['skillCount'] = len(data['skills'])
manifest['cases'] = []; manifest['skills'] = []
source_ids = {x['caseId'] for x in manifest['sourceSnapshots']}
for c in data['cases']:
    folder = ROOT/'cases'/c['id']; folder.mkdir(parents=True, exist_ok=True)
    (folder/'case.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    guide = website/'guides'/f"{c['id']}.md"
    if guide.exists(): shutil.copy2(guide,folder/'GUIDE.md')
    flow = 'flowchart LR\n'+'\n'.join(f'  n{i}["{s.replace(chr(34),chr(39))}"]' for i,s in enumerate(c['flow']))+'\n  '+' --> '.join(f'n{i}' for i in range(len(c['flow'])))+'\n'
    (folder/'flow.mmd').write_text(flow)
    demo = c['demo'].replace('https://isabella-ai-workbench.xieyongshi.chatgpt.site/','')
    target = html.escape('../../website/'+demo, quote=True)
    (folder/'demo.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><title>{html.escape(c["name"])}</title><a href="{target}">打开演示</a></html>')
    sections=[('为什么做',c['why']),('解决什么问题',c['problem']),('原来怎么工作',c['before']),('现在我做什么',c['human']),('现在 AI 做什么',c['ai']),('实际做到了什么',c['effect']),('怎样复用',c['reuse']),('贡献与来源',c['contribution'])]
    readme=f'# {c["name"]}\n\n[复用说明](GUIDE.md) · [演示入口](demo.html) · [结构化资料](case.json) · [流程图](flow.mmd)\n\n'
    readme+='\n\n'.join(f'## {title}\n\n{body}' for title,body in sections)+'\n\n'
    readme+=('代码：[source/](source/)，来源及导入提交见 [SOURCE.md](SOURCE.md)。' if c['id'] in source_ids else '本目录发布说明、脱敏材料及[共享浏览器演示代码](../../website/demo/)，不包含公司生产后端。')+'\n'
    (folder/'README.md').write_text(readme)
    manifest['cases'].append({'id':c['id'],'name':c['name'],'path':f'cases/{c["id"]}/','implementation':'public-platform-source' if c['id'] in source_ids else 'browser-demo-and-documentation'})
for s in data['skills']:
    folder=ROOT/'skills'/s['id']; (folder/'examples').mkdir(parents=True,exist_ok=True)
    (folder/'skill.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
    guide=website/'guides'/f"skill-{s['id']}.md"
    if guide.exists(): shutil.copy2(guide,folder/'GUIDE.md')
    (folder/'examples/input.txt').write_text(s['exampleInput']+'\n');(folder/'examples/review-output.txt').write_text(s['exampleOutput']+'\n')
    steps='\n'.join(f'{i+1}. {x}' for i,x in enumerate(s['how']))
    (folder/'README.md').write_text(f'# {s["name"]}\n\n原条目：`{s["sourceName"]}` · [关联案例](../../cases/{s["caseId"]}/) · [复用说明](GUIDE.md)\n\n## What\n\n{s["what"]}\n\n## Why\n\n{s["why"]}\n\n## How\n\n{steps}\n\n## 效果\n\n{s["effect"]}\n\n## 示例\n\n[虚构输入](examples/input.txt) · [输出检查顺序](examples/review-output.txt)\n\n## 发布范围\n\n本目录是公开使用说明，不是原内部 SKILL.md 或独立运行包。{s["boundary"]}\n')
    manifest['skills'].append({'id':s['id'],'name':s['name'],'path':f'skills/{s["id"]}/','packageType':'public-usage-guide'})
(ROOT/'cases/README.md').write_text('# 案例目录\n\n'+ '\n'.join(f'- [{x["name"]}]({x["id"]}/)' for x in data['cases'])+'\n')
(ROOT/'skills/README.md').write_text('# Skill 公开说明\n\n'+ '\n'.join(f'- [{x["name"]}]({x["id"]}/)' for x in data['skills'])+'\n')
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Updated {len(data["cases"])} cases and {len(data["skills"])} Skill guides. Existing CLI source snapshots were retained. Review git diff before publishing.')
