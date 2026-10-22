#!/usr/bin/env python3
"""Edge-case owner probes: India composition dealer, Saudi B2C simplified invoice, 'Other country' with its own
currency, German purchase with input VAT. Prints observations."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser
from owner_journey import H
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
OUT = '/private/tmp/claude-501/-Users-ramlakhan-Desktop-Projests/de10ec63-a650-4f6e-b43f-0d3dab730a18/scratchpad/journey'

def setup(b, code, fields):
    b.go(BASE); b.wait('document.querySelector("[data-next]")', 15)
    b.click('[data-next]'); b.click(f'[data-c="{code}"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")'); b.eval(H)
    for k, v in fields.items(): b.eval(f'T.set("[name={k}]", {json.dumps(v)})'); time.sleep(0.15)
    b.eval('(()=>{const s=T.q("[data-seed]"); if(s && s.checked) s.click();})()')
    b.click('[data-finish]'); time.sleep(2); b.eval(H)
    return b.eval('!!document.querySelector(".stat")')

def bill(b, typ, cust, items, extra=''):
    b.eval(f'location.hash="#/bills/new/{typ}"'); b.wait('document.querySelector("[data-paper] .bill-page")', 12); time.sleep(0.5); b.eval(H)
    if cust: b.eval(f'T.set("[data-cust-input]", {json.dumps(cust)})')
    for i, (n, r) in enumerate(items):
        if i: b.click('[data-add]'); time.sleep(0.2); b.eval(H)
        b.eval(f'T.set(\'[data-k="items.{i}.name"]\', {json.dumps(n)}); T.set(\'[data-k="items.{i}.rate"]\', "{r}")')
    if extra: b.eval(extra)
    time.sleep(0.3); b.click('[data-save]'); time.sleep(1.5)
    w = None
    if b.eval('!!document.querySelector(".modal [data-ok]")'): w = b.eval('T.text(".modal")'); b.click('.modal [data-ok]'); time.sleep(1.5)
    b.eval(H)
    if '/new/' in b.eval('location.hash'): return {'saved': False, 'toasts': b.eval('T.toasts()'), 'warn': w}
    b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.6)
    return {'saved': True, 'warn': w, 'paper': b.eval('T.text("[data-paper] .bill-page")'), 'qr': b.eval('!!document.querySelector("[data-paper] svg rect, [data-paper] .qr svg, [data-paper] img[src^=data]")')}

print('== India composition dealer')
with Browser(1300, 950) as b:
    ok = setup(b, 'IN', {'taxScheme': 'composition', 'name': 'Gupta Kirana', 'region': '09', 'taxId': '09AAPFU0939F1Z' })
    gst = b.eval("(async()=>{const v=await import('./assets/js/lib/validators.js'); return '09AAPFU0939F1Z'+v.gstinChecksum('09AAPFU0939F1Z')})()")
    if not ok:
        b.eval(f'T.set("[name=taxId]", "{gst}")'); b.click('[data-finish]'); time.sleep(2); b.eval(H); ok = b.eval('!!document.querySelector(".stat")')
    print('setup ok', ok)
    r = bill(b, 'invoice', 'Ramesh', [('Rice 5kg', 450)])
    print({k: (v[:700] if isinstance(v, str) else v) for k, v in r.items()})
    b.shot(f'{OUT}/edge-in-composition.png')
    b.eval('location.hash="#/money"'); time.sleep(1); b.eval(H); b.eval('T.q("[data-exp]").click()'); time.sleep(0.5)
    print('expense form labels', b.eval('T.qa(".modal label").map(l=>l.textContent)'))
    b.eval('T.qa(".overlay").forEach(o=>o.remove())')
    print('logs', b.logs)

print('== Saudi B2C (walk-in, no VAT number)')
with Browser(1300, 950) as b:
    print('setup ok', setup(b, 'SA', {'name': 'Riyadh Mart', 'taxId': '300000000000003', 'address': 'King Fahd Rd'}))
    r = bill(b, 'invoice', 'Walk-in customer', [('Dates 1kg', 40)])
    print({k: (v[:700] if isinstance(v, str) else v) for k, v in r.items()})
    b.shot(f'{OUT}/edge-sa-b2c.png')
    print('logs', b.logs)

print('== Other country (Qatar shop, QAR)')
with Browser(1300, 950) as b:
    print('setup ok', setup(b, 'OTHER', {'name': 'Doha Store', 'currency': 'QAR', 'taxScheme': 'unregistered'}))
    print('biz', b.eval("(async()=>{const s=await import('./assets/js/store.js'); const x=s.state.business; return [x.currency,x.locale,x.taxScheme,x.taxes.map(t=>t.label)]})()"))
    r = bill(b, 'invoice', 'Ali', [('Shoes', 199.5)])
    print({k: (v[:700] if isinstance(v, str) else v) for k, v in r.items()})
    b.shot(f'{OUT}/edge-other-qar.png')
    print('logs', b.logs)

print('== Germany: purchase with input VAT → VAT report net payable')
with Browser(1300, 950) as b:
    print('setup ok', setup(b, 'DE', {'name': 'Berlin GmbH', 'taxId': 'DE123456789', 'address': 'Unter den Linden 1', 'city': 'Berlin'}))
    r = bill(b, 'invoice', 'Kunde AG', [('Beratung', 1000)], 'T.set(\'[data-k="customer.address"]\', "Hauptstr. 5, 10115 Berlin")')
    print('saved', r.get('saved'), r.get('toasts'))
    b.eval('location.hash="#/money"'); time.sleep(1); b.eval(H); b.eval('T.q("[data-exp]").click()'); time.sleep(0.5)
    b.eval('(()=>{const m=T.q(".modal"); T.set("[name=vendor]","Office Supplier",m); T.set("[name=amount]","119",m); T.set("[name=tax]","19",m); m.querySelector("[data-ok]").click();})()'); time.sleep(1)
    b.eval('location.hash="#/reports"'); time.sleep(1); b.eval(H); b.eval('(()=>{const x=T.q("[data-back]"); x&&x.click()})()'); time.sleep(0.3); b.eval('T.q("[data-r=tax]").click()'); time.sleep(1)
    print(b.eval('T.text("#view")')[:1500])
    b.shot(f'{OUT}/edge-de-vatreport.png', True)
    print('logs', b.logs)
