import json,unittest
from browser_wire_observer import safe_sent,safe_received,safe_url,allowed_cdp,STORAGE_EXPRESSION

class Redaction(unittest.TestCase):
    def test_login_values_never_enter_event(self):
        message=dict(protocol='fraktal.opcua.gateway.v1',id=9,method='writeBatch',params=dict(writes=[
            dict(path='Press/HmiRequest/Kind',value=1),dict(path='Press/HmiRequest/Sequence',value=23),
            dict(path='Press/HmiRequest/User',value='SYNTHETIC_USER'),dict(path='Press/HmiRequest/Secret',value='SYNTHETIC_PIN'),
            dict(path='Press/HmiRequest/TextValue',value='SYNTHETIC_TEXT')]))
        observed=safe_sent(json.dumps(message));text=json.dumps(observed)
        self.assertEqual(observed['kind'],1);self.assertEqual(observed['sequence'],23)
        for secret in ('SYNTHETIC_USER','SYNTHETIC_PIN','SYNTHETIC_TEXT'):self.assertNotIn(secret,text)
    def test_response_only_records_public_counter_whitelist(self):
        observed=safe_received(json.dumps(dict(id=9,ok=True,result=dict(values={
            'Press/Access/CurrentLevel':4,'Press/HmiResponse/AckSequence':23,
            'Press/Access/CurrentUser':'SYNTHETIC_USER','Press/HmiRequest/Secret':'SYNTHETIC_PIN'}))),[])
        self.assertEqual(len(observed['publicCounters']),2)
        self.assertNotIn('SYNTHETIC',json.dumps(observed))
    def test_indexed_snapshot_counters_use_the_discovery_vector(self):
        paths=['Press/HmiResponse/AckSequence','Press/HmiRequest/Secret']
        observed=safe_received(json.dumps(dict(id=1,ok=True,result=dict(values={'0':23,'1':'SYNTHETIC_PIN'}))),paths)
        self.assertEqual(observed['publicCounters'],{'Press/HmiResponse/AckSequence':23})
        self.assertNotIn('SYNTHETIC',json.dumps(observed))
    def test_error_and_malformed_payloads_do_not_echo_values(self):
        for payload in ('SYNTHETIC_PIN',json.dumps(dict(id=1,ok=False,error='SYNTHETIC_PIN'))):
            self.assertNotIn('SYNTHETIC',json.dumps(safe_received(payload,[])))
    def test_urls_drop_userinfo_query_and_fragment(self):
        value=safe_url('ws://SYNTHETIC_USER:SYNTHETIC_PIN@127.0.0.1:8080/fraktal?token=SYNTHETIC_TOKEN#SYNTHETIC_FRAGMENT')
        self.assertEqual(value,dict(scheme='ws',host='127.0.0.1',port=8080,path='/fraktal'))
        self.assertNotIn('SYNTHETIC',json.dumps(value))
    def test_only_read_only_instrumentation_can_be_sent(self):
        self.assertTrue(allowed_cdp('Network.enable',{}))
        self.assertTrue(allowed_cdp('Runtime.evaluate',dict(expression=STORAGE_EXPRESSION,returnByValue=True)))
        for method,params in [('Input.dispatchMouseEvent',{}),('Page.navigate',{}),
            ('Runtime.evaluate',dict(expression='localStorage.clear()',returnByValue=True))]:
            self.assertFalse(allowed_cdp(method,params))
    def test_unexpected_endpoint_paths_are_not_logged(self):
        value=safe_url('ws://127.0.0.1:8080/SYNTHETIC_PIN')
        self.assertEqual(value['path'],'other')
        self.assertNotIn('SYNTHETIC',json.dumps(value))

if __name__=='__main__':unittest.main()
