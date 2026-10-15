#!/usr/bin/env python3
"""Regenerate sw.js with the full precache list and a content hash as the cache version."""
import hashlib, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = ['./', 'index.html', 'manifest.webmanifest']
for base in ['assets']:
    for d, _, fs in os.walk(os.path.join(ROOT, base)):
        for f in sorted(fs):
            if f.startswith('.'):
                continue
            files.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
h = hashlib.sha256()
for f in files:
    p = os.path.join(ROOT, 'index.html' if f == './' else f)
    h.update(f.encode()); h.update(open(p, 'rb').read())
version = h.hexdigest()[:12]
tpl = open(os.path.join(ROOT, 'tools', 'sw.template.js')).read()
out = tpl.replace('__VERSION__', version).replace('__FILES__', json.dumps(sorted(set(files)), indent=2))
open(os.path.join(ROOT, 'sw.js'), 'w').write(out)
print(f'sw.js: {len(files)} files, version {version}')
