#!/usr/bin/env python3
"""Check public package completeness and local links; never connects to recruiting systems."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from html.parser import HTMLParser
import json,re,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def require(path):
    if not path.exists(): errors.append('Missing: '+str(path.relative_to(ROOT)))
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src','poster') and v: self.urls.append(v)
manifest=json.loads((ROOT/'manifest.json').read_text());data=json.loads((ROOT/'website/portfolio-data.json').read_text())
for kind,filename in [('cases','case.json'),('skills','skill.json')]:
    expected={x['id'] for x in data[kind]};actual={x['id'] for x in manifest[kind]}
    if expected!=actual: errors.append(kind+' manifest differs from website catalog')
    folders={x.name for x in (ROOT/kind).iterdir() if x.is_dir()}
    if expected!=folders: errors.append(kind+' folder list differs from catalog')
    for item in data[kind]:
        folder=ROOT/kind/item['id']
        for name in ['README.md','GUIDE.md',filename]: require(folder/name)
        if json.loads((folder/filename).read_text())!=item: errors.append('Stale metadata: '+item['id'])
        if kind=='cases':
            for name in ['demo.html','flow.mmd']:require(folder/name)
        else:
            for name in ['input.txt','review-output.txt','prompt.txt']:require(folder/'examples'/name)
for p in ROOT.rglob('*'):
    if '.git' in p.parts or not p.is_file():continue
    if p.is_symlink():errors.append('Unexpected symlink: '+str(p.relative_to(ROOT)))
    if p.stat().st_size>95*1024*1024:errors.append('Oversized GitHub file: '+str(p.relative_to(ROOT)))
    if p.suffix.lower() not in {'.html','.md','.json','.js','.mjs','.py','.css','.txt','.svg','.yml','.yaml','.command','.patch'}:continue
    text=p.read_text(errors='replace')
    # A local developer path or a real-looking token must not enter the public export.
    if re.search(r'/(?:Users|home)/[A-Za-z][^\s"\']*/',text):errors.append('Personal absolute path: '+str(p.relative_to(ROOT)))
    if re.search(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{35,})',text):errors.append('Possible credential: '+str(p.relative_to(ROOT)))
    if p.suffix=='.html':
        parser=Links();parser.feed(text)
        for url in parser.urls:
            parsed=urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:continue
            target=(ROOT/'website'/unquote(parsed.path.lstrip('/'))) if parsed.path.startswith('/') else p.parent/unquote(parsed.path)
            if not target.exists():errors.append('Broken HTML link: '+str(p.relative_to(ROOT))+' -> '+url)
for x in manifest['sourceSnapshots']:
    for name in ['LICENSE','README.md','SKILL.md']:require(ROOT/'cases'/x['caseId']/'source'/name)
for p in (ROOT/'website').glob('*.js'):
    result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
    if result.returncode:errors.append('JavaScript syntax: '+str(p.relative_to(ROOT))+' '+result.stderr)
if errors:
    print('\n'.join(sorted(set(errors))));sys.exit(1)
print(f'PASS: {len(data["cases"])} case folders, {len(data["skills"])} Skill folders; metadata, local HTML links, source licenses, file sizes and credential patterns checked.')
