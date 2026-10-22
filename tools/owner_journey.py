#!/usr/bin/env python3
"""Business-owner journey, once per country: set up the shop, add a customer and a product, raise a
B2B invoice (2 lines at different rates + shipping), check every number against an independent
calculation, record a part payment, issue a partial credit note, convert a quotation, then check the
dashboard, customer balance, sales/tax reports and the print/PDF defaults. Writes JSON lines of findings.
Usage: python3 tools/owner_journey.py [base-url] [shard] [nshards] [out.jsonl]"""
import sys, os, json, time, re, math
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser
from country_sweep import SAMPLE_IDS

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
SHARD, NSHARDS = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
OUTF = sys.argv[4] if len(sys.argv) > 4 else '/dev/stdout'
SHOTS = '/private/tmp/claude-501/-Users-ramlakhan-Desktop-Projests/de10ec63-a650-4f6e-b43f-0d3dab730a18/scratchpad/journey'
os.makedirs(SHOTS, exist_ok=True)

H = r'''
window.T = {
  q: (s) => document.querySelector(s), qa: (s) => [...document.querySelectorAll(s)],
  set(sel, v, root = document) { const e = root.querySelector(sel); if (!e) return false; if (e.type === 'checkbox') e.checked = !!v; else e.value = v;
    e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); return true; },
  toasts: () => [...document.querySelectorAll('.toast span')].map((x) => x.textContent),
  text: (s) => document.querySelector(s)?.innerText || '',
};'''

def rnd(v, dp):
    f = 10 ** dp
    return math.floor(abs(v) * f + 0.5 + 1e-9) / f * (1 if v >= 0 else -1)

def journey(c, out):
    code = c['code']; F = []; O = {}
    def bad(sev, msg): F.append({'sev': sev, 'msg': msg})
    with Browser(1300, 950) as b:
      try:
        return _journey(b, c, out, code, F, O, bad)
      except Exception:
        try: LAST['screen'] = b.eval('location.hash + " | " + document.body.innerText.slice(0,300)') + ' | logs ' + str(b.logs[-3:])
        except Exception: pass
        raise

