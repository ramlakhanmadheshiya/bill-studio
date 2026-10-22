#!/usr/bin/env python3
"""Country sweep: onboard every country (registered + unregistered), create a bill, visit every screen,
and flag tax vocabulary that belongs to OTHER countries, wrong titles, and JS errors.
Usage: python3 tools/country_sweep.py [base-url] [shard] [nshards]"""
import sys, os, json, time, re
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
SHARD, NSHARDS = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)

SAMPLE_IDS = {
    'IN': '27AAPFU0939F1ZV', 'US': '12-3456789', 'GB': 'GB123456789', 'CA': '123456789RT0001', 'AU': '51824753556', 'NZ': '123456789',
    'SG': '201912345K', 'MY': 'W10-1808-31000001', 'AE': '100123456700003', 'SA': '300000000000003', 'BH': '123456789012345', 'OM': 'OM1100000000',
    'JP': 'T1234567890123', 'CH': 'CHE-123.456.789 MWST', 'NO': '123456789MVA', 'ZA': '4123456789', 'AT': 'ATU12345678', 'BE': 'BE0123456789',
    'BG': 'BG123456789', 'CY': 'CY12345678X', 'CZ': 'CZ12345678', 'DE': 'DE123456789', 'DK': 'DK12345678', 'EE': 'EE123456789', 'GR': 'EL123456789',
    'ES': 'ESA1234567B', 'FI': 'FI12345678', 'FR': 'FRAB123456789', 'HR': 'HR12345678901', 'HU': 'HU12345678', 'IE': 'IE1234567T', 'IT': 'IT12345678901',
    'LT': 'LT123456789', 'LU': 'LU12345678', 'LV': 'LV12345678901', 'MT': 'MT12345678', 'NL': 'NL123456789B01', 'PL': 'PL1234567890', 'PT': 'PT123456789',
    'RO': 'RO1234567', 'SE': 'SE123456789012', 'SI': 'SI12345678', 'SK': 'SK1234567890',
    'KR': '123-45-67890', 'TW': '12345678', 'CN': '91350100M000100Y43', 'TR': '1234567890', 'IL': '512345678', 'TZ': '123-456-789',
    'UG': '1000123456', 'MA': '001234567000089', 'AR': '20-12345678-9', 'CL': '76.123.456-7', 'CO': '900123456-7', 'PE': '20123456789', 'IS': '123456',
}
# Tax vocabulary that must only appear where it belongs.
VOCAB = ['GSTIN', 'HSN', 'IGST', 'CGST', 'SGST', 'UTGST', 'PAN', 'GST', 'VAT', 'HST', 'PST', 'QST', 'RST', 'IVA', 'PPN', 'SST', 'Consumption tax',
         'Sales tax', 'ABN', 'TRN', 'EIN', 'USt-IdNr', 'Steuernummer', 'NIF', 'OIB', 'NIP', 'KRA', 'NTN', 'MST', 'RFC', 'CNPJ', 'NPWP', 'BIN', 'Bill of Supply',
         '₹', 'lakh', 'crore', 'Place of supply', 'Composition', 'UPI', 'ZATCA', 'Qualified Invoice', 'Tax Invoice', 'reverse charge']
SCREENS = ['#/', '#/bills', '#/customers', '#/items', '#/money', '#/reports', '#/templates', '#/business', '#/settings']

def allowed_text(c):
    parts = [c.get('taxName', ''), c.get('taxIdLabel', ''), c.get('secondaryIdLabel') or '', c.get('notes') or '', c.get('eInvoice') or '',
             c.get('exemptNote') or '', json.dumps(c.get('docTitle', {})), ' '.join(p['label'] + ' ' + ' '.join(x['name'] for x in p.get('components', [])) for p in c['presets'])]
    t = ' '.join(parts)
    if c['code'] == 'IN': t += ' GSTIN HSN IGST CGST SGST UTGST PAN GST Bill of Supply ₹ lakh crore Place of supply Composition UPI Tax Invoice reverse charge'
    if c.get('qr') == 'zatca': t += ' ZATCA'
    if c.get('eu') or c['code'] == 'GB' or c.get('taxName') == 'VAT': t += ' reverse charge'
    return t

def scan(text, allowed):
    bad = set()
    for w in VOCAB:
        if re.search(r'(?<![A-Za-z])' + re.escape(w) + r'(?![A-Za-z])', text, re.I if w in ('lakh', 'crore', 'reverse charge') else 0) and w.lower() not in allowed.lower():
            bad.add(w)
    return bad

