"""Session-only tracing of the unchanged legacy Part reader.

Retain only schema/revision words and timing, never Part identity/payload bytes.
The original reader owns requests, attempts, projection and acceptance.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import struct
import sys
import time


class _TraceRead:
    def __init__(self, comm, expected_tag, rows, clock):
        self.comm,self.expected_tag,self.rows,self.clock=comm,expected_tag,rows,clock

    def __getattr__(self,name):
        return getattr(self.comm,name)

    def Read(self,*args,**kwargs):
        ordinal=len(self.rows)
        row=dict(ordinal=ordinal,phase=('before','body','after')[ordinal%3],
                 attempt=ordinal//3+1,startUs=self.clock())
        try:
            reply=self.comm.Read(*args,**kwargs)
            try:
                from fraktal_ab_press_execute import _success,_value
                row['success']=bool(_success(reply))
                row['tagMatched']=bool(args and args[0]==self.expected_tag)
                raw=_value(reply)
                if row['success'] and row['tagMatched'] and isinstance(raw,(bytes,bytearray)) and len(raw)>=8:
                    row['schemaVersion'],row['dataRevision']=struct.unpack_from('<2i',raw)
            except Exception as error:
                row['diagnosticErrorType']=type(error).__name__
            return reply
        except BaseException as error:
            row['readErrorType']=type(error).__name__
            raise
        finally:
            row['elapsedUs']=self.clock()-row['startUs']
            self.rows.append(row)


@contextmanager
def trace_part_reads(path,*,clock=None):
    import fraktal_ab_part as part
    clock=clock or (lambda:time.perf_counter_ns()//1000)
    original=part.read
    with Path(path).open('x',encoding='utf-8',newline='') as output:
        sequence=0

        def traced(comm,app,attempts=3):
            nonlocal sequence
            sequence+=1
            rows=[]
            started=clock()
            error=None
            try:
                return original(_TraceRead(comm,part.tag(app),rows,clock),app,attempts=attempts)
            except BaseException as caught:
                error=caught
                raise
            finally:
                record=dict(call=sequence,attemptBudget=attempts,readCount=len(rows),
                            elapsedUs=clock()-started,passed=error is None,
                            errorType=type(error).__name__ if error else None,reads=rows)
                try:
                    output.write(json.dumps(record,separators=(',',':'))+'\n')
                    output.flush()
                except Exception:
                    if error is None:
                        raise
                    # Preserve the original refusal even if diagnostic I/O fails.
                    print('Part read diagnostic write failed; original refusal retained.',file=sys.stderr)

        part.read=traced
        try:
            yield
        finally:
            part.read=original
