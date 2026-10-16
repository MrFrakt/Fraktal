"""Read the platform conversion witness without exposing framework scratch data."""
import json
import math
import os
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'tools'))
from tia_target_guard import guard
from tia_webapi import WebApi, leaf_var


def collect(out):
    api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
    base = 'GDB_ConfigNumericTest'
    def read(member): return api.call('PlcProgram.Read', {'var': leaf_var([base, member])})
    def write(member, value):
        guard()
        api.call('PlcProgram.Write', {'var': leaf_var([base, member]), 'value': value})
    result = []
    partial = out.with_suffix('.partial.jsonl').open('x', encoding='ascii', newline='\n')
    try:
        api.login('fraktal')
        cases = ['1.2345678901234567', '-999999.9999999999', '1.0000000000000002e-100',
                     '0.10000000149011612', '1.1754943508222875e-38',
                     '1.7976931348623157e308', '2.2250738585072014e-308', '4.9406564584124654e-324',
                     '1.00000000000000011102230246251565404236316680908203125',
                     '1.00000000000000011102230246251565404236316680908203126',
                     '0.999999999999999944488848768742172978818416595458984375']
        random_values = random.Random(1500)
        for exponent in (-1022, -1000, -500, -100, -1, 0, 1, 100, 500, 1000, 1023):
            value = math.ldexp(1+random_values.getrandbits(52)/2**52, exponent)
            cases += [repr(value), repr(-value)]
        for text in cases:
            write('InputText', text); write('Requested', True)
            deadline = time.monotonic()+8
            while read('Requested') and time.monotonic() < deadline: time.sleep(.05)
            assert not read('Requested'), 'numeric witness did not complete'
            row = dict(input=text, input_value=read('InputValue'), input_valid=read('InputValid'),
                       formatted_text=read('FormattedText'), output_text=read('OutputText'), output_value=read('OutputValue'), output_valid=read('OutputValid'),
                       status=guard(), conversions=[dict(text=read('Texts[%d]'%i), value=read('Values[%d]'%i),
                                                        valid=read('Valid[%d]'%i)) for i in range(1,7)])
            result.append(row)
            partial.write(json.dumps(row)+'\n'); partial.flush()
            print(json.dumps(row), flush=True)
            expected = float(text)
            # Preserve the measured native subnormal admission as a separate
            # observation; every normal IEEE value must pass exactly.
            if abs(expected) >= sys.float_info.min or row['input_valid']:
                assert row['input_valid'] and row['input_value'] == expected, 'decimal rounding '+text
                assert row['output_valid'] and row['output_value'] == expected, 'PLC round trip '+text
                assert float(row['output_text']) == expected, 'independent decimal round trip '+text
        out.write_bytes((json.dumps(result, indent=2)+'\n').encode('ascii'))
    finally:
        partial.close()
        api.conn.close()


if __name__ == '__main__': collect(Path(sys.argv[1]))
