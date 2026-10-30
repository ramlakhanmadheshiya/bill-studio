#!/usr/bin/env python3
"""Build dist/Bill-Studio-offline.html — the whole app in ONE file that runs by double-clicking it
(file://, no server, no internet) — and dist/bill-studio-offline.zip with the self-hostable folder.

How: every ES module is embedded as a data: URL and wired together with an inline import map, so the
browser keeps real module semantics (live bindings, lazy views) without any network or server."""
import base64, json, os, re, zipfile, hashlib, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
os.makedirs(DIST, exist_ok=True)
JS = os.path.join(ROOT, 'assets', 'js')

def rel(p): return os.path.relpath(p, ROOT).replace(os.sep, '/')
def key(path): return 'bs/' + rel(path)

modules = {}
for d, _, fs in os.walk(JS):
    for f in fs:
        if f.endswith('.js'): modules[os.path.join(d, f)] = open(os.path.join(d, f), encoding='utf-8').read()

def rewrite(path, src):
    base = os.path.dirname(path)
    def fix(spec):
        if not spec.startswith('.'): return spec
        return key(os.path.normpath(os.path.join(base, spec)))
    # static: import ... from './x.js' | export ... from './x.js'
    src = re.sub(r"(\bfrom\s+)(['\"])(\.{1,2}/[^'\"]+)\2", lambda m: m.group(1) + m.group(2) + fix(m.group(3)) + m.group(2), src)
    # dynamic: import('./x.js') and import(`./views/${x}.js`)
    src = re.sub(r"(\bimport\(\s*)(['\"])(\.{1,2}/[^'\"]+)\2", lambda m: m.group(1) + m.group(2) + fix(m.group(3)) + m.group(2), src)
    src = re.sub(r"(\bimport\(\s*`)(\.{1,2}/[^`$]*)", lambda m: m.group(1) + fix(m.group(2)).rstrip('/') + ('/' if m.group(2).endswith('/') else ''), src)
    return src

imap = {}
for p, src in modules.items():
    code = rewrite(p, src)
    imap[key(p)] = 'data:text/javascript;base64,' + base64.b64encode(code.encode('utf-8')).decode()

css = open(os.path.join(ROOT, 'assets/css/app.css'), encoding='utf-8').read()
font = base64.b64encode(open(os.path.join(ROOT, 'assets/fonts/inter.woff2'), 'rb').read()).decode()
css = css.replace("url('../fonts/inter.woff2')", f"url(data:font/woff2;base64,{font})")
vendor = ''.join(f'<script>{open(os.path.join(ROOT, "assets/vendor", v), encoding="utf-8").read()}</script>\n'
                 for v in ['qrcode.js', 'html2canvas.min.js', 'jspdf.umd.min.js'])
icon = base64.b64encode(open(os.path.join(ROOT, 'assets/icons/icon-192.png'), 'rb').read()).decode()

index = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
theme = '<script>' + open(os.path.join(ROOT, 'assets/js/theme-init.js'), encoding='utf-8').read() + '</script>'
version = hashlib.sha256(''.join(imap.values()).encode()).hexdigest()[:10]
built = datetime.date.today().isoformat()

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Bill Studio (offline)</title>
<meta name="description" content="Bill Studio offline edition — runs entirely on this computer. Build {version}, {built}.">
<meta name="bill-studio-build" content="{version}">
<link rel="icon" href="data:image/png;base64,{icon}">
<style>{css}</style>
{theme}
<script type="importmap">{json.dumps({"imports": imap})}</script>
</head>
<body>
<div id="app"><div style="min-height:100vh;display:grid;place-items:center;color:#86868b;font:15px -apple-system,system-ui,sans-serif">Loading Bill Studio…</div></div>
<div id="print-root"></div>
<noscript><p style="padding:24px;font-family:system-ui">Bill Studio needs JavaScript enabled.</p></noscript>
{vendor}
<script type="module">import 'bs/assets/js/app.js';</script>
</body>
</html>
'''
out = os.path.join(DIST, 'Bill-Studio-offline.html')
open(out, 'w', encoding='utf-8').write(html)

# Self-hostable folder (for an intranet / any static web server) + the single file + instructions.
readme = f'''Bill Studio — offline & self-hosted package (build {version}, {built})

1) Easiest: double-click Bill-Studio-offline.html. It runs in your browser with no internet.
   Use Google Chrome or Microsoft Edge (recommended), Firefox or Safari.
   Your data is stored inside that browser on this computer. Keep backups (Settings > Full backup).

2) For a whole office: copy the "web" folder to any web server (IIS, Apache, nginx, NAS, intranet).
   Open it over https:// (or http://localhost). It also installs as an app and works offline.

First time: click Sign up. The first account becomes the Owner (choose your own User ID and password,
and keep the recovery key safe). Add your team in Team.

Moving data between computers: Settings > Full backup on the old one, then Settings > Import > Replace
on the new one. To send only some days, use Export a period, then Import > Merge.
'''
zpath = os.path.join(DIST, 'bill-studio-offline.zip')
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('README.txt', readme)
    z.write(out, 'Bill-Studio-offline.html')
    for f in ['index.html', 'sw.js', 'manifest.webmanifest']:
        z.write(os.path.join(ROOT, f), 'web/' + f)
    for d, _, fs in os.walk(os.path.join(ROOT, 'assets')):
        for f in fs:
            if not f.startswith('.'): z.write(os.path.join(d, f), 'web/' + rel(os.path.join(d, f)))
print(f'{out}: {os.path.getsize(out)//1024} KB, {len(imap)} modules, build {version}')
print(f'{zpath}: {os.path.getsize(zpath)//1024} KB')
