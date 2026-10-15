"""Reference-simulator event sink: durable SQLite commit before root receipt.

Library entry points accept an existing transport and guard. The CLI is limited
to the qualified simulator; it neither logs in nor changes an application session.
"""
import argparse,hashlib,json,os,sqlite3,struct,time,uuid,zlib
from datetime import datetime,timezone
from pathlib import Path
from fraktal_tia_binding import Catalog
from fraktal_tia_event_delivery import POLICY
from tia_webapi import WebApi,leaf_var
from tia_mailbox import Mailbox
from tia_delivery_mailbox import ReceiptMailbox

POLICY_DATA=json.loads(POLICY.read_bytes())
EVENT_FIELDS=Catalog.read().resolve(['ST_AlarmEvent'])['ST_AlarmEvent']
APP_ID=0x46524B45

def event_crc(event):
    """Canonical Core-field encoding matches FRK_AlarmEventCrc, including UTF-16."""
    if set(event)!={f['member'] for f in EVENT_FIELDS}:raise ValueError('Incomplete event record')
    data=bytearray()
    for f in EVENT_FIELDS:
        value=event[f['member']];kind=f['native_type']
        if kind.startswith(('String[','WString[')):
            raw=value.encode('utf-16-le' if kind.startswith('WString') else 'latin-1')
            units=len(raw)//2 if kind.startswith('WString') else len(raw)
            data+=struct.pack('<I',units)+raw
        elif kind=='LDT':data+=struct.pack('<Q',int(value)&0xffffffffffffffff)
        elif kind in ('DInt','Time'):data+=struct.pack('<I',int(value)&0xffffffff)
        elif kind=='Bool':
            if type(value) is not bool:raise ValueError('Invalid event Boolean')
            data+=struct.pack('<I',int(value))
        else:raise ValueError('Unmapped Core event field '+kind)
    return zlib.crc32(data)

def entry_crc(sequence,event):
    return zlib.crc32(struct.pack('<I',sequence),event_crc(event)^0xffffffff)^0xffffffff

def validate_envelope(envelope):
    if set(envelope)!={'schema_version','token','scope','stream_id','epoch','checksum','event'} or type(envelope['schema_version']) is not int or envelope['schema_version']!=1:raise ValueError('Unsupported delivery envelope schema')
    if type(envelope['epoch']) is not int or type(envelope['checksum']) is not int or not 0<=envelope['checksum']<=0xffffffff:raise ValueError('Invalid delivery scalar')
    parts=envelope['token'].split('/')
    if len(parts)!=4:raise ValueError('Invalid delivery identity')
    stream,scope,epoch,sequence=parts
    if str(uuid.UUID(stream))!=stream or stream!=envelope['stream_id'] or scope!=envelope['scope']:
        raise ValueError('Delivery identity does not match its owner')
    epoch,sequence=int(epoch),int(sequence)
    if not 1<=epoch<=0xffffffff or not 1<=sequence<=0xffffffff:raise ValueError('Delivery identity exhausted')
    if parts[2:]!=[str(epoch),str(sequence)]:raise ValueError('Noncanonical delivery identity')
    if epoch!=envelope['epoch'] or entry_crc(sequence,envelope['event'])!=envelope['checksum']:
        raise ValueError('Delivery record checksum mismatch')
    return json.dumps(envelope,sort_keys=True,ensure_ascii=False,separators=(',',':'))