def run(code, scheme, c, out):
    issues = []
    with Browser(1300, 950) as b:
        b.go(BASE); b.wait('document.querySelector("[data-next]")', 15)
        b.click('[data-next]'); b.wait('document.querySelector("[data-c]")')
        b.click(f'[data-c="{code}"]'); time.sleep(0.2); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
        def setf(n, v):
            b.eval(f'(()=>{{const e=document.querySelector("[name={n}]"); if(!e) return; e.value={json.dumps(v)}; e.dispatchEvent(new Event("input",{{bubbles:true}})); e.dispatchEvent(new Event("change",{{bubbles:true}}));}})()'); time.sleep(0.25)
        if c.get('noTax') and scheme == 'regular': return []
        b.eval(f'(()=>{{const e=document.querySelector("select[name=taxScheme]"); if(e){{e.value={json.dumps(scheme)}; e.dispatchEvent(new Event("change",{{bubbles:true}}));}}}})()'); time.sleep(0.25)
        setf('name', f'{code} Test Co')
        if scheme == 'regular':
            setf('taxId', SAMPLE_IDS.get(code, 'TAX-12345'))
            setf('salesTaxRate', '8.25')
        setf('secondaryId', '12/345/67890')
        if code == 'IN': setf('region', '27')
        if code == 'CA': setf('region', 'ON')
        b.eval('(()=>{const s=document.querySelector("[data-seed]"); if(s && !s.checked) s.click();})()')
        b.click('[data-finish]'); time.sleep(2)
        if not b.eval('!!document.querySelector(".stat")'):
            issues.append('onboarding blocked: ' + str(b.eval('[...document.querySelectorAll(".toast span")].map(x=>x.textContent)')))
            return issues + b.logs
        allowed = allowed_text(c)
        for h in SCREENS:
            b.eval(f'location.hash={json.dumps(h)}'); time.sleep(1.1)
            txt = b.eval('document.querySelector("#view").innerText')
            bad = scan(txt, allowed)
            if bad: issues.append(f'{h}: foreign terms {sorted(bad)}')
            if 'Something went wrong' in txt: issues.append(f'{h}: error page')
        # tax report
        b.eval('location.hash="#/reports"'); time.sleep(0.8)
        b.eval('(()=>{const r=document.querySelector("[data-r=gstr1],[data-r=tax]"); r && r.click();})()'); time.sleep(0.8)
        bad = scan(b.eval('document.querySelector("#view").innerText'), allowed)
        if bad: issues.append(f'tax report: foreign terms {sorted(bad)}')
        # editor + saved bill
        b.eval('location.hash="#/bills/new/invoice"'); b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.6)
        bad = scan(b.eval('document.querySelector("#view").innerText'), allowed)
        if bad: issues.append(f'editor: foreign terms {sorted(bad)}')
        b.eval('''(()=>{const set=(s,v)=>{const e=document.querySelector(s); if(!e) return; e.value=v; e.dispatchEvent(new Event("input",{bubbles:true}));};
          set("[data-cust-input]","Acme Buyer"); set('[data-k="customer.address"]',"1 Main Road"); set('[data-k="items.0.name"]',"Service fee"); set('[data-k="items.0.rate"]',"100");})()''')
        time.sleep(0.4); b.click('[data-save]'); time.sleep(1.5)
        if '/new/' in b.eval('location.hash'):
            # a soft-warning confirm may be open
            if b.eval('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.5)
        if '/new/' in b.eval('location.hash'):
            issues.append('could not save bill: ' + str(b.eval('[...document.querySelectorAll(".toast span")].map(x=>x.textContent)')))
        else:
            b.wait('document.querySelector("[data-paper] .bill-page")', 10); time.sleep(0.8)
            paper = b.eval('document.querySelector("[data-paper] .bill-page").innerText')
            bad = scan(paper, allowed)
            if bad: issues.append(f'printed bill: foreign terms {sorted(bad)}')
            exp = b.eval('''(async()=>{const s=await import('./assets/js/store.js'); const id=location.hash.split('/').pop(); const d=await (await import('./assets/js/db.js')).db.get('documents',id); return s.docTitle(d.type, s.bizFor(d), d)})()''')
            title = b.eval('document.querySelector("[data-paper] .b-title").innerText')
            if exp.lower() not in title.lower(): issues.append(f'title mismatch: expected {exp} got {title!r}')
            if scheme == 'unregistered':
                if re.search(r'\d+(\.\d+)?%', b.eval('document.querySelector("[data-paper] .b-totals")?.innerText || ""')): issues.append('unregistered bill shows a tax %')
                if c['taxIdLabel'] in paper and code != 'AU': issues.append('unregistered bill prints tax id label')
                if c.get('exemptNote') and c['exemptNote'][:20] not in paper: issues.append('missing small-business exemption note')
            else:
                if code not in ('US', 'OTHER', 'BR') and c['taxIdLabel'].split(' (')[0] not in paper: issues.append('registered bill missing seller tax ID')
            b.shot(f'{out}/{code}-{scheme}.png')
        issues += [l for l in b.logs if 'favicon' not in l]
    return issues

if __name__ == '__main__':
    out = '/private/tmp/claude-501/-Users-ramlakhan-Desktop-Projests/de10ec63-a650-4f6e-b43f-0d3dab730a18/scratchpad/sweep'
    os.makedirs(out, exist_ok=True)
    with Browser() as b:
        b.go(BASE + 'tests/unit.html'); time.sleep(1)
        countries = b.eval('''(async()=>{const m=await import('../assets/js/tax/countries.js'); return m.COUNTRY_LIST})()''')
    countries = [c for i, c in enumerate(countries) if i % NSHARDS == SHARD]
    total = 0
    for c in countries:
        for scheme in ('regular', 'unregistered'):
            try:
                iss = run(c['code'], scheme, c, out)
            except Exception as e:
                iss = [f'EXCEPTION {e}']
            total += len(iss)
            print(f"{c['code']:5} {scheme:12} {'OK' if not iss else '; '.join(iss)}", flush=True)
    print('ISSUES:', total)
