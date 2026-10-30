#!/usr/bin/env python3
"""Tiny Chrome DevTools Protocol driver (stdlib only) for smoke-testing Bill Studio.

Usage in scripts:
    from cdp import Browser
    with Browser() as b:
        b.go('http://127.0.0.1:8765/'); b.wait('document.querySelector(".welcome")')
        b.eval('...'); b.shot('out.png')
"""
import base64, json, os, socket, struct, subprocess, tempfile, time, urllib.request, shutil

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


class WS:
    def __init__(self, url):
        assert url.startswith('ws://')
        hostport, path = url[5:].split('/', 1)
        host, port = hostport.split(':')
        self.s = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f'GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            resp += self.s.recv(4096)
        self.buf = resp.split(b'\r\n\r\n', 1)[1]

    def send(self, text):
        data = text.encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr.append(0x80 | 126); hdr += struct.pack('>H', n)
        else: hdr.append(0x80 | 127); hdr += struct.pack('>Q', n)
        mask = os.urandom(4)
        self.s.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk: raise ConnectionError('socket closed')
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b''
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7f
            if n == 126: n = struct.unpack('>H', self._read(2))[0]
            elif n == 127: n = struct.unpack('>Q', self._read(8))[0]
            payload = self._read(n)
            msg += payload
            if b1 & 0x80: return msg.decode('utf-8', 'replace')


class Browser:
    def __init__(self, width=1440, height=960, mobile=False, profile=None):
        self.width, self.height, self.mobile = width, height, mobile
        self.profile = profile or tempfile.mkdtemp(prefix='bs-cdp-')
        self.port = 9300 + os.getpid() % 500
        self.proc = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--remote-debugging-port={self.port}',
                                      f'--user-data-dir={self.profile}', '--no-first-run', '--no-default-browser-check', 'about:blank'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json'))
                page = [t for t in tabs if t.get('type') == 'page'][0]
                break
            except Exception:
                time.sleep(0.1)
        self.ws = WS(page['webSocketDebuggerUrl'])
        self.id = 0
        self.logs = []
        self.cmd('Runtime.enable'); self.cmd('Page.enable'); self.cmd('Log.enable')
        self.cmd('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=1 if not mobile else 2, mobile=mobile)
        if mobile:
            self.cmd('Emulation.setTouchEmulationEnabled', enabled=True)

    def cmd(self, method, **params):
        self.id += 1
        mid = self.id
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get('method') == 'Runtime.exceptionThrown':
                d = m['params']['exceptionDetails']
                self.logs.append('EXCEPTION ' + (d.get('exception', {}).get('description') or d.get('text', '')))
            elif m.get('method') == 'Runtime.consoleAPICalled' and m['params']['type'] in ('error', 'warning'):
                self.logs.append('CONSOLE.' + m['params']['type'] + ' ' + ' '.join(str(a.get('value', a.get('description', ''))) for a in m['params']['args']))
            elif m.get('method') == 'Log.entryAdded' and m['params']['entry']['level'] == 'error':
                self.logs.append('LOG ' + m['params']['entry']['text'] + ' ' + m['params']['entry'].get('url', ''))
            if m.get('id') == mid:
                if 'error' in m: raise RuntimeError(f"{method}: {m['error']}")
                return m.get('result', {})

    def eval(self, expr, await_promise=True):
        r = self.cmd('Runtime.evaluate', expression=expr, awaitPromise=await_promise, returnByValue=True)
        if 'exceptionDetails' in r:
            raise RuntimeError('JS error: ' + json.dumps(r['exceptionDetails'].get('exception', {}).get('description', r['exceptionDetails'])))
        return r.get('result', {}).get('value')

    def go(self, url, login=True):
        self.cmd('Page.navigate', url=url)
        time.sleep(0.6)
        if login and 'tests/' not in url:
            self.login()

    def login(self, user='owner', password='Test1234pass', timeout=10, name='Test Owner'):
        """Get past the public home page: sign up as the owner on a fresh device, otherwise log in.
        Returns True if it signed in / up, False if the app was already open."""
        t = time.time()
        while time.time() - t < timeout:
            state = self.eval('document.querySelector(".landing") ? (document.querySelector("[data-signup]") ? "signup" : "login") : (document.querySelector(".welcome, .shell") ? "app" : "")')
            if state == 'app': return False
            if state == 'signup':
                self.eval('document.querySelector("[data-signup]").click()'); time.sleep(0.4)
                self.eval(f'''(()=>{{const f=document.querySelector(".modal [data-form]"); f.name.value={json.dumps(name)}; f.username.value={json.dumps(user)}; f.password.value={json.dumps(password)}; f.password2.value={json.dumps(password)}; f.requestSubmit();}})()''')
                time.sleep(1.5)
                self.eval('(()=>{const a=document.querySelector(".modal [data-ack]"); if(a){a.click(); document.querySelector(".modal [data-ok]").click();}})()')
                time.sleep(0.8)
                return True
            if state == 'login':
                self.eval('document.querySelector("[data-login]").click()'); time.sleep(0.4)
                self.eval(f'''(()=>{{const f=document.querySelector(".modal [data-form]"); f.username.value={json.dumps(user)}; f.password.value={json.dumps(password)}; f.requestSubmit();}})()''')
                time.sleep(1.3)
                return bool(self.eval('!document.querySelector(".landing")'))
            time.sleep(0.15)
        return False

    def wait(self, expr, timeout=10):
        t = time.time()
        while time.time() - t < timeout:
            try:
                if self.eval(f'!!({expr})'): return True
            except RuntimeError:
                pass
            time.sleep(0.15)
        raise TimeoutError('wait: ' + expr)

    def click(self, selector):
        sel = json.dumps(selector)
        self.eval(f'(()=>{{const e=document.querySelector({sel}); if(!e) throw new Error("no element " + {sel}); e.click();}})()')
        time.sleep(0.35)

    def shot(self, path, full=False):
        time.sleep(0.4)
        params = {'format': 'png'}
        if full:
            h = self.eval('Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)')
            params['clip'] = {'x': 0, 'y': 0, 'width': self.width, 'height': min(h, 6000), 'scale': 1}
            params['captureBeyondViewport'] = True
        data = self.cmd('Page.captureScreenshot', **params)['data']
        open(path, 'wb').write(base64.b64decode(data))
        return path

    def close(self):
        try: self.proc.terminate(); self.proc.wait(5)
        except Exception: self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)

    def __enter__(self): return self
    def __exit__(self, *a): self.close()
