import sys
sys.path.pop(0)
from pathlib import Path
import http.server, json, socket, subprocess, threading

W=Path('C:/work/fraktal-ab-s5-20261029')
D=W/'browser_smoke_15_01'
assert not D.exists()
D.mkdir()
class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'''<!doctype html><title>Read-only diagnostic self-test</title><script>setInterval(()=>console.log('[Fraktal/Freshness] stage=complete-sample-rejected sourceAgeUs=1100001 rpcUs=350000'),1000)</script>'''
        self.send_response(200)
        self.send_header('Content-Type','text/html')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args):pass

with socket.socket() as check:check.bind(('127.0.0.1',19114))
server=http.server.ThreadingHTTPServer(('127.0.0.1',8080),Page)
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
chrome=None
try:
    with (D/'chrome_private.log').open('x',encoding='utf-8') as output:
        chrome=subprocess.Popen(['C:/Program Files/Google/Chrome/Application/chrome.exe',
            '--headless=new','--user-data-dir='+str(D/'browser_profile'),
            '--remote-debugging-address=127.0.0.1','--remote-debugging-port=19114',
            '--no-first-run','--no-default-browser-check','--disable-background-mode',
            'http://127.0.0.1:8080/'],stdout=output,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        result=subprocess.run([sys.executable,str(W/'session_15/browser_wire_observer.py'),
            '--directory',str(D),'--port','19114','--seconds','10'],
            cwd=W/'session_15',check=True)
    events=[json.loads(line) for line in (D/'browser_rpc_events.log').read_text(encoding='utf-8').splitlines()]
    assert any(r.get('event')=='page-observed' for r in events)
    assert any(r.get('event')=='client-console' and r.get('sourceAgeUs')==1100001 for r in events)
    with (W/'session_15/browser_trace_smoke_result.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(passed=True,readOnly=True,realChrome=True,controllerAccess=False,
            UIActions=0,traceRecords=len(events),profileNotArchived=True),stream,indent=2)
    print(json.dumps(dict(passed=True,controllerAccess=False,UIActions=0,traceRecords=len(events))))
finally:
    server.shutdown();server.server_close()
    if chrome is not None and chrome.poll() is None:
        chrome.terminate();chrome.wait(timeout=10)
