"""Open a fresh owned Chrome window; every acceptance action remains manual."""
from pathlib import Path
import hashlib,subprocess
from s5_session import authorize
import json
D=Path(__file__).parent
CHROME=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')

class OwnerBrowser:
    def __init__(self,save):self.save=save;self.browser=None
    def __enter__(self):
        authorize(json.loads((D/'authorization.json').read_bytes()))
        assert CHROME.is_file() and not (D/'browser_profile').exists()
        return self
    def open(self):
        self.browser=subprocess.Popen([str(CHROME),'--user-data-dir='+str(D/'browser_profile'),
            '--no-first-run','--no-default-browser-check','--disable-background-mode',
            '--new-window','http://127.0.0.1:8080/'])
        self.save('browser_window_opened.json',dict(opened=True,url='http://127.0.0.1:8080/',
            browserPid=self.browser.pid,freshProfile=True,
            chromeExecutableSha256=hashlib.sha256(CHROME.read_bytes()).hexdigest().upper(),
            noAutomatedClicksLoginModeOrChecklist=True,credentialValuesRecorded=False))
    def __exit__(self,kind,error,stack):
        forced=False
        if self.browser is not None and self.browser.poll() is None:
            try:self.browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.browser.terminate();self.browser.wait(timeout=10);forced=True
        self.save('owner_browser_cleanup.json',dict(ownedBrowserOnly=True,forcedStop=forced,
            profileNotArchived=True,controllerWrites=0,echoHardKills=0))
        return False
