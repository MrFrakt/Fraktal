from pathlib import Path
import unittest
from manual_window import BROWSER_WINDOW_SECONDS,GATEWAY_TTL_MINUTES,MONITOR_MAX_SECONDS
from gateway_stage import gateway_arguments
class Window(unittest.TestCase):
    def test_gateway_lease_covers_browser_and_startup(self):
        args=gateway_arguments(Path('gateway.exe'),Path('.'),'echo',8080,True)
        ttl=int(args[args.index('--commissioning-ttl-minutes')+1])
        self.assertEqual(ttl,GATEWAY_TTL_MINUTES)
        self.assertGreaterEqual(ttl*60,BROWSER_WINDOW_SECONDS+600)
        self.assertLessEqual(ttl,1440)
    def test_monitor_covers_full_owner_window_plus_native_reads(self):
        self.assertEqual(BROWSER_WINDOW_SECONDS,7200)
        self.assertGreaterEqual(MONITOR_MAX_SECONDS,BROWSER_WINDOW_SECONDS+1200)
if __name__=='__main__':unittest.main()
