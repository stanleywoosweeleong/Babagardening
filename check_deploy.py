#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify every asset referenced by index.html, manifest and sw.js actually
resolves. Run against the local folder AND the live site before trusting a deploy.

  python3 check_deploy.py                       # local folder over http
  python3 check_deploy.py https://user.github.io/Repo/   # live site
"""
import json, re, sys, os, subprocess, time, urllib.request, urllib.error

D = '/mnt/user-data/outputs/babagardening'
base = sys.argv[1] if len(sys.argv) > 1 else None
served = None

if not base:
    served = subprocess.Popen([sys.executable, '-m', 'http.server', '8901'],
                              cwd=D, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    base = 'http://127.0.0.1:8901/'
if not base.endswith('/'):
    base += '/'

html = open(f'{D}/index.html', encoding='utf-8').read()
mani = json.load(open(f'{D}/manifest.webmanifest'))
sw = open(f'{D}/sw.js', encoding='utf-8').read()

refs = {}   # url -> where it came from

# <link href> / <script src> that aren't data URIs
for m in re.finditer(r'<link[^>]+href="([^"]+)"', html):
    u = m.group(1)
    if not u.startswith(('data:', 'http')):
        refs.setdefault(u, []).append('index.html <link>')

refs.setdefault('manifest.webmanifest', []).append('index.html <link rel=manifest>')

for i in mani['icons']:
    refs.setdefault(i['src'], []).append(f"manifest icon {i['sizes']} {i.get('purpose','any')}")
for s in mani.get('shortcuts', []):
    for i in s.get('icons', []):
        refs.setdefault(i['src'], []).append('manifest shortcut icon')

for m in re.finditer(r"'\./([^']+)'", sw):
    refs.setdefault(m.group(1), []).append('sw.js precache')

# README images (shown on the repo front page)
for m in re.finditer(r'<img src="([^"]+)"', open(f'{D}/README.md', encoding='utf-8').read()):
    refs.setdefault(m.group(1), []).append('README image')

print(f'Checking {len(refs)} referenced assets against {base}\n')
bad = []
for url in sorted(refs):
    full = base + url.lstrip('./')
    try:
        with urllib.request.urlopen(full, timeout=20) as r:
            code, ctype, size = r.status, r.headers.get('Content-Type', '?'), len(r.read())
    except urllib.error.HTTPError as e:
        code, ctype, size = e.code, '-', 0
    except Exception as e:
        code, ctype, size = 'ERR', str(e)[:30], 0
    ok = code == 200
    if not ok:
        bad.append((url, refs[url]))
    print(f"  {'ok ' if ok else 'MISSING'}  {str(code):4}  {url:28s} {str(size):>9} B  {ctype.split(';')[0]}")

print()
if bad:
    print('PROBLEMS — these are referenced but do not resolve:')
    for u, where in bad:
        print(f'  {u}\n      referenced by: {", ".join(where)}')
else:
    print('All referenced assets resolve. Safe to deploy.')

if served:
    served.terminate()
sys.exit(1 if bad else 0)
