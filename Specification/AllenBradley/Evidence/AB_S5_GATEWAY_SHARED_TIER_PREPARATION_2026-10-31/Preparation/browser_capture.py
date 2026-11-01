"""Open only an owned fresh Chrome profile; the owner performs every UI action."""
from pathlib import Path
import hashlib,json,socket,subprocess,sys,time,urllib.request
from s5_session import authorize
from manual_window import BROWSER_WINDOW_SECONDS

D=Path(__file__).parent
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
PORT=19114

class CapturedBrowser:
    def __init__(self,save):
        self.save=save;self.browser=None;self.observer=None;self.log=None
    def __enter__(self):
        authorize(json.loads((D/'authorization.json').read_bytes()))
        assert CHROME.is_file()
        with socket.socket() as probe:probe.bind(('127.0.0.1',PORT))
        profile=D/'browser_profile'
        assert not profile.exists(),'Fresh owned browser profile required'
        return self
    def open(self):
        self.log=(D/'browser_rpc_observer.log').open('x',encoding='utf-8')
        self.observer=subprocess.Popen([sys.executable,str(D/'browser_wire_observer.py'),
            '--directory',str(D),'--port',str(PORT),'--seconds',str(BROWSER_WINDOW_SECONDS+60)],
            cwd=D,stdout=self.log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        self.browser=subprocess.Popen([str(CHROME),'--user-data-dir='+str(D/'browser_profile'),
            '--remote-debugging-address=127.0.0.1','--remote-debugging-port='+str(PORT),
            '--no-first-run','--no-default-browser-check','--disable-background-mode',
            '--new-window','http://127.0.0.1:8080/'])
        deadline=time.monotonic()+60;version=None
        while time.monotonic()<deadline:
            if self.browser.poll() is not None:raise RuntimeError('Owned Chrome exited during startup')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/version',timeout=1) as response:
                    version=json.load(response).get('Browser')
            except (OSError,ValueError):pass
            if version and (D/'browser_rpc_page_ready.json').exists():break
            if self.observer.poll() is not None:raise RuntimeError('Read-only browser observer exited before ready')
            time.sleep(.1)
        else:raise TimeoutError('Owned browser instrumentation did not become ready')
        self.save('browser_capture_ready.json',dict(ready=True,readOnlyObservation=True,
            chromeVersion=version,chromeExecutableSha256=hashlib.sha256(CHROME.read_bytes()).hexdigest().upper(),
            profile=str(D/'browser_profile'),browserPid=self.browser.pid,observerPid=self.observer.pid,
            debuggingLoopbackPort=PORT,url='http://127.0.0.1:8080/',
            noAutomatedClicksOrCommands=True,credentialValuesRecorded=False))
    def __exit__(self,kind,error,stack):
        forcedObserver=False;forcedBrowser=False
        if self.observer is not None:
            with (D/'browser_rpc_observer_stop.json').open('x',encoding='utf-8') as stream:json.dump(dict(stop=True),stream)
            try:self.observer.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.observer.terminate();self.observer.wait(timeout=10);forcedObserver=True
        if self.log:self.log.close()
        if self.browser is not None and self.browser.poll() is None:
            try:self.browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # This handle belongs only to the unique task profile above.
                self.browser.terminate();self.browser.wait(timeout=10);forcedBrowser=True
        self.save('browser_capture_cleanup.json',dict(ownedProcessesOnly=True,
            observerForcedStop=forcedObserver,browserForcedStop=forcedBrowser,
            profileNotArchived=True,controllerWrites=0,echoHardKills=0))
        return False
