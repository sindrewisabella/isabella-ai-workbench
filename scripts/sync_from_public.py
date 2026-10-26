#!/usr/bin/env python3
"""Export a reviewed static portfolio using an explicit public-file allowlist."""
import argparse, html, json, shutil, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LIVE_URL = 'https://sindrewisabella.github.io/isabella-ai-workbench/'
PAGES = 'index.html home-preview.html library.html skill.html case-note.html workbench-interactive.html cli-case.html salary-case.html evaluation-case.html evaluation-evidence.html dashboard-case.html'.split()
CODE = 'dashboard-case.js dashboard-case.css portfolio-preview.js portfolio-preview.css case-shell.js case-reading.css case-demos.js case-demos.css salary-import.css evaluation-runs.js evaluation-runs.css workbench-interactive.js workbench-interactive.css'.split()
DATA = 'portfolio-data.json evaluation-run-data.json october-public-stats.json'.split()
ASSETS = 'portfolio-fullstack.png mark.svg female-creator.png workbench-overview.png portfolio-evaluation.png portfolio-salary-import-v2.png workbench-collection.png zone-distribution.png zone-collection.png zone-review.png zone-rescue.png zone-done.png boss-greeting-20261020.mp4 boss-greeting-20261020-poster.png boss-ai-live-showcase-1.25x.mp4 boss-ai-live-showcase-poster.png boss-request-20261020.mp4 boss-request-20261020-poster.png boss-accept-20261021.mp4 boss-accept-20261021-poster.png boss-request-explained-1.25x.mp4 boss-request-explained-poster.png boss-accept-explained-1.25x.mp4 boss-accept-explained-poster.png boss-share-web.m4a payroll-demo-07.svg payroll-demo-08.svg salary-material-demo.mp4'.split()
CASE_PAGES = {'workbench':'workbench-interactive.html','cli':'cli-case.html','salary':'salary-case.html','evaluation':'evaluation-case.html','dashboard':'dashboard-case.html'}
def write(p,text):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
def structured(p,value):write(p,json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path,help='Reviewed static folder containing portfolio-data.json')
    source=parser.parse_args().source.resolve();required=PAGES+CODE+DATA+['assets/'+x for x in ASSETS]
    missing=[x for x in required if not (source/x).is_file()]
    if missing or not (source/'workbench-demo/index.html').is_file():parser.error('Missing reviewed static files: '+', '.join(missing))
    data=json.loads((source/'portfolio-data.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text());source_ids={x['caseId'] for x in manifest['sourceSnapshots']}
    for kind in ['cases','skills']:
        if {x['id'] for x in data[kind]}!={x['id'] for x in manifest[kind]}:parser.error(kind+' IDs changed; review additions/removals first.')
    with tempfile.TemporaryDirectory(prefix='portfolio-public-') as temp:
        export=Path(temp)/'website'
        for name in required:
            target=export/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
        shutil.copytree(source/'workbench-demo',export/'workbench-demo',ignore=shutil.ignore_patterns('*.map','.DS_Store'))
        for name in ['index.html','fullstack-data.js','NOTICE.md']:
            target=export/'fullstack-dashboard'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/'fullstack-dashboard'/name,target)
        js=export/'portfolio-preview.js';js.write_text(js.read_text().replace('<span class="preview-mark">整站预览</span>',''))
        write(export/'.nojekyll','');shutil.rmtree(ROOT/'website');shutil.copytree(export,ROOT/'website')
    manifest.update(snapshotDate='2026-10-26',publicUrl=LIVE_URL,website='website/',catalog='website/portfolio-data.json',caseCount=len(data['cases']),skillCount=len(data['skills']));manifest['cases']=[];manifest['skills']=[]
    for c in data['cases']:
        folder=ROOT/'cases'/c['id'];structured(folder/'case.json',c)
        sections=[('为什么做',c['why']),('解决什么问题',c['problem']),('原来怎么工作',c['before']),('现在我做什么',c['human']),('现在 AI 做什么',c['ai']),('实际完成范围',c['effect']),('怎样复用',c['reuse']),('贡献与来源',c['contribution'])]
        body='\n\n'.join('## '+title+'\n\n'+text for title,text in sections)
        links='[展示入口](demo.html) · [输入与输出](GUIDE.md) · [结构化资料](case.json) · [流程图](flow.mmd)'
        note='既有公开代码与许可证见 [source/](source/) 及 [SOURCE.md](SOURCE.md)。' if c['id'] in source_ids else '本目录为公开展示与说明，不含公司生产后端。'
        write(folder/'README.md','# '+c['name']+'\n\n'+links+'\n\n'+body+'\n\n'+note+'\n')
        write(folder/'GUIDE.md','# '+c['name']+'：具体怎样使用\n\n## 示例输入\n\n'+c['input']+'\n\n## 处理方式\n\n'+c['process']+'\n\n## 示例输出\n\n'+c['output']+'\n\n## 实际完成范围\n\n'+c['effect']+'\n\n## 换一个任务\n\n'+c['reuse']+'\n')
        flow='flowchart LR\n'+'\n'.join('  n%d["%s"]'%(i,s.replace('"',"'")) for i,s in enumerate(c['flow']))+'\n  '+' --> '.join('n%d'%i for i in range(len(c['flow'])))+'\n';write(folder/'flow.mmd',flow)
        target=html.escape('../../website/'+CASE_PAGES.get(c['id'],'case-note.html?id='+c['id']),quote=True)
        write(folder/'demo.html','<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='+target+'"><title>'+html.escape(c['name'])+'</title><a href="'+target+'">打开作品展示</a></html>')
        manifest['cases'].append({'id':c['id'],'name':c['name'],'path':'cases/'+c['id']+'/','implementation':'public-platform-source' if c['id'] in source_ids else 'browser-demo-and-documentation'})
    for s in data['skills']:
        folder=ROOT/'skills'/s['id'];structured(folder/'skill.json',s);write(folder/'examples/input.txt',s['input']+'\n');write(folder/'examples/review-output.txt',s['output']+'\n')
        write(folder/'examples/prompt.txt','请帮助我完成以下任务：'+s['what']+'\n\n处理规则：'+s['process']+'\n\n输入材料：\n'+s['input']+'\n\n输出要求：'+s['outputRequest']+'\n缺失事实保留为待确认，不补写。\n')
        how='\n'.join(str(i+1)+'. '+step for i,step in enumerate(s['how']))
        guide='# '+s['name']+'\n\n## What\n\n'+s['what']+'\n\n## Why\n\n'+s['why']+'\n\n## How\n\n'+how+'\n\n## 实际效果与范围\n\n'+s['effect']+'\n\n## 示例\n\n[输入](examples/input.txt) · [输出](examples/review-output.txt) · [可复制提示词](examples/prompt.txt)\n\n示例材料为虚构，网页不调用模型、不执行真实业务。\n\n## 来源与复用\n\n'+s['provenance']+'\n'
        write(folder/'README.md',guide);write(folder/'GUIDE.md','# 使用示例：'+s['name']+'\n\n## 输入\n\n'+s['input']+'\n\n## 处理\n\n'+s['process']+'\n\n## 输出\n\n'+s['output']+'\n\n替换材料并确认操作范围，实际运行需要对应系统与权限。\n')
        manifest['skills'].append({'id':s['id'],'name':s['name'],'path':'skills/'+s['id']+'/','packageType':'public-usage-guide'})
    for kind,title in [('cases','案例目录'),('skills','Skill 公开说明')]:write(ROOT/kind/'README.md','# '+title+'\n\n'+'\n'.join('- ['+x['name']+']('+x['id']+'/)' for x in data[kind])+'\n')
    structured(ROOT/'manifest.json',manifest);print('Exported %d cases, %d Skill guides and allowlisted static assets.'%(len(data['cases']),len(data['skills'])))
if __name__=='__main__':main()
