#!/usr/bin/env python3
"""Team & permissions end-to-end: sign-up, roles, forced password change, what each role can see and do,
manager limits, disable/lockout, owner recovery, legacy migration and moving the team to a new device.
Usage: python3 tools/team_test.py [base-url]"""
import sys, os, json, time, re, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
fails = []
def check(name, cond, info=''):
    print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''), flush=True)
    if not cond: fails.append(name)

H = '''window.T={q:(s)=>document.querySelector(s),qa:(s)=>[...document.querySelectorAll(s)],
  set(sel,v,root=document){const e=root.querySelector(sel); if(!e) return false; if(e.type==='checkbox'||e.type==='radio') e.checked=!!v; else e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return true;},
  text:(s)=>document.querySelector(s)?.innerText||'', toasts:()=>[...document.querySelectorAll('.toast span')].map(x=>x.textContent),
  navs:()=>[...document.querySelectorAll('.sidebar .nav a')].map(a=>a.textContent.trim()),
  visible:(s)=>{const e=document.querySelector(s); return !!e && getComputedStyle(e).display!=='none' && !!e.offsetParent;}};'''

def js(b, s): b.eval(H); return b.eval(s)

def onboard(b, name='Main Store'):
    b.wait('document.querySelector("[data-next]")', 15)
    b.click('[data-next]'); b.click('[data-c="IN"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
    js(b, f'T.set("[name=name]",{json.dumps(name)}); T.set("[name=region]","27"); T.set("[name=taxId]","27AAPFU0939F1ZV"); (()=>{{const s=T.q("[data-seed]"); if(s&&s.checked) s.click();}})()')
    b.click('[data-finish]'); b.wait('document.querySelector(".stat")', 20); time.sleep(0.5)

def go(b, hash):
    b.eval(f'location.hash={json.dumps(hash)}'); time.sleep(1.0); b.eval(H)

def login_as(b, user, pw):
    """From the home page: Log in; returns error text or ''."""
    b.wait('document.querySelector(".landing")', 10); time.sleep(0.3)
    b.eval('document.querySelector("[data-login]").click()'); time.sleep(0.4)
    b.eval(f'''(()=>{{const f=document.querySelector(".modal [data-form]"); f.username.value={json.dumps(user)}; f.password.value={json.dumps(pw)}; f.requestSubmit();}})()'''); time.sleep(1.4)
    return b.eval('document.querySelector(".modal [data-err]")?.textContent || ""')

def sign_out(b):
    b.eval('(async()=>{const a=await import("./assets/js/auth.js"); a.signOut();})()'); time.sleep(1.6)
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')

def add_member(b, name, user, role, bizNames=None):
    go(b, '#/team'); b.wait('document.querySelector("[data-add]")'); b.click('[data-add]'); time.sleep(0.4)
    js(b, f'''(()=>{{const m=T.q(".modal"); T.set("[name=name]",{json.dumps(name)},m); T.set("[name=username]",{json.dumps(user)},m); T.set("[name=roleId]",{json.dumps(role)},m);
      {('T.set("[name=bizMode][value=some]",true,m); T.qa(".modal [data-bizlist] label").forEach(l=>{ if(%s.includes(l.textContent.trim())) l.querySelector("input").checked=true; });' % json.dumps(bizNames)) if bizNames else ''}}})()''')
    temp = b.eval('document.querySelector(".modal [name=temp]").value')
    b.click('.modal [data-ok]'); time.sleep(1.0)
    shown = b.eval('document.querySelector(".modal")?.innerText || ""')
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    return temp, shown

def first_login(b, user, temp, newpw):
    err = login_as(b, user, temp)
    if err: return 'login: ' + err
    if not b.eval('!!document.querySelector("[name=pw2]")'): return 'no forced password change'
    js(b, f'T.set("[name=cur]",{json.dumps(temp)}); T.set("[name=pw]",{json.dumps(newpw)}); T.set("[name=pw2]",{json.dumps(newpw)}); T.q("[data-form]").requestSubmit()'); time.sleep(1.8)
    return b.eval('document.querySelector("[name=pw2]") ? "still on password page: " + (document.querySelector("[data-err]")?.textContent || "") : ""')

def new_bill(b, cust, rate):
    go(b, '#/bills/new/invoice'); b.wait('document.querySelector("[data-paper] .bill-page")', 12); time.sleep(0.4)
    js(b, f'''T.set("[data-cust-input]",{json.dumps(cust)}); T.set('[data-k="items.0.name"]',"Service"); T.set('[data-k="items.0.rate"]',"{rate}"); T.set('[data-k="items.0.hsn"]',"9983")''')
    b.click('[data-save]'); time.sleep(1.5)
    if b.eval('!!document.querySelector(".modal [data-ok]")'): b.click('.modal [data-ok]'); time.sleep(1.5)
    return '/new/' not in b.eval('location.hash')

profile = tempfile.mkdtemp(prefix='bs-team-')
with Browser(1300, 950, profile=profile) as b:
    b.go(BASE, login=False); b.wait('document.querySelector(".landing")', 15); b.eval(H)
    txt = b.eval('document.body.innerText')
    check('home page shown first (not a login wall)', b.eval('!!document.querySelector(".landing") && !document.querySelector(".modal")'))
    check('no default credentials anywhere', '12345' not in txt and '67890' not in txt)
    check('Log in + Sign up in the corner', b.eval('T.qa(".land-top button").map(x=>x.textContent.trim()).join("|")') .endswith('Log in|Sign up'))
    # sign-up validation
    b.eval('document.querySelector("[data-signup]").click()'); time.sleep(0.4)
    js(b, '(()=>{const f=T.q(".modal [data-form]"); f.name.value="Anita Rao"; f.orgName.value="Rao Group"; f.username.value="anita"; f.password.value="short"; f.password2.value="short"; f.requestSubmit();})()'); time.sleep(0.6)
    check('weak password rejected at sign-up', 'at least 8' in b.eval('T.text(".modal [data-err]")'))
    js(b, '(()=>{const f=T.q(".modal [data-form]"); f.password.value="Owner2026pass"; f.password2.value="Owner2026pass"; f.requestSubmit();})()'); time.sleep(1.6)
    key = b.eval('document.querySelector(".modal [data-key]")?.textContent || ""')
    check('recovery key shown once', bool(re.match(r'^[A-Z0-9]{5}(-[A-Z0-9]{5}){3}$', key)), key)
    b.eval('document.querySelector(".modal [data-close]").click()'); time.sleep(0.4)
    check('recovery key cannot be skipped', b.eval('!!document.querySelector(".modal [data-key]")'))
    b.eval('(()=>{const a=document.querySelector(".modal [data-ack]"); a.click(); document.querySelector(".modal [data-ok]").click();})()'); time.sleep(0.8)
    onboard(b, 'Main Store')
    check('owner reaches dashboard', b.eval('!!document.querySelector(".shell")'))
    check('owner sees Team in menu', 'Team' in js(b, 'T.navs()'))
    # second business
    go(b, '#/welcome'); b.wait('document.querySelector("[data-c]")', 10)
    b.click('[data-c="IN"]'); b.click('[data-next]'); b.wait('document.querySelector("[name=name]")')
    js(b, 'T.set("[name=name]","Branch Pune"); T.set("[name=region]","27"); T.set("[name=taxId]","27AAPFU0939F1ZV")'); b.click('[data-finish]'); time.sleep(2)
    check('second business created', b.eval('(async()=>{const {db}=await import("./assets/js/db.js"); return (await db.all("businesses")).length})()') == 2)
    ok = new_bill(b, 'Owner Customer', 1000)
    check('owner creates a bill', ok)

    t_mgr, shown = add_member(b, 'Mohan Manager', 'mohan', 'manager')
    check('member added; temp password shown once', t_mgr in shown and 'mohan' in shown)
    t_acc, _ = add_member(b, 'Asha Accounts', 'asha', 'accountant')
    t_sal, _ = add_member(b, 'Sunil Sales', 'sunil', 'sales', ['Branch Pune'])
    users = b.eval('(async()=>{const {db}=await import("./assets/js/db.js"); return (await db.all("users")).map(u=>[u.username,u.roleId,u.businessIds.length,u.mustChangePassword,!!u.hash, JSON.stringify(u).includes("%s")])})()' % t_sal)
    check('4 users, passwords stored only as hashes', len(users) == 4 and all(u[4] and not u[5] for u in users), str(users))
    sign_out(b)

    # --- Sales staff
    check('sales: first sign-in forces own password', first_login(b, 'Sunil', t_sal, 'Blue2026river') == '')
    try: b.wait('document.querySelector(".shell")', 10)
    except TimeoutError: print('SCREEN', b.eval('location.hash + " | " + document.body.innerText.slice(0,400)'), b.logs[-5:]); raise
    b.eval(H)
    navs = js(b, 'T.navs()')
    check('sales menu limited', 'Bills' in navs and 'Customers' in navs and not any(x in navs for x in ['Reports', 'Team', 'Business profile', 'Templates']), str(navs))
    check('sales sees only allowed business', b.eval('(async()=>{const s=await import("./assets/js/store.js"); return s.state.businesses.map(x=>x.name)})()') == ['Branch Pune'])
    go(b, '#/reports'); check('sales blocked from Reports', 'don’t have access' in b.eval('document.querySelector("#view").innerText'))
    go(b, '#/team'); check('sales blocked from Team', 'don’t have access' in b.eval('document.querySelector("#view").innerText'))
    check('sales can create a bill', new_bill(b, 'Sunil Customer', 500))
    more = b.eval('(()=>{document.querySelector("[data-more]").click(); const r=[...document.querySelectorAll(".menu button, .menu [role=menuitem], .menu a")].map(x=>x.textContent.trim()); document.querySelectorAll(".menu").forEach(m=>m.remove()); return r})()')
    check('sales cannot cancel or delete bills', not any('Delete' in x or 'Cancel bill' in x for x in more), str(more))
    go(b, '#/bills'); time.sleep(0.4)
    bills_txt = b.eval('document.querySelector("#view").innerText')
    check('sales sees only own bills', 'Sunil Customer' in bills_txt and 'Owner Customer' not in bills_txt)
    sign_out(b)

    # --- Manager
    check('manager: first sign-in', first_login(b, 'mohan', t_mgr, 'Green2026hill') == '')
    b.wait('document.querySelector(".shell")', 10)
    navs = js(b, 'T.navs()')
    check('manager sees Reports and Team', 'Reports' in navs and 'Team' in navs, str(navs))
    go(b, '#/team'); b.wait('document.querySelector("[data-add]")'); b.click('[data-add]'); time.sleep(0.4)
    opts = b.eval('[...document.querySelectorAll(".modal [name=roleId] option")].map(o=>[o.value,o.disabled])')
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    ids = [o[0] for o in opts if not o[1]]
    check('manager can give only lower roles', 'admin' not in ids and 'owner' not in ids and 'manager' not in ids and 'sales' in ids, str(opts))
    rows = b.eval('[...document.querySelectorAll("tr[data-u]")].map(r=>[r.innerText.split("\\n")[0], r.classList.contains("click")])')
    check('manager cannot manage the owner', not any(r[1] for r in rows if r[0].startswith('Anita')), str(rows))
    t_cash, _ = add_member(b, 'Chetan Cashier', 'chetan', 'sales')
    check('manager adds a cashier', len(t_cash) >= 8)
    sign_out(b)

    # --- Accountant
    check('accountant: first sign-in', first_login(b, 'asha', t_acc, 'Red2026lake') == '')
    b.wait('document.querySelector(".shell")', 10)
    go(b, '#/reports'); check('accountant can open Reports', 'don’t have access' not in b.eval('document.querySelector("#view").innerText'))
    go(b, '#/bills/new/invoice'); check('accountant cannot create bills', 'don’t have access' in b.eval('document.querySelector("#view").innerText'))
    go(b, '#/bills'); check('accountant sees everyone’s bills', 'Owner Customer' in b.eval('document.querySelector("#view").innerText'))
    sign_out(b)

    # --- Owner: disable sunil; lockout; activity log; recovery
    check('owner logs back in', login_as(b, 'anita', 'Owner2026pass') == '')
    b.wait('document.querySelector(".shell")', 10)
    go(b, '#/team'); b.eval('[...document.querySelectorAll("tr[data-u]")].find(r=>r.innerText.includes("Sunil")).click()'); time.sleep(0.5)
    b.eval('document.querySelector(".modal [data-toggle]").click()'); time.sleep(0.5)
    b.eval('[...document.querySelectorAll(".modal")].at(-1).querySelector("[data-ok]").click()'); time.sleep(0.8)
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    go(b, '#/team?tab=activity'); time.sleep(0.6)
    log = b.eval('document.querySelector("#view").innerText')
    for a in ['Organisation created', 'Team member added', 'Signed in', 'Invoice created', 'Team member disabled']:
        check(f'activity log has “{a}”', a in log)
    sign_out(b)
    check('disabled account refused', 'disabled' in login_as(b, 'sunil', 'Blue2026river'))
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    for i in range(5):
        e = login_as(b, 'chetan', 'wrong-pass-1'); b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    check('account locks after 5 wrong passwords', 'locked' in e, e)
    b.eval('document.querySelector("[data-login]").click()'); time.sleep(0.3); b.eval('document.querySelector(".modal [data-forgot]").click()'); time.sleep(0.4)
    js(b, f'T.set(".modal [name=key]",{json.dumps(key.lower())}); T.set(".modal [name=pw]","NewOwner2026"); T.set(".modal [name=pw2]","NewOwner2026"); T.q(".modal [data-form]").requestSubmit()'); time.sleep(1.5)
    b.eval('document.querySelectorAll(".overlay").forEach(o=>o.remove())')
    check('owner resets password with recovery key', login_as(b, 'anita', 'NewOwner2026') == '')
    b.wait('document.querySelector(".shell")', 10)
    backup = b.eval('(async()=>{const k=await import("./assets/js/backup.js"); return await (await k.makeBackup("pp")).text()})()')
    logs = [l for l in b.logs if 'favicon' not in l]
    check('no console errors (device 1)', not logs, str(logs[:3]))

# --- New device: restore the full backup from the home page, team comes along
with Browser(1300, 950) as b2:
    b2.go(BASE, login=False); b2.wait('document.querySelector(".landing")', 15)
    r = b2.eval('(async()=>{const k=await import("./assets/js/backup.js"); const d=await k.readBackup(%s,"pp"); await k.importData(d,"replace"); return true})()' % json.dumps(backup))
    b2.eval('location.reload()'); time.sleep(2)
    check('new device: home page offers Log in only', b2.eval('!document.querySelector("[data-signup]") && !!document.querySelector("[data-login]")'))
    check('new device: manager signs in with same password', login_as(b2, 'mohan', 'Green2026hill') == '')

# --- Legacy device (single 12345 owner sign-in) is migrated to an Owner account
with Browser(1300, 950) as b3:
    b3.go(BASE, login=False); b3.wait('document.querySelector(".landing")', 15)
    b3.eval('''(async()=>{const {db}=await import("./assets/js/db.js"); const enc=new TextEncoder(); const salt="00112233445566778899aabbccddeeff";
      const key=await crypto.subtle.importKey("raw",enc.encode("67890"),"PBKDF2",false,["deriveBits"]);
      const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt:Uint8Array.from(salt.match(/../g).map(h=>parseInt(h,16))),iterations:1000,hash:"SHA-256"},key,256);
      const hash=[...new Uint8Array(bits)].map(b=>b.toString(16).padStart(2,"0")).join("");
      await db.setting("auth",{userId:"12345",salt,iterations:1000,hash,ownerName:"Old Owner",autoLockMin:15,isDefault:true});})()''')
    b3.eval('location.reload()'); time.sleep(2)
    err = login_as(b3, '12345', '67890')
    check('legacy sign-in migrates and forces a new password', err == '' and b3.eval('!!document.querySelector("[name=pw2]")'), err)

print('\nFAILS:' if fails else '\nALL TEAM CHECKS PASSED', *fails, sep='\n')
