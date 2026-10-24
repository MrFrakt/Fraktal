"""Generic read-only canonical CIP capture. No station/declaration imports."""
import argparse
import gzip
import json
from pathlib import Path
import re

from fraktal_ab_canonical_reader import read_document


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--slot',type=int,default=0)
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--capture-output',type=Path,required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Fa-f0-9]{8}',args.expect_serial) or not 0 <= args.slot <= 255:
        parser.error('exact eight-hex serial and valid slot required')
    if args.output.resolve()==args.capture_output.resolve() or any(p.exists() for p in (args.output,args.capture_output)):
        parser.error('two distinct new output paths required')
    from pylogix import PLC
    with PLC(args.host) as comm:
        comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=args.slot,4000,10
        document,capture=read_document(comm,expect_serial=args.expect_serial)
    for path,value in ((args.output,document),(args.capture_output,capture)):
        opener=gzip.open if path.suffix=='.gz' else open
        with opener(path,'xt',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2,allow_nan=False)
            stream.write('\n')
    print(json.dumps(dict(values=document['nodeCount'],modules=document['moduleCount'],readOnly=True)))
    return 0


if __name__=='__main__':raise SystemExit(main())
