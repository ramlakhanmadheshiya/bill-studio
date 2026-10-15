#!/usr/bin/env python3
"""End-to-end smoke test: onboard an Indian business, visit every screen, screenshot each.
Run: python3 tools/smoke.py <base-url> <out-dir> [--mobile]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/bs-shots'
MOBILE = '--mobile' in sys.argv
COUNTRY = next((a.split('=')[1] for a in sys.argv if a.startswith('--country=')), 'IN')
os.makedirs(OUT, exist_ok=True)
w, h = (390, 844) if MOBILE else (1440, 960)
tag = ('m-' if MOBILE else '') + COUNTRY.lower() + '-'
fails = []

def step(name, fn):
    try:
        fn(); print('ok  ', name)
    except Exception as e:
        fails.append(f'{name}: {e}'); print('FAIL', name, '->', e)

with Browser(w, h, mobile=MOBILE) as b:
    S = lambda n, full=False: b.shot(os.path.join(OUT, tag + n + '.png'), full)
    b.go(BASE)
    step('welcome', lambda: (b.wait('document.querySelector(".welcome")'), S('01-welcome')))
    def onboard():
        b.click('[data-next]'); b.wait('document.querySelector("[data-c]")')
        b.click(f'[data-c="{COUNTRY}"]'); S('02-country')
        b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
        b.eval('''(()=>{const set=(n,v)=>{const e=document.querySelector(`[name=${n}]`); if(e){e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));}};
          set('name','Sharma Electronics'); set('address','14 MG Road, Andheri East'); set('city','Mumbai'); set('postal','400069'); set('phone','+91 98200 12345'); set('email','billing@sharma.example');
          set('taxId', document.querySelector('[name=region]') ? '27AAPFU0939F1ZV' : 'GB123456789'); })()''')
        S('03-details')
        b.click('[data-finish]')
        b.wait('document.querySelector(".stat")', 15)
        time.sleep(0.8); S('04-dashboard', True)
    step('onboard', onboard)
    def visit(route, wait_sel, name, full=True):
        b.eval(f'location.hash={json.dumps(route)}')
        b.wait(f'document.querySelector({json.dumps(wait_sel)})', 12)
        time.sleep(0.9); S(name, full)
    step('bills', lambda: visit('#/bills', '.table, .empty', '05-bills'))
    step('editor', lambda: visit('#/bills/new/invoice', '[data-paper] .bill-page', '06-editor'))
    def make_invoice():
        b.eval('''(()=>{const i=document.querySelector('[data-cust-input]'); i.value='Northwind'; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('focus'));})()''')
        time.sleep(0.3)
        b.eval('''(()=>{const s=document.querySelector('[data-cust-suggest] button'); if(s) s.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));})()''')
        time.sleep(0.3)
        b.eval('''(()=>{const n=document.querySelector('[data-name]'); n.value='Wireless'; n.dispatchEvent(new Event('input',{bubbles:true}));})()''')
        time.sleep(0.3)
        b.eval('''(()=>{const s=document.querySelector('.item-card .suggest button'); if(s) s.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));})()''')
        time.sleep(0.3)
        b.eval('''(()=>{const q=document.querySelector('[data-k="items.0.qty"]'); q.value='3'; q.dispatchEvent(new Event('input',{bubbles:true}));})()''')
        b.click('[data-add]')
        b.eval('''(()=>{const set=(k,v)=>{const e=document.querySelector(`[data-k="${k}"]`); e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));}; set('items.1.name','On-site installation'); set('items.1.rate','1500'); set('items.1.qty','2');})()''')
        time.sleep(0.8); S('07-editor-filled', True)
        b.click('[data-save]')
        b.wait('location.hash.match(/#\\/bills\\/[\\w-]+$/) && document.querySelector("[data-paper] .bill-page")', 12)
        time.sleep(1); S('08-docview', True)
    step('create invoice', make_invoice)
    step('templates', lambda: visit('#/templates', '.tpl-card .bill-page', '09-templates'))
    def designer():
        b.eval('document.querySelector("[data-edit=tpl-cupertino]").click()')
        b.wait('document.querySelector(".designer .blk-frame")', 12)
        time.sleep(0.6)
        b.eval('document.querySelector(".blk-frame.b-items").dispatchEvent(new PointerEvent("pointerdown",{bubbles:true,clientX:600,clientY:500}))');
        b.eval('window.dispatchEvent(new PointerEvent("pointerup",{bubbles:true}))')
        time.sleep(0.5); S('10-designer', False)
        b.click('[data-done]'); b.wait('location.hash==="#/templates"')
    step('designer', designer)
    step('customers', lambda: visit('#/customers', '.group, .empty', '11-customers'))
    def cust():
        b.eval('document.querySelector(".group a.row").click()'); b.wait('document.querySelector(".table")'); time.sleep(0.6); S('12-customer', True)
    step('customer', cust)
    step('items', lambda: visit('#/items', '.table, .empty', '13-items'))
    step('payments', lambda: visit('#/money', '.stat', '14-payments'))
    step('reports', lambda: visit('#/reports', '[data-r]', '15-reports'))
    def rep(key, name):
        b.eval(f'document.querySelector("[data-r={key}]").click()'); b.wait('document.querySelector("[data-pdf]")'); time.sleep(0.5)
        b.eval('(()=>{const s=document.querySelector("[data-period]"); if(s){s.value="all"; s.dispatchEvent(new Event("change"));}})()'); time.sleep(0.6)
        S(name, True); b.eval('document.querySelector("[data-back]").click()'); time.sleep(0.4)
    step('report tax', lambda: rep('gstr1' if COUNTRY == 'IN' else 'tax', '16-report-tax'))
    step('report pl', lambda: rep('pl', '17-report-pl'))
    step('business', lambda: visit('#/business', '[data-save]', '18-business'))
    step('settings', lambda: visit('#/settings', '[data-backup]', '19-settings'))
    def dark():
        b.eval('localStorage.setItem("bs-theme","dark"); document.documentElement.dataset.theme="dark"; location.hash="#/"')
        b.wait('document.querySelector(".stat")'); time.sleep(0.8); S('20-dark-dashboard')
        b.eval('location.hash="#/templates"'); b.wait('document.querySelector(".tpl-card .bill-page")'); time.sleep(0.8); S('21-dark-templates')
    step('dark', dark)
    def pdf():
        b.eval('location.hash="#/bills"'); b.wait('document.querySelector("[data-id]")'); b.eval('document.querySelector("[data-id]").click()')
        b.wait('document.querySelector("[data-paper] .bill-page")')
        size = b.eval('''(async()=>{const m=await import('./assets/js/export.js'); const r=await import('./assets/js/render.js'); const s=await import('./assets/js/store.js'); const db=(await import('./assets/js/db.js')).db; const t=await import('./assets/js/tplstore.js');
          const id=location.hash.split('/').pop(); const d=await db.get('documents',id); const ctx=r.buildContext(d,s.state.business); const tpl=await t.templateFor(d); const blob=await m.pdfBlob(ctx,tpl); return blob.size;})()''')
        assert size > 20000, f'pdf too small {size}'
        print('     pdf bytes', size)
    step('pdf', pdf)
    print('\n'.join(['LOGS:'] + b.logs) if b.logs else 'no console errors')
print('FAILS:' if fails else 'ALL PASSED', *fails, sep='\n')
