#!/usr/bin/env python3
"""Run tests/unit.html in headless Chrome and print failures. Usage: python3 tools/unit.py [base-url]"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from cdp import Browser
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
with Browser() as b:
    b.go(BASE + 'tests/unit.html', login=False); time.sleep(2.5)
    t = b.eval('document.getElementById("out").textContent')
    print('\n'.join(l for l in t.splitlines() if not l.startswith('PASS')))
    print([l for l in b.logs if 'favicon' not in l])
