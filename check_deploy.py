#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check that every file the app needs is actually reachable.

  python check_deploy.py                     # check the folder this script sits in
  python check_deploy.py https://user.github.io/Repo/    # check the live site

Reads the service worker's generated PRECACHE list plus the icons named in the
manifest and the <link> tags in index.html, then requests each one.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
base = sys.argv[1] if len(sys.argv) > 1 else None
if base and not base.endswith('/'):
    base += '/'


def read(name):
    """Fetch a file from the live site, or read it from this folder."""
    if base:
        with urllib.request.urlopen(base + name, timeout=30) as r:
            return r.read().decode('utf-8', 'replace')
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return f.read()


def check(name):
    """Return (status, bytes) for one asset."""
    if base:
        try:
            with urllib.request.urlopen(base + name.lstrip('./'), timeout=30) as r:
                return r.status, len(r.read())
        except urllib.error.HTTPError as e:
            return e.code, 0
        except Exception as e:
            return type(e).__name__, 0
    path = os.path.join(HERE, name.lstrip('./'))
    if os.path.isdir(path) or name in ('./', ''):
        path = os.path.join(HERE, 'index.html')
    return (200, os.path.getsize(path)) if os.path.exists(path) else (404, 0)


where = base or HERE
print('Checking ' + where + '\n')

try:
    sw = read('sw.js')
    html = read('index.html')
    mani = json.loads(read('manifest.webmanifest'))
except Exception as e:
    print('Could not read the core files (sw.js / index.html / manifest.webmanifest)')
    print('  ' + type(e).__name__ + ': ' + str(e))
    if not base:
        print('\nRun this from inside the folder that holds index.html, or pass the site URL:')
        print('  python check_deploy.py https://your-user.github.io/YourRepo/')
    sys.exit(2)

version = re.search(r"CACHE_VERSION = '([^']+)'", sw)
print('service worker version: ' + (version.group(1) if version else '?'))

refs = {}
m = re.search(r'const PRECACHE = (\[[\s\S]*?\]);', sw)
if m:
    for f in json.loads(m.group(1)):
        refs.setdefault(f, []).append('sw precache')
lz = re.search(r'const LAZY = (\[[\s\S]*?\]);', sw)
if lz:
    for f in json.loads(lz.group(1)):
        refs.setdefault(f, []).append('detail image (lazy)')
for icon in mani.get('icons', []):
    refs.setdefault('./' + icon['src'], []).append('manifest icon ' + icon.get('sizes', ''))
for href in re.findall(r'<link[^>]+href="([^"]+)"', html):
    if not href.startswith(('data:', 'http')):
        refs.setdefault('./' + href, []).append('index.html <link>')

print('checking %d files\n' % len(refs))
bad = []
for name in sorted(refs):
    status, size = check(name)
    ok = status == 200
    if not ok:
        bad.append(name)
    print('  %-7s %-5s %-26s %8s B' % ('ok' if ok else 'MISSING', status,
                                       name.lstrip('./') or '(root)', size))

print()
if bad:
    print('%d MISSING — upload these, then run this again:' % len(bad))
    for n in bad:
        print('  ' + n.lstrip('./') + '   (needed by: ' + ', '.join(refs[n]) + ')')
else:
    print('All %d files present. Safe to deploy.' % len(refs))
sys.exit(1 if bad else 0)