LAST = {}
def _journey(b, c, out, code, F, O, bad):
    if True:
        js = lambda s: b.eval(s)
        b.go(BASE); b.wait('document.querySelector("[data-next]")', 15)
        b.click('[data-next]'); b.wait('document.querySelector("[data-c]")'); b.click(f'[data-c="{code}"]'); time.sleep(0.2)
        b.click('[data-next]'); b.wait('document.querySelector("[name=name]")'); js(H)
        form_labels = js('T.qa(".field label").filter(l=>l.offsetParent).map(l=>l.textContent.trim())')
        O['onboarding_fields'] = form_labels
        vals = {'name': f'{c["name"]} Traders', 'address': '12 Market Street', 'city': 'Capital City', 'postal': '10001', 'phone': '+1 555 0100',
                'email': 'owner@example.com', 'taxId': SAMPLE_IDS.get(code, 'TAX-12345'), 'salesTaxRate': '8.25', 'secondaryId': '12/345/67890'}
        js('T.set("select[name=taxScheme]","regular")'); time.sleep(0.2)
        for k, v in vals.items(): js(f'T.set("[name={k}]", {json.dumps(v)})')
        if code == 'IN': js('T.set("[name=region]","27")')
        if code == 'CA': js('T.set("[name=region]","ON")'); time.sleep(0.2)
        js('(()=>{const s=T.q("[data-seed]"); if(s && s.checked) s.click();})()')
        b.click('[data-finish]'); time.sleep(2); js(H)
        if not js('!!document.querySelector(".stat")'):
            bad('blocker', 'Could not finish setup: ' + str(js('T.toasts()'))); return F, O
        biz = js('''(async()=>{const s=await import('./assets/js/store.js'); const m=await import('./assets/js/lib/money.js'); const b=s.state.business;
          return {taxes:b.taxes, def:b.defaultTaxId, cur:b.currency, locale:b.locale, dp:m.currencyDecimals(b.currency), fy:b.fyStartMonth, region:b.region}})()''')
        dp = biz['dp']; O['currency'] = biz['cur']; O['dp'] = dp
        rate_of = {t['id']: (t['rate'] if t.get('gst') else sum(x['rate'] for x in t.get('components', []))) for t in biz['taxes']}
        nonzero = [t for t in biz['taxes'] if rate_of[t['id']] > 0]
        std = biz['def']; R1 = rate_of.get(std, 0)
        O['default_tax'] = next((t['label'] for t in biz['taxes'] if t['id'] == std), None)
        if not nonzero and not c.get('noTax'): bad('high', 'No non-zero tax rate preset after registering')
        elif c.get('noTax'): pass
        elif R1 == 0: bad('high', f'Default tax for a registered business is 0% ({O["default_tax"]})')
        elif code not in ('US', 'MY', 'BR', 'IN', 'CA') and R1 != max(rate_of.values()): bad('medium', f'Default tax {R1}% is not the standard rate {max(rate_of.values())}%')
        if code == 'IN' and R1 != 18: bad('medium', f'India default GST is {R1}% (most goods/services are 18%)')
        red = next((t for t in nonzero if rate_of[t['id']] != R1), None)
        R2id = red['id'] if red else std; R2 = rate_of[R2id]

        # --- Customer (B2B, other region for India)
        cust_id = SAMPLE_IDS.get(code, '')
        if code == 'IN':
            cust_id = js('''(async()=>{const v=await import('./assets/js/lib/validators.js'); const s='29AAPFU0939F1Z'; return s+v.gstinChecksum(s)})()''')
        js('location.hash="#/customers"'); b.wait('document.querySelector("[data-new]")?.textContent.includes("New customer")'); js(H); b.click('[data-new]'); time.sleep(0.4)
        js(f'''(()=>{{const m=T.q(".modal"); T.set("[name=name]","Globex Buyer Ltd",m); T.set("[name=phone]","+1 555 0199",m); T.set("[name=email]","ap@globex.example",m);
             T.set("[name=address]","99 Commerce Ave",m); T.set("[name=taxId]",{json.dumps(cust_id)},m); m.querySelector("[data-ok]").click();}})()'''); time.sleep(0.8)
        if js('!!document.querySelector(".modal [data-ok]")'): bad('high', 'Customer form refused a valid customer: ' + str(js('T.toasts()'))); js('T.qa(".overlay").forEach(o=>o.remove())')

        # --- Product
        time.sleep(0.5); js('location.hash="#/items"'); b.wait('document.querySelector("[data-new]")?.textContent.includes("New item")'); js(H); b.click('[data-new]'); time.sleep(0.4)
        js(f'''(()=>{{const m=T.q(".modal"); T.set("[name=name]","Office Chair",m); T.set("[name=price]","1234.56",m); T.set("[name=cost]","800",m); T.set("[name=taxId]",{json.dumps(std)},m);
             T.set("[name=hsn]","9401",m); T.set("[name=trackStock]",true,m); T.set("[name=stock]","10",m); m.querySelector("[data-ok]").click();}})()'''); time.sleep(0.8)
        if js('!!document.querySelector(".modal [data-ok]")'): bad('high', 'Product form refused: ' + str(js('T.toasts()'))); js('T.qa(".overlay").forEach(o=>o.remove())')

        # --- Invoice via the editor
        js('location.hash="#/bills/new/invoice"'); b.wait('document.querySelector("[data-paper] .bill-page")', 12); time.sleep(0.5); js(H)
        js('(()=>{const i=T.q("[data-cust-input]"); i.focus(); i.value="Globex"; i.dispatchEvent(new Event("input",{bubbles:true}));})()'); time.sleep(0.3)
        picked = js('(()=>{const x=document.querySelector("[data-cust-suggest] [data-i]"); if(!x) return false; x.dispatchEvent(new MouseEvent("mousedown",{bubbles:true})); return true})()'); time.sleep(0.4)
        if not picked: bad('high', 'Saved customer not offered in the bill editor')
        js('(()=>{const i=T.q(\'[data-k="items.0.name"]\'); i.value="Office"; i.dispatchEvent(new Event("input",{bubbles:true}));})()'); time.sleep(0.3)
        pp = js('(()=>{const x=document.querySelector("[data-name=\'0\']").parentElement.querySelector("[data-j]"); if(!x) return false; x.dispatchEvent(new MouseEvent("mousedown",{bubbles:true})); return true})()'); time.sleep(0.4)
        if not pp: bad('high', 'Saved product not offered in the bill editor')
        js('T.set(\'[data-k="items.0.qty"]\',"3"); T.set(\'[data-k="items.0.disc"]\',"10")')
        b.click('[data-add]'); time.sleep(0.3); js(H)
        js(f'T.set(\'[data-k="items.1.name"]\',"Installation service"); T.set(\'[data-k="items.1.rate"]\',"99.99"); T.set(\'[data-k="items.1.qty"]\',"2"); T.set(\'[data-k="items.1.taxId"]\',{json.dumps(R2id)})')
        if code == 'IN': js('T.set(\'[data-k="items.1.hsn"]\',"998719")')
        js('(()=>{const x=T.q("[data-add-charge]"); x && x.click();})()'); time.sleep(0.3); js(H)
        js('T.set(\'[data-k="charges.0.amount"]\',"50")')
        pos = js('T.q("[data-k=placeOfSupply]")?.value || ""')
        if code == 'IN' and pos != '29': bad('high', f'Place of supply not taken from the customer GSTIN (got {pos}, expected 29)')
        time.sleep(0.4)
        b.click('[data-save]'); time.sleep(1.6)
        warn = None
        if js('!!document.querySelector(".modal [data-ok]")'):
            warn = js('T.text(".modal")'); b.click('.modal [data-ok]'); time.sleep(1.6)
        if '/new/' in js('location.hash'):
            bad('blocker', 'Invoice could not be saved: ' + str(js('T.toasts()'))); return F, O
        if warn: O['save_warning'] = warn[:300]
        b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.8); js(H)
        inv_id = js('location.hash.split("/").pop()')
        d = js('''(async()=>{const s=await import('./assets/js/store.js'); const {db}=await import('./assets/js/db.js'); const d=await db.get('documents',location.hash.split('/').pop());
          const t=s.docTotals(d); return {d, t:{taxable:t.taxable, tax:t.tax, total:t.total, roundOff:t.roundOff, taxSummary:t.taxSummary, lines:t.lines.map(l=>({taxable:l.taxable,tax:l.tax}))}, title:s.docTitle(d.type,s.bizFor(d),d)}})()''')
        doc, t = d['d'], d['t']
        O['invoice_number'] = doc['number']; O['title'] = d['title']
        # Independent calculation
        jp = c.get('taxRoundPerInvoice')
        l1 = rnd(3 * 1234.56 * 0.9, dp); l2 = rnd(2 * 99.99, dp); sh = rnd(50, dp)
        groups = {}
        for amt, r in ((l1, R1), (l2, R2), (sh, 0 if code == 'US' else R1)): groups.setdefault(r, []).append(amt)
        if jp:
            tax = sum(math.floor(sum(v) * r / 100 * 10 ** dp + 1e-9) / 10 ** dp for r, v in groups.items())
        elif code == 'IN':
            tax = sum(rnd(a * r / 100, dp) for r, v in groups.items() for a in v)  # inter-state: IGST
        else:
            tax = sum(rnd(a * r / 100, dp) for r, v in groups.items() for a in v)
        taxable = rnd(l1 + l2 + sh, dp); total = rnd(taxable + tax, dp)
        if doc.get('roundOff'): total = round(total)
        O['expected'] = {'taxable': taxable, 'tax': round(tax, dp), 'total': total}; O['app'] = {'taxable': t['taxable'], 'tax': t['tax'], 'total': t['total']}
        if abs(t['taxable'] - taxable) > 10 ** -dp / 2: bad('blocker', f'Taxable value wrong: app {t["taxable"]} vs expected {taxable}')
        if abs(t['tax'] - tax) > 10 ** -dp / 2 + 1e-9: bad('blocker', f'Tax wrong: app {t["tax"]} vs expected {round(tax, dp)}')
        if abs(t['total'] - total) > 10 ** -dp / 2 + 1e-9: bad('blocker', f'Total wrong: app {t["total"]} vs expected {total}')
        names = sorted({x['name'] for x in t['taxSummary']})
        O['tax_components'] = names
        if code == 'IN' and names != ['IGST']: bad('blocker', f'Inter-state Indian invoice should be IGST only, got {names}')
        if code == 'CA' and 'HST' not in names: bad('high', f'Ontario seller should charge HST, got {names}')
        # Printed bill
        paper = js('T.text("[data-paper] .bill-page")')
        fm = js(f'''(async()=>{{const m=await import('./assets/js/lib/money.js'); const w=await import('./assets/js/lib/words.js'); const s=await import('./assets/js/store.js'); const b=s.state.business; const c=(await import('./assets/js/tax/countries.js')).getCountry(b.country);
            return {{total:m.fmtMoney({t['total']},b.currency,b.locale), plain:m.fmtPlain({t['total']},b.currency,b.locale), words:w.amountInWords({t['total']},b.currency,c.numberSystem)}}}})()''')
        norm = lambda s: re.sub(r'[\s  ]', '', s)
        if norm(fm['total']) not in norm(paper) and norm(fm['plain']) not in norm(paper): bad('high', f'Grand total {fm["total"]} not visible on the printed bill')
        if 'words' not in O: O['words'] = fm['words']
        if fm['words'].lower()[:25] not in paper.lower(): bad('low', 'Amount in words not printed on the invoice')
        if d['title'].lower() not in paper.lower(): bad('high', f'Title "{d["title"]}" not on printed bill')
        if doc['number'] not in paper: bad('high', 'Invoice number not on printed bill')
        if vals['taxId'].upper().replace(' ', '') not in paper.upper().replace(' ', '') and code not in ('US', 'OTHER', 'BR') and not c.get('noTax'): bad('high', 'Seller tax ID not on printed bill')
        if cust_id and cust_id.upper() not in paper.upper().replace(' ', '') and c.get('eu'): bad('medium', 'Buyer VAT number not printed on B2B invoice')
        if 'Globex Buyer Ltd' not in paper: bad('high', 'Buyer name not on printed bill')
        if '99 Commerce Ave' not in paper: bad('medium', 'Buyer address not on printed bill')
        if code == 'IN' and 'Place of' not in paper: bad('high', 'Place of supply not printed (mandatory for inter-state)')
        if code == 'IN' and '9401' not in paper: bad('medium', 'HSN not printed')
        if R1 and not re.search(r'\d+(\.\d+)?\s?%', paper): bad('medium', 'No tax rate (%) shown on a tax invoice')
        if '12 Market Street' not in paper: bad('medium', 'Seller address missing on bill')
        if 'NaN' in paper or 'undefined' in paper or 'null' in paper: bad('blocker', 'NaN/undefined/null printed on the bill')
        if re.search(r'taken back', paper, re.I): bad('high', 'No-returns clause printed in default terms')
        if code in ('DE', 'AT') and not re.search(r'(Date of supply|Supply date)', paper): bad('medium', 'Supply date not printed (DE/AT)')
        b.shot(f'{out}/{code}-1-invoice.png')
        stock = js('''(async()=>{const {db}=await import('./assets/js/db.js'); return (await db.all('products')).map(p=>p.stock)})()''')
        if stock != [7]: bad('medium', f'Stock not reduced correctly after selling 3 (now {stock})')

        # --- Part payment
        part = rnd(t['total'] * 0.4, dp)
        b.click('[data-act=pay]'); time.sleep(0.5); js(H)
        modes = js('T.qa(".modal [name=mode] option").map(o=>o.textContent)')
        ph = js('T.q(".modal [name=reference]")?.placeholder || ""')
        O['pay_modes'] = modes
        if code != 'IN' and any(m.lower() == 'upi' for m in modes): bad('medium', 'Payment dialog offers "UPI" (India-only payment method)')
        if code != 'IN' and 'UTR' in ph: bad('low', f'Payment reference placeholder uses Indian term "UTR" ({ph})')
        js(f'T.set(".modal [name=amount]","{part}")'); b.click('.modal [data-ok]'); time.sleep(1.2); js(H)
        st = js('T.text(".badge")'); O['status_after_part'] = st
        if 'part' not in st.lower(): bad('high', f'After a part payment status is "{st}"')

        # --- Credit note: return 1 chair
        js(f'location.hash="#/bills/new/credit?ref={inv_id}"'); b.wait('document.querySelector("[data-paper] .bill-page")', 12); time.sleep(0.6); js(H)
        nitems = js('T.qa("[data-row]").length')
        if nitems < 2: bad('high', f'Credit note did not copy the invoice lines ({nitems})')
        js('T.set(\'[data-k="items.0.qty"]\',"1")')
        # remove service line and charge for a clean partial return
        js('(()=>{const r=T.qa("[data-remove]"); if(r[1]) r[1].click();})()'); time.sleep(0.3); js(H)
        js('(()=>{const r=T.q("[data-del-charge]"); r && r.click();})()'); time.sleep(0.3)
        b.click('[data-save]'); time.sleep(1.6)
        if js('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.6)
        if '/new/' in js('location.hash'): bad('high', 'Credit note could not be saved: ' + str(js('T.toasts()')))
        else:
            js(H); cpaper = js('T.text("[data-paper] .bill-page")'); b.shot(f'{out}/{code}-2-credit.png')
            if doc['number'] not in cpaper: bad('high', 'Credit note does not reference the original invoice number')
            ct = js('''(async()=>{const s=await import('./assets/js/store.js'); const {db}=await import('./assets/js/db.js'); const d=await db.get('documents',location.hash.split('/').pop()); const t=s.docTotals(d); return {total:t.total, tax:t.tax, title:s.docTitle(d.type,s.bizFor(d),d)}})()''')
            O['credit_title'] = ct['title']
            l1c = rnd(1234.56 * 0.9, dp)
            exp_ct = (math.floor(l1c * R1 / 100 * 10 ** dp + 1e-9) / 10 ** dp) if jp else rnd(l1c * R1 / 100, dp)
            exp_c = rnd(l1c + exp_ct, dp)
            if doc.get('roundOff'): exp_c = round(exp_c)
            if abs(ct['total'] - exp_c) > 10 ** -dp: bad('blocker', f'Credit note total wrong: app {ct["total"]} vs expected {exp_c}')
            due_exp = rnd(t['total'] - ct['total'] - part, dp)
            js(f'location.hash="#/bills/{inv_id}"'); b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.8); js(H)
            inv_txt = js('T.text("#view")')
            due_str = js(f'''(async()=>{{const m=await import('./assets/js/lib/money.js'); const s=await import('./assets/js/store.js'); return m.fmtMoney({due_exp}, s.state.business.currency, s.state.business.locale)}})()''')
            O['due_expected'] = due_str
            if norm(due_str) not in norm(inv_txt): bad('high', f'Invoice page does not show the right balance due {due_str} after payment + credit note')
            # Customer balance
            bal = js('''(async()=>{const s=await import('./assets/js/store.js'); const docs=await s.list('documents'); const pays=await s.list('payments'); const cs=await s.list('customers'); return s.customerLedger(cs[0],docs,pays).balance})()''')
            if abs(bal - due_exp) > 10 ** -dp: bad('high', f'Customer ledger balance {bal} ≠ invoice due {due_exp}')
            # Dashboard receivable
            js('location.hash="#/"'); b.wait('document.querySelector(".stat")'); time.sleep(0.8); js(H)
            if norm(due_str) not in norm(js('T.text("#view")')): bad('medium', f'Dashboard does not show receivable {due_str}')
            b.shot(f'{out}/{code}-3-dashboard.png')
            # Tax report = invoice tax − credit tax
            js('location.hash="#/reports"'); b.wait('document.querySelector("[data-r]")'); time.sleep(0.4); js(H)
            key = 'gstr1' if code == 'IN' else 'tax'
            js(f'T.q("[data-r={key}]").click()'); time.sleep(1.0); js(H)
            rep = js('T.text("#view")')
            net_tax = rnd(t['tax'] - ct['tax'], dp)
            nt = js(f'''(async()=>{{const m=await import('./assets/js/lib/money.js'); const s=await import('./assets/js/store.js'); const b=s.state.business; return [m.fmtMoney({net_tax},b.currency,b.locale), m.fmtNumber({net_tax},'en-US',{dp}), m.fmtPlain({net_tax},b.currency,b.locale)]}})()''')
            if not any(norm(x) in norm(rep) for x in nt): bad('high', f'{key} report does not show net output tax {nt[0]} (invoice tax − credit note tax)')
            if 'NaN' in rep or 'undefined' in rep: bad('blocker', 'NaN/undefined in tax report')
            b.shot(f'{out}/{code}-4-taxreport.png', True)
            # Sales register precision (3-decimal currencies)
            js('location.hash="#/reports"'); time.sleep(0.8); js('(()=>{const x=document.querySelector("[data-back]"); x && x.click();})()'); b.wait('document.querySelector("[data-r]")'); time.sleep(0.3); js(H)
            js('T.q("[data-r=register]").click()'); time.sleep(1.0); js(H)
            reg = js('T.text("#view")')
            if dp == 3 and not re.search(r'\d\.\d{3}\b', reg): bad('high', f'Sales register shows {biz["cur"]} amounts with 2 decimals (currency has 3)')
            if dp == 0 and re.search(r'\d\.\d{2}\b', reg.split('Total')[-1]): bad('low', f'Sales register shows decimals for {biz["cur"]} (no minor unit)')

        # --- Quotation -> invoice
        js('location.hash="#/bills/new/quotation"'); b.wait('document.querySelector("[data-paper] .bill-page")', 12); time.sleep(0.5); js(H)
        js('T.set("[data-cust-input]","Walk-in Prospect"); T.set(\'[data-k="customer.address"]\',"7 Side Street"); T.set(\'[data-k="items.0.name"]\',"Desk"); T.set(\'[data-k="items.0.rate"]\',"500")')
        b.click('[data-save]'); time.sleep(1.5)
        if js('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.5)
        if '/new/' in js('location.hash'): bad('high', 'Quotation could not be saved: ' + str(js('T.toasts()')))
        else:
            js(H); qp = js('T.text("[data-paper] .bill-page")')
            if re.search(r'tax invoice', qp, re.I): bad('high', 'Quotation is titled as a tax invoice')
            b.click('[data-act=convert]'); time.sleep(1.2); js(H)
            conv_toasts = []
            if 'new' in js('location.hash'):
                b.click('[data-save]'); time.sleep(1.5); js(H); conv_toasts = js('T.toasts()')
                if js('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.5)
            js(H)
            num2 = js('''(async()=>{const {db}=await import('./assets/js/db.js'); return (await db.all('documents')).filter(d=>d.type==='invoice').map(d=>d.number).sort()})()''')
            O['invoice_numbers'] = num2
            if len(num2) != 2: bad('high', f'Quotation conversion did not create a 2nd invoice ({num2}); messages: {conv_toasts}; hash {js("location.hash")}')
            elif num2[0][:-1] != num2[1][:-1] and num2[0][:-4] != num2[1][:-4]: bad('medium', f'Invoice numbering not sequential: {num2}')

        # --- Print dialog default paper + real PDF
        js(f'location.hash="#/bills/{inv_id}"'); b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.6)
        b.click('[data-act=print]'); time.sleep(1.2); js(H)
        paperSel = js('(T.q(".modal [data-o=paper]")?.selectedOptions[0]?.textContent)||""'); O['default_paper'] = paperSel
        if code in ('US', 'CA', 'MX', 'PH', 'CL', 'CO') and 'Letter' not in paperSel: bad('medium', f'Default paper for {code} is {paperSel} (Letter expected)')
        if code not in ('US', 'CA', 'MX', 'PH', 'CL', 'CO') and 'A4' not in paperSel: bad('low', f'Default paper is {paperSel} (A4 expected)')
        b.shot(f'{out}/{code}-5-print.png')
        js('T.qa(".overlay").forEach(o=>o.remove())')
        F.extend({'sev': 'js-error', 'msg': l} for l in b.logs if 'favicon' not in l)
    return F, O

if __name__ == '__main__':
    with Browser() as b:
        b.go(BASE + 'tests/unit.html'); time.sleep(1)
        countries = b.eval('''(async()=>{const m=await import('../assets/js/tax/countries.js'); return m.COUNTRY_LIST})()''')
    only = os.environ.get('ONLY')
    countries = [c for i, c in enumerate(countries) if i % NSHARDS == SHARD and (not only or c['code'] in only.split(','))]
    with open(OUTF, 'a') as f:
        for c in countries:
            try: F, O = journey(c, SHOTS)
            except Exception as e:
                import traceback; tb = traceback.extract_tb(e.__traceback__)[-2:]
                F, O = [{'sev': 'exception', 'msg': repr(e)[:200] + ' @ line ' + str([x.lineno for x in tb]) + ' screen: ' + str(LAST.get('screen'))[:300]}], {}
            f.write(json.dumps({'code': c['code'], 'name': c['name'], 'findings': F, 'obs': O}) + '\n'); f.flush()
            print(c['code'], len(F), [x['msg'][:90] for x in F], flush=True)
