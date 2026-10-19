#!/usr/bin/env python3
"""Exploratory user-journey probes. Prints OBSERVATIONS (not just pass/fail) for audit.
Run: python3 tools/probe.py [base-url]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
OUT = '/private/tmp/claude-501/-Users-ramlakhan-Desktop-Projests/de10ec63-a650-4f6e-b43f-0d3dab730a18/scratchpad/probe'
os.makedirs(OUT, exist_ok=True)

JS_HELPERS = r'''
window.T = {
  q: (s) => document.querySelector(s),
  qa: (s) => [...document.querySelectorAll(s)],
  set(sel, v) { const e = document.querySelector(sel); if (!e) throw new Error('no ' + sel); if (e.type === 'checkbox') { e.checked = !!v; } else e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); },
  click(sel) { const e = document.querySelector(sel); if (!e) throw new Error('no ' + sel); e.click(); },
  toasts() { return [...document.querySelectorAll('.toast span')].map((x) => x.textContent); },
  async mods() { return { s: await import('./assets/js/store.js'), db: (await import('./assets/js/db.js')).db, e: await import('./assets/js/tax/engine.js') }; },
};
'''

def obs(tag, msg):
    print(f'[{tag}] {msg}', flush=True)

def boot(b):
    b.go(BASE)
    b.wait('document.querySelector(".welcome")', 15)
    b.eval(JS_HELPERS)

def onboard(b, country, fields, finish=True, seed=False):
    b.click('[data-next]'); b.wait('document.querySelector("[data-c]")')
    b.click(f'[data-c="{country}"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
    b.eval(JS_HELPERS)
    for k, v in fields.items():
        b.eval(f'T.set("[name={k}]", {json.dumps(v)})')
    if not seed:
        b.eval('(()=>{const s=T.q("[data-seed]"); if(s && s.checked) s.click();})()')
    if finish:
        b.eval('T.toasts && document.querySelectorAll(".toast").forEach(t=>t.remove())')
        b.click('[data-finish]'); time.sleep(1.2)
        b.eval(JS_HELPERS)
        return b.eval('({hash: location.hash, onDash: !!document.querySelector(".stat"), toasts: T.toasts()})')

def fresh():
    return Browser(1440, 960)

def scenario(name):
    print(f'\n=== {name} ===', flush=True)

# ---------------------------------------------------------------------------
scenario('India: onboarding field rules per GST status')
for scheme in ['regular', 'composition', 'unregistered']:
    with fresh() as b:
        boot(b)
        b.click('[data-next]'); b.click('[data-c="IN"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")'); b.eval(JS_HELPERS)
        b.eval(f'T.set("[name=taxScheme]", "{scheme}")'); time.sleep(0.3)
        vis = b.eval('(()=>{const t=T.q("[name=taxId]"); return t ? (t.offsetParent!==null) : false})()')
        obs(scheme, f'GSTIN field visible: {vis}')
        r = onboard(b, 'IN', {}, finish=False) if False else None
        b.eval('T.set("[name=name]","Test Shop"); T.set("[name=region]","27")')
        b.eval('(()=>{const s=T.q("[data-seed]"); if(s && s.checked) s.click();})()')
        b.click('[data-finish]'); time.sleep(1.2); b.eval(JS_HELPERS)
        dash = b.eval("!!document.querySelector('.stat')"); obs(scheme, f'finish without GSTIN -> dashboard={dash} toasts={b.eval("T.toasts()")}')
        if dash:
            b.eval('location.hash="#/bills/new/invoice"'); b.wait('document.querySelector("[data-paper] .bill-page")')
            obs(scheme, 'editor h1: ' + b.eval('T.q("[data-h1]").textContent'))
            obs(scheme, 'paper title: ' + b.eval('T.q(".b-title").textContent.trim()'))
            obs(scheme, 'tax selects present: ' + str(b.eval('T.qa("[data-k$=taxId]").length')))
            b.eval('location.hash="#/bills/new/receipt"'); b.wait('document.querySelector("[data-paper] .bill-page")'); time.sleep(0.3)
            obs(scheme, 'receipt paper title: ' + b.eval('T.q(".b-title").textContent.trim()'))
            b.shot(f'{OUT}/in-{scheme}-receipt.png')

# ---------------------------------------------------------------------------
scenario('Other countries: registered without tax ID / unregistered')
for cc in ['US', 'GB', 'DE', 'AU', 'AE', 'SA', 'JP', 'CA', 'OTHER']:
    with fresh() as b:
        boot(b)
        b.click('[data-next]'); b.click(f'[data-c="{cc}"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")'); b.eval(JS_HELPERS)
        opts = b.eval('T.qa("[name=taxScheme] option").map(o=>o.value+":"+o.textContent)')
        label = b.eval('(T.q("[name=taxId]")?.closest(".field")?.querySelector("label")?.textContent)||"-"')
        b.eval('T.set("[name=name]","Shop "+Math.random().toString(36).slice(2,6))')
        b.eval('(()=>{const s=T.q("[data-seed]"); if(s && s.checked) s.click();})()')
        b.click('[data-finish]'); time.sleep(1.2); b.eval(JS_HELPERS)
        ok = b.eval('!!document.querySelector(".stat")')
        obs(cc, f'schemes={opts} taxIdLabel={label} registered-without-id accepted={ok}')
        if ok:
            info = b.eval('''(async()=>{const {s}=await T.mods(); const b=s.state.business; return {cur:b.currency, fy:b.fyStartMonth, def:b.defaultTaxId, taxes:b.taxes.map(t=>t.label), title:s.docTitle('invoice',b), rtitle:s.docTitle('receipt',b)}})()''')
            obs(cc, json.dumps(info))

# ---------------------------------------------------------------------------
scenario('Editor validation (India regular, seeded)')
with fresh() as b:
    boot(b)
    print(onboard(b, 'IN', {'name': 'Sharma Electronics', 'region': '27', 'taxId': '27AAPFU0939F1ZV'}, seed=True))
    def newinv(t='invoice'):
        b.eval('location.hash="#/bills"'); b.wait('document.querySelector(".table, .empty")')
        b.eval(f'location.hash="#/bills/new/{t}"'); b.wait('document.querySelector("[data-paper] .bill-page")'); time.sleep(0.3); b.eval(JS_HELPERS)
    def save():
        b.eval('document.querySelectorAll(".toast").forEach(t=>t.remove())'); b.click('[data-save]'); time.sleep(0.9); b.eval(JS_HELPERS)
        return {'hash': b.eval('location.hash'), 'toasts': b.eval('T.toasts()')}
    newinv(); obs('empty', save())
    newinv(); b.eval('T.set("[data-cust-input]","Walk In")'); b.eval('T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","-50"); T.set("[data-k=\\"items.0.qty\\"]","-2")')
    obs('negative qty/rate', save())
    newinv(); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100"); T.set("[data-k=\\"items.0.disc\\"]","150")')
    obs('discount 150%', save())
    newinv(); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100"); T.set("[data-k=dueDate]","2020-01-01")')
    obs('due before date', save())
    newinv(); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100"); T.set("[data-k=number]","INV 26#27 0001")')
    obs('invalid chars in number', save())
    newinv(); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100"); T.set("[data-k=number]", T.qa("[data-k=number]")[0].value.replace(/\\d+$/, "0001"))')
    obs('duplicate number', save())
    newinv(); b.eval('T.set("[data-cust-input]","Acme B2B"); T.set("[data-k=\\"customer.taxId\\"]","29ABCDE1234F1Z9"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100")')
    obs('bad customer GSTIN help', b.eval('T.q("[data-cust-taxhelp]").textContent'))
    obs('bad customer GSTIN', save())
    newinv(); b.eval('T.set("[data-cust-input]","Acme"); T.set("[data-k=\\"customer.taxId\\"]","29AAPFU0939F1ZV"); T.set("[data-k=placeOfSupply]","27"); T.set("[data-k=\\"items.0.name\\"]","Thing"); T.set("[data-k=\\"items.0.rate\\"]","100")')
    obs('GSTIN state 29 vs POS 27 help', b.eval('T.q("[data-pos-help]").textContent'))
    newinv(); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","No HSN item"); T.set("[data-k=\\"items.0.rate\\"]","100")')
    obs('no HSN on tax invoice', save())
    newinv('credit'); b.eval('T.set("[data-cust-input]","Walk In"); T.set("[data-k=\\"items.0.name\\"]","Return"); T.set("[data-k=\\"items.0.rate\\"]","100")')
    obs('credit note without original invoice', save())
    newinv('receipt'); b.eval('T.set("[data-k=\\"items.0.name\\"]","Cash item"); T.set("[data-k=\\"items.0.rate\\"]","100")')
    r = save(); obs('receipt walk-in (paid now)', r)
    if '/bills/' in r['hash']:
        obs('receipt status', b.eval('T.q(".badge").textContent'))
    # email validation in editor
    newinv(); b.eval('T.set("[data-cust-input]","Bad Mail"); T.set("[data-k=\\"customer.email\\"]","not-an-email"); T.set("[data-k=\\"items.0.name\\"]","x"); T.set("[data-k=\\"items.0.rate\\"]","10")')
    obs('bad email', save())

    newinv(); b.eval('T.set("[data-cust-input]","Big Buyer"); T.set("[data-k=\\"items.0.name\\"]","Sofa"); T.set("[data-k=\\"items.0.rate\\"]","60000")')
    obs('B2C >= 50k without address', save())
    newinv(); b.eval('T.set("[data-cust-input]","Exporter Inc"); T.set("[data-k=supplyType]","export_lut"); T.set("[data-k=\\"items.0.name\\"]","Software"); T.set("[data-k=\\"items.0.rate\\"]","1000")')
    obs('export LUT: POS, total', b.eval('({pos:T.q("[data-k=placeOfSupply]").value, total:T.q(".totals-box .grand b").textContent})'))
    r = save(); obs('export LUT save', r)
    if '/bills/' in r['hash'] and 'new' not in r['hash']: obs('export endorsement printed', b.eval('T.q(".b-totals").textContent.includes("WITHOUT PAYMENT OF INTEGRATED TAX")'))
    newinv(); b.eval('T.set("[data-cust-input]","RC Buyer"); T.set("[data-flag=reverseCharge]", true); T.set("[data-k=\\"items.0.name\\"]","Legal fee"); T.set("[data-k=\\"items.0.rate\\"]","1000")')
    obs('reverse charge without customer GSTIN', save())
    newinv('receipt'); time.sleep(0.2)
    obs('regular GST receipt h1 / paper title', b.eval('[T.q("[data-h1]").textContent, T.q(".b-title").textContent.trim()]'))
    newinv('challan'); obs('challan copy label default', b.eval('T.q("[data-k=copyLabel]").value'))
    scenario('Payments, credit notes, cancel, convert (India)')
    st = b.eval('''(async()=>{const {s,db}=await T.mods(); const docs=await s.list('documents'); const pays=await s.list('payments'); const custs=await s.list('customers');
      return custs.map(c=>[c.name, s.customerLedger(c,docs,pays).balance]);})()''')
    obs('balances before', st)
    # overpay an invoice via dialog
    inv = b.eval('''(async()=>{const {s}=await T.mods(); const d=(await s.list('documents')).find(d=>d.type==='invoice'&&d.customer.name==='Northwind Traders'); return d.id})()''')
    b.eval(f'location.hash="#/bills/{inv}"'); b.wait('document.querySelector("[data-paper] .bill-page")'); b.eval(JS_HELPERS)
    b.eval('T.click("[data-act=pay]")'); time.sleep(0.4); b.eval('T.set(".modal [name=amount]","99999999")'); b.eval('T.click(".modal [data-ok]")'); time.sleep(0.6)
    obs('overpay -> confirm shown', b.eval('[...document.querySelectorAll(".modal h2")].map(h=>h.textContent)'))
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    # credit note via menu link
    b.eval(f'location.hash="#/bills/new/credit?ref={inv}"'); b.wait('document.querySelector("[data-paper] .bill-page")'); time.sleep(0.4); b.eval(JS_HELPERS)
    obs('credit prefilled', b.eval('({cust:T.q("[data-cust-input]").value, items:T.qa("[data-name]").length, ref:T.q("[data-refdoc]")?.value})'))
    r = save(); obs('credit save', r)
    obs('credit view', b.eval('({badge:T.q(".badge")?.textContent, paper: T.q(".b-meta")?.textContent.replace(/\\s+/g," ")})'))
    st = b.eval('''(async()=>{const {s}=await T.mods(); const docs=await s.list('documents'); const pays=await s.list('payments'); const custs=await s.list('customers');
      return custs.map(c=>[c.name, s.customerLedger(c,docs,pays).balance]);})()''')
    obs('balances after overpay+credit', st)
    # quotation convert
    q = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('documents')).find(d=>d.type==='quotation').id})()''')
    b.eval(f'location.hash="#/bills/{q}"'); b.wait('document.querySelector("[data-paper] .bill-page")'); b.eval(JS_HELPERS)
    b.eval('T.click("[data-act=convert]")'); b.wait('document.querySelector("[data-paper] .bill-page") && location.hash.includes("from=")'); time.sleep(0.4); b.eval(JS_HELPERS)
    r = save(); obs('convert save', r)
    b.eval(f'location.hash="#/bills/{q}"'); b.wait('document.querySelector("[data-paper] .bill-page")'); b.eval(JS_HELPERS)
    obs('quotation after convert', b.eval('({badge:T.q(".badge").textContent, btn:T.q("[data-act=convert]")?.textContent.trim()})'))
    # cancel an invoice, stock check
    stock0 = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('products')).map(p=>[p.name,p.stock])})()''')
    b.eval(f'location.hash="#/bills/{inv}"'); b.wait('document.querySelector("[data-more]")'); b.eval(JS_HELPERS)
    b.eval('T.click("[data-more]")'); time.sleep(0.3)
    b.eval('[...document.querySelectorAll(".menu button")].find(x=>x.textContent.includes("Cancel bill")).click()'); time.sleep(0.4)
    b.eval('T.click(".modal [data-ok]")'); time.sleep(1); b.eval(JS_HELPERS)
    stock1 = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('products')).map(p=>[p.name,p.stock])})()''')
    obs('cancel: stock before/after', [stock0, stock1])
    obs('cancel: badge / payments still', b.eval('({badge:T.q(".badge").textContent, pays:T.qa("[data-delpay]").length})'))
    # edit invoice (stock double counting?)
    d2 = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('documents')).find(d=>d.type==='invoice'&&d.status==='final'&&d.items.some(i=>i.productId)).id})()''')
    s0 = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('products')).map(p=>p.stock)})()''')
    b.eval(f'location.hash="#/bills/{d2}/edit"'); b.wait('document.querySelector("[data-paper] .bill-page")'); time.sleep(0.3); b.eval(JS_HELPERS)
    r = save(); s1 = b.eval('''(async()=>{const {s}=await T.mods(); return (await s.list('products')).map(p=>p.stock)})()''')
    obs('edit-save unchanged invoice: stock equal', s0 == s1)
    # settings change affects old invoices?
    tot0 = b.eval(f'''(async()=>{{const {{s,db}}=await T.mods(); const d=await db.get('documents','{d2}'); return s.docTotals(d).total}})()''')
    b.eval('''(async()=>{const {s}=await T.mods(); const b=JSON.parse(JSON.stringify(s.state.business)); b.taxes=b.taxes.map(t=>t.id==='gst18'?{...t,rate:40}:t); await s.saveBusiness(b);})()'''); time.sleep(1); b.eval(JS_HELPERS)
    tot1 = b.eval(f'''(async()=>{{const {{s,db}}=await T.mods(); const d=await db.get('documents','{d2}'); return s.docTotals(d).total}})()''')
    obs('changing tax rate in settings changes ALREADY-ISSUED invoice total', [tot0, tot1])
    b.eval('''(async()=>{const {s}=await T.mods(); const b=JSON.parse(JSON.stringify(s.state.business)); b.taxes=b.taxes.map(t=>t.id==='gst18'?{...t,rate:18}:t); await s.saveBusiness(b);})()'''); time.sleep(1)

    scenario('Customers / items / delete rules')
    b.eval(JS_HELPERS)
    cid = b.eval('''(async()=>{const {s,db}=await T.mods(); const c=await db.put('customers',{businessId:s.state.business.id,name:'Payer Only',openingBalance:0}); await db.put('payments',{businessId:s.state.business.id,customerId:c.id,amount:500,date:'2026-10-01',mode:'cash'}); return c.id})()''')
    b.eval(f'location.hash="#/customers/{cid}"'); b.wait('document.querySelector("[data-more]")'); b.eval(JS_HELPERS)
    b.eval('T.click("[data-more]")'); time.sleep(0.3); b.eval('[...document.querySelectorAll(".menu button")].find(x=>x.textContent.includes("Delete")).click()'); time.sleep(0.4)
    has_modal = b.eval('!!T.q(".modal")')
    if has_modal: b.eval('T.click(".modal [data-ok]")'); time.sleep(0.8)
    orphan = b.eval(f'''(async()=>{{const {{s}}=await T.mods(); return (await s.list('payments')).filter(p=>p.customerId==='{cid}').length}})()''')
    obs('delete customer that has only payments -> orphan payments left', orphan)
    # business switch isolation
    scenario('Multi-business isolation')
    b.eval('location.hash="#/welcome"'); b.wait('document.querySelector(".welcome [data-c]")'); b.eval(JS_HELPERS)
    b.click('[data-c="US"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")'); b.eval(JS_HELPERS)
    b.eval('T.set("[name=name]","US Store"); T.set("[name=salesTaxRate]","7.25")'); b.click('[data-finish]'); time.sleep(1.5); b.eval(JS_HELPERS)
    obs('2nd business active', b.eval('''(async()=>{const {s}=await T.mods(); return [s.state.business.name, (await s.list('documents')).length, (await s.list('customers')).length, s.state.businesses.length]})()'''))
    b.eval('location.hash="#/bills/new/invoice"'); b.wait('document.querySelector("[data-paper] .bill-page")'); b.eval(JS_HELPERS)
    obs('US new invoice number + tax options', b.eval('({n:T.q("[data-k=number]").value, tax:T.qa("[data-k=\\"items.0.taxId\\"] option").map(o=>o.textContent)})'))
    b.shot(f'{OUT}/us-editor.png')

    scenario('Backup / restore round trip')
    cnt = b.eval('''(async()=>{const {db}=await T.mods(); const d=await db.exportAll(); return Object.fromEntries(Object.entries(d.stores).map(([k,v])=>[k,v.length]))})()''')
    rt = b.eval('''(async()=>{const bk=await import('./assets/js/backup.js'); const {db}=await T.mods(); const blob=await bk.makeBackup('pw123'); const txt=await blob.text(); let bad; try{await bk.readBackup(txt,'wrong')}catch(e){bad=e.message}
       const data=await bk.readBackup(txt,'pw123'); await db.wipe(); await db.importAll(data); const d=await db.exportAll(); return {bad, after:Object.fromEntries(Object.entries(d.stores).map(([k,v])=>[k,v.length]))}})()''')
    obs('backup counts before', cnt); obs('restore', rt)
    print('\nLOGS:', b.logs)
