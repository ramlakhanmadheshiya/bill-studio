#!/usr/bin/env python3
"""Feature tests: owner sign-in, every paper size (print preview + real PDF), export/import between two devices."""
import sys, os, json, time, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
OUT = '/private/tmp/claude-501/-Users-ramlakhan-Desktop-Projests/de10ec63-a650-4f6e-b43f-0d3dab730a18/scratchpad/features'
os.makedirs(OUT, exist_ok=True)
fails = []
def check(name, cond, info=''):
    print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''), flush=True)
    if not cond: fails.append(name)

def onboard(b, country='IN'):
    b.wait('document.querySelector("[data-next]")', 15)
    b.click('[data-next]'); b.click(f'[data-c="{country}"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
    b.eval('''(()=>{const s=(n,v)=>{const e=document.querySelector(`[name=${n}]`); if(!e) return; e.value=v; e.dispatchEvent(new Event("input",{bubbles:true})); e.dispatchEvent(new Event("change",{bubbles:true}));};
      s("name", %s); s("region","27"); s("taxId", %s); s("salesTaxRate","8");})()''' % (json.dumps('Sharma Electronics' if country == 'IN' else 'Austin Store'), json.dumps('27AAPFU0939F1ZV' if country == 'IN' else '')))
    b.click('[data-finish]'); b.wait('document.querySelector(".stat")', 20)

profile = tempfile.mkdtemp(prefix='bs-dev1-')
with Browser(1300, 950, profile=profile) as b:
    # ---- Sign-in
    b.go(BASE, login=False)
    b.wait('document.querySelector("[data-login]")', 10)
    check('sign-in screen shown first', b.eval('!!document.querySelector("[data-login]")'))
    check('first-run hint shows defaults', '12345' in b.eval('document.body.innerText'))
    b.eval('(()=>{const f=document.querySelector("[data-login]"); f.username.value="12345"; f.password.value="wrong"; f.requestSubmit();})()'); time.sleep(1.2)
    check('wrong password rejected', b.eval('document.querySelector("[data-err]").textContent').startswith('User ID or password'))
    b.login(); onboard(b)
    check('dashboard warns about default password', 'default User ID and password' in b.eval('document.body.innerText'))
    b.click('[data-lock]'); time.sleep(1.5)
    check('lock returns to sign-in', b.eval('!!document.querySelector("[data-login]")'))
    check('no defaults hint after setup', '67890' not in b.eval('document.body.innerText'))
    b.login()
    b.eval('location.hash="#/settings"'); b.wait('document.querySelector("[data-cred]")'); b.click('[data-cred]'); time.sleep(0.4)
    b.eval('''(()=>{const m=document.querySelector(".modal"); const s=(n,v)=>m.querySelector(`[name=${n}]`).value=v; s("ownerName","Ravi"); s("userId","ravi"); s("current","67890"); s("pw1","S3cret!"); s("pw2","S3cret!"); m.querySelector("[data-ok]").click();})()'''); time.sleep(2)
    b.eval('document.querySelector("[data-lock-now]").click()'); time.sleep(1.5)
    b.login('12345', '67890'); time.sleep(0.5)
    check('old credentials no longer work', b.eval('!!document.querySelector("[data-login]")'))
    b.eval('document.querySelector("[data-err]").textContent=""')
    check('new credentials work', b.login('ravi', 'S3cret!') and b.eval('!document.querySelector("[data-login]")'))
    stored = b.eval('''(async()=>{const {db}=await import('./assets/js/db.js'); return JSON.stringify(await db.setting('auth'))})()''')
    check('password never stored in plain text', 'S3cret' not in stored)

    # ---- Bill + every paper size
    b.eval('location.hash="#/bills/new/invoice"'); b.wait('document.querySelector("[data-cust-input]")'); time.sleep(0.4)
    b.eval('''(()=>{const set=(s,v)=>{const e=document.querySelector(s); e.value=v; e.dispatchEvent(new Event("input",{bubbles:true}));};
      set("[data-cust-input]","Acme Buyer"); set('[data-k="customer.address"]',"1 Main Road");
      set('[data-k="items.0.name"]',"Wireless keyboard"); set('[data-k="items.0.rate"]',"1499"); set('[data-k="items.0.qty"]',"3");})()''')
    for i in range(1, 14):
        b.click('[data-add]'); time.sleep(0.15)
        b.eval(f'''(()=>{{const set=(s,v)=>{{const e=document.querySelector(s); e.value=v; e.dispatchEvent(new Event("input",{{bubbles:true}}));}}; set('[data-k="items.{i}.name"]',"Line item {i}"); set('[data-k="items.{i}.rate"]',"{100 + i}");}})()''')
    b.click('[data-save]'); time.sleep(1.5)
    if b.eval('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.5)
    b.wait('document.querySelector("[data-paper] .bill-page") && !location.hash.includes("new")', 12)
    papers = b.eval('''(async()=>{const p=await import('./assets/js/print.js'); return p.PAPERS.filter(x=>x.id!=='custom').map(x=>[x.id, x.sheet||0, x.roll||false])})()''')
    for pid, sheet, roll in papers:
        for multi in ([False, True] if sheet else [False]):
            for tpl in (['tpl-classic', 'tpl-receipt'] if pid in ('a4', 'a6', 'a7', 't80') else (['tpl-receipt'] if roll else ['tpl-cupertino'])):
                b.click('[data-act=print]'); b.wait('document.querySelector(".print-dlg")'); time.sleep(0.2)
                b.eval(f'''(()=>{{const m=document.querySelector(".modal"); const s=(k,v)=>{{const e=m.querySelector(`[data-o=${{k}}]`); if(e.type==="checkbox") e.checked=v; else e.value=v; e.dispatchEvent(new Event("change",{{bubbles:true}}));}};
                    s("tplId","{tpl}"); s("paper","{pid}"); {'s("multiUp", true);' if multi else ''}}})()'''); time.sleep(1.2)
                info = b.eval('document.querySelector("[data-prev] .small")?.textContent || ""')
                ok = 'page' in info
                # Real PDF of the same sheets
                size = b.eval('''(async()=>{const p=await import('./assets/js/print.js'); const r=await import('./assets/js/render.js'); const s=await import('./assets/js/store.js'); const {db}=await import('./assets/js/db.js'); const t=await import('./assets/js/tplstore.js');
                    const id=location.hash.split('/').pop(); const d=await db.get('documents',id); const tpl=await t.getTemplate('%s');
                    const mount=document.createElement('div'); mount.style.cssText='position:fixed;left:-20000px'; document.body.append(mount);
                    const sheets=p.buildSheets((l)=>r.buildContext(l?{...d,copyLabel:l}:d, s.state.business), tpl, {paper:'%s', multiUp:%s, copies:%d, labels:[]}, mount); mount.remove();
                    const blob=await p.pdfFromSheets(sheets,{title:'t'}); return [blob.size, sheets.length, sheets[0].wMm, sheets[0].hMm, sheets[0].slots.length];})()''' % (tpl, pid, 'true' if multi else 'false', sheet if multi else 1))
                check(f'paper {pid}{" x"+str(sheet)+" per sheet" if multi else ""} [{tpl}]', ok and size[0] > 5000, f'{info} | pdf {size[0]//1024} KB, {size[1]} sheet(s) {round(size[2])}x{round(size[3])}mm, {size[4]} per sheet')
                if pid in ('a5l', 'a7', 't80', 'a4', 'a6', 'letter') :
                    b.shot(f'{OUT}/print-{pid}{"-multi" if multi else ""}-{tpl}.png')
                b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')

    # ---- Export (date range + full) from device 1
    blob_range = b.eval('''(async()=>{const k=await import('./assets/js/backup.js'); const {todayISO,addDays}=await import('./assets/js/lib/dates.js'); const bl=await k.exportData({businessId:null, from:addDays(todayISO(),-7), to:todayISO()}); return await bl.text()})()''')
    blob_full = b.eval('''(async()=>{const k=await import('./assets/js/backup.js'); const bl=await k.exportData({passphrase:'pw'}); return await bl.text()})()''')
    counts1 = b.eval('''(async()=>{const {db}=await import('./assets/js/db.js'); const d=await db.exportAll(); return Object.fromEntries(Object.entries(d.stores).map(([k,v])=>[k,v.length]))})()''')
    print('device 1 counts:', counts1)

# ---- Device 2: fresh profile, import
with Browser(1300, 950) as b2:
    b2.go(BASE); onboard(b2, 'US')
    r = b2.eval('''(async()=>{const k=await import('./assets/js/backup.js'); const data=JSON.parse(%s); return await k.importData(data,'merge')})()''' % json.dumps(blob_range))
    check('range import merges into another device', r['added'] > 0, str(r))
    biz = b2.eval('''(async()=>{const {db}=await import('./assets/js/db.js'); return (await db.all('businesses')).map(x=>x.name)})()''')
    check('both businesses present after merge', 'Sharma Electronics' in biz and len(biz) == 2, str(biz))
    r2 = b2.eval('''(async()=>{const k=await import('./assets/js/backup.js'); const data=JSON.parse(%s); return await k.importData(data,'merge')})()''' % json.dumps(blob_range))
    check('re-importing the same file adds nothing', r2['added'] == 0 and r2['updated'] == 0, str(r2))
    full = b2.eval('''(async()=>{const k=await import('./assets/js/backup.js'); const data=await k.readBackup(%s,'pw'); const r=await k.importData(data,'replace'); const {db}=await import('./assets/js/db.js'); const d=await db.exportAll(); return Object.fromEntries(Object.entries(d.stores).map(([k,v])=>[k,v.length]))})()''' % json.dumps(blob_full))
    check('full encrypted backup replaces device exactly', full == counts1, f'{full} vs {counts1}')
    b2.eval('sessionStorage.clear(); location.reload()'); time.sleep(1.5)
    check('after replace, sign-in comes from the backup', b2.login('ravi', 'S3cret!'))
    print('LOGS', [l for l in b2.logs if 'favicon' not in l])

print('\nFAILS:' if fails else '\nALL FEATURE CHECKS PASSED', *fails, sep='\n')
