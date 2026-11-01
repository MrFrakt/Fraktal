import json, unittest
from browser_wire_observer import safe_console, safe_received, allowed_cdp

class ConsoleSafety(unittest.TestCase):
    def test_late_sample_keeps_only_public_timing_fields(self):
        result=safe_console('[Fraktal/Freshness] stage=complete-sample-rejected sourceAgeUs=1100001 rpcUs=300000 responseProcessingMs=200.5 Secret=private TextValue=private User=private')
        self.assertEqual(result,dict(channel='Freshness',stage='complete-sample-rejected',sourceAgeUs=1100001.0,rpcUs=300000.0,responseProcessingMs=200.5))
        self.assertNotIn('private',json.dumps(result))
    def test_unknown_console_stage_and_other_console_are_ignored(self):
        self.assertIsNone(safe_console('[Fraktal/Connection] stage=private'))
        self.assertIsNone(safe_console('private'))
        self.assertIsNone(safe_console({'value':'private'}))
    def test_connection_failure_has_a_constant_class_without_error_text(self):
        result=safe_console('[Fraktal/Connection] stage=startup-failed error=Complete station sample is late or expired. private')
        self.assertEqual(result['failureClass'],'late-station-sample')
        self.assertNotIn('private',json.dumps(result))
    def test_snapshot_metadata_drops_private_fields_and_invalid_numbers(self):
        result=safe_received(json.dumps(dict(id=3,ok=True,result=dict(sampleAgeMs=4.5,responseProcessingMs=6,nodeCount='private',Secret='private'))),[])
        self.assertEqual(result,dict(ok=True,rpcId=3,sampleAgeMs=4.5,responseProcessingMs=6))
        self.assertNotIn('private',json.dumps(result))
    def test_no_browser_action_or_script_installation_is_allowed(self):
        for method in ('Input.dispatchMouseEvent','Input.dispatchKeyEvent','Page.navigate','Page.addScriptToEvaluateOnNewDocument'):
            self.assertFalse(allowed_cdp(method,{}))
        self.assertFalse(allowed_cdp('Runtime.evaluate',dict(expression='private',returnByValue=True)))

if __name__=='__main__':unittest.main()