class SqliteEventStore:
    def __init__(self,path,timeout=2):
        self.path=Path(path)
        self.conn=sqlite3.connect(self.path,timeout=timeout,isolation_level=None)
        try:
            version=self.conn.execute('PRAGMA user_version').fetchone()[0]
            identity=self.conn.execute('PRAGMA application_id').fetchone()[0]
            tables=self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if not (version==0 and identity==0 and not tables) and (version!=1 or identity!=APP_ID or tables!=[('events',)]):raise ValueError('Unsupported event database identity/schema')
            assert self.conn.execute('PRAGMA journal_mode=DELETE').fetchone()[0]=='delete'
            self.conn.execute('PRAGMA synchronous=FULL')
            if version==0 and identity==0 and not tables:
                self.conn.execute('BEGIN IMMEDIATE')
                self.conn.execute('CREATE TABLE events (token TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL, received_utc TEXT NOT NULL)')
                self.conn.execute('PRAGMA application_id='+str(APP_ID))
                self.conn.execute('PRAGMA user_version=1');self.conn.execute('COMMIT')
            elif version!=1 or identity!=APP_ID or tables!=[('events',)]:
                raise ValueError('Unsupported event database identity/schema')
            columns=self.conn.execute('PRAGMA table_info(events)').fetchall()
            if [r[1] for r in columns]!=['token','payload','sha256','received_utc'] or columns[0][5]!=1:
                raise ValueError('Event database table shape changed')
        except BaseException:
            self.conn.close();raise
    def persist(self,envelope):
        payload=validate_envelope(envelope);digest=hashlib.sha256(payload.encode('utf-8')).hexdigest()
        try:
            self.conn.execute('BEGIN IMMEDIATE')
            old=self.conn.execute('SELECT payload,sha256 FROM events WHERE token=?',(envelope['token'],)).fetchone()
            if old is not None:
                if old!=(payload,digest):raise ValueError('Conflicting or damaged durable event identity')
            else:
                self.conn.execute('INSERT INTO events VALUES (?,?,?,?)',(envelope['token'],payload,digest,datetime.now(timezone.utc).isoformat()))
            self.conn.execute('COMMIT')
            return old is None
        except BaseException:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise
    def close(self):self.conn.close()

class EventCollector:
    def __init__(self,api,store,guard,emit=lambda row:None):
        self.api,self.store,self.emit=api,store,emit
        self.box=Mailbox(api,guard,emit)
        self.receipts=ReceiptMailbox(api,guard,emit)
    def head(self,slot):
        count=int(self.box.read('FRK_EventDeliveryView.Count'))
        if not 1<=slot<=count:raise ValueError('Delivery slot outside deployment')
        base='FRK_EventDeliveryView.Rows['+str(slot)+']'
        if self.box.read(base+'.RestoreLost'):raise RuntimeError('PLC delivery image rejected; engineering discard required')
        before=self.box.read(base+'.Token')
        if not before:return None
        paths=[base+'.'+n for n in ('Scope','StreamId','Epoch','Checksum')]
        paths += [base+'.Ev.'+f['member'] for f in EVENT_FIELDS]
        replies=self.api.bulk([('PlcProgram.Read',{'var':leaf_var(p.split('.'))}) for p in paths])
        if any(error for value,error in replies):raise RuntimeError('Delivery snapshot read refused')
        values=[v for v,error in replies]
        after=self.box.read(base+'.Token')
        if before!=after:raise RuntimeError('Delivery head changed during snapshot')
        envelope=dict(schema_version=1,token=before,scope=values[0],stream_id=values[1],epoch=int(values[2]),checksum=int(values[3]),event={f['member']:v for f,v in zip(EVENT_FIELDS,values[4:])})
        validate_envelope(envelope)
        return envelope
    def acknowledge(self,envelope):
        return self.receipts.request(POLICY_DATA['request_kinds']['ACK_EVENT_DELIVERY'],envelope['scope'].split('.')[0],TargetPath=envelope['scope'],NameValue=envelope['token'],DurationMs=envelope['checksum'])
    def deliver_once(self,slot):
        envelope=self.head(slot)
        if envelope is None:return None
        fresh=self.store.persist(envelope)
        self.emit(dict(event='durable-event',token=envelope['token'],new=fresh))
        # A timeout is returned to the caller. Reconnection starts a new read;
        # it never replays the previous request/commit sequence.
        accepted=self.acknowledge(envelope)
        self.emit(dict(event='delivery-receipt',token=envelope['token'],accepted=accepted))
        return dict(token=envelope['token'],new=fresh,accepted=accepted)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--confirm-simulator',choices=['Fraktal'],required=True)
    parser.add_argument('--slot',type=int,required=True)
    args=parser.parse_args()
    from tia_target_guard import guard
    os.environ['FRAKTAL_TIA_SIM_INSTANCE']=args.confirm_simulator
    guard()
    api=WebApi('169.254.212.49',Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin',False)
    store=SqliteEventStore(args.database)
    try:
        api.login('fraktal')
        collector=EventCollector(api,store,guard,lambda r:print(json.dumps(r)))
        result=collector.deliver_once(args.slot)
        return 0 if result is None or result['accepted'] else 2
    finally:store.close();api.conn.close()

if __name__=='__main__':raise SystemExit(main())
