"""Common store-response wire V1. No station, source-tree or controller access."""
VERSION=1
SERVICE_KIND=1
QUERY_KIND=2
INPUT='FRK_T_ConfigProviderRequestV1'
ACK='FRK_T_ConfigProviderAckV1'
WORK='FRK_T_ConfigProviderWorkV1'
MAX_SETS=4  # Wire V1 capacity; engineering verifies the matching Core limit.
TEXTS=tuple((f'{n}{i}',width) for i in range(MAX_SETS) for n,width in
    (('SetName',80),('RootIdentity',80),('ModelCode',64)))+(
    ('Document',480),('RejectScope',80),('RejectKey',160))
OFFSETS=tuple(sum(width for _,width in TEXTS[:i]) for i in range(len(TEXTS)))
BYTE_CAPACITY=sum(width for _,width in TEXTS)
CATALOG,DOCUMENT,REJECTION=1,2,4


def layout():
    return tuple((n,0) for n in ('SchemaVersion','Sequence','RequestSequence','LoginSequence','BuildRevision',
        'Operation','Flags','Count','DocumentLine','DocumentLines','Commit'))+tuple(
        (n,MAX_SETS) for n in ('SetSchema','ConfigRevision','RecordKind','RecordCount','CreatedSeconds','Synchronized'))+(
        ('TextLength',len(TEXTS)),('TextBytes',BYTE_CAPACITY))

def payload(*,sequence,request_sequence,login_sequence,build_revision,operation,headers=None,document=None,
            document_line=0,document_lines=0,reject_scope='',reject_key=''):
    """Encode the common provider contract; no station symbol/schema imports."""
    def integer(value,lo,hi):
        if type(value) is not int or not lo<=value<=hi:raise ValueError('provider integer outside contract')
        return value
    def word(value):
        integer(value,0,0xffffffff)
        return value if value<0x80000000 else value-0x100000000
    result={name:([0]*count if count else 0) for name,count in layout()}
    result.update(SchemaVersion=VERSION,Sequence=integer(sequence,1,2147483646),Commit=sequence,
        RequestSequence=word(request_sequence),LoginSequence=word(login_sequence),BuildRevision=integer(build_revision,1,0x7fffffff),
        Operation=integer(operation,0,0x7fffffff),Flags=REJECTION,DocumentLine=integer(document_line,-1,64),DocumentLines=integer(document_lines,0,64))
    def text(field,value):
        if not isinstance(value,str) or '\x00' in value:raise ValueError('provider text must be NUL-free Unicode')
        raw=value.encode('utf-8');width=TEXTS[field][1]
        if len(raw)>width:raise ValueError('provider text exceeds Core byte width')
        result['TextLength'][field]=len(raw);offset=OFFSETS[field]
        result['TextBytes'][offset:offset+len(raw)]=raw
    if headers is not None:
        if len(headers)>MAX_SETS:raise ValueError('provider catalog exceeds Core capacity')
        result['Flags']|=CATALOG;result['Count']=len(headers)
        for i,h in enumerate(headers):
            for j,key in enumerate(('set','root','model')):text(i*3+j,h[key])
            for target,key,lo,hi in (('SetSchema','schema',1,65535),('RecordKind','kind',0,2),
                    ('RecordCount','records',0,64),('Synchronized','clock',0,1)):
                result[target][i]=integer(h[key],lo,hi)
            result['ConfigRevision'][i]=word(h['configRev']);result['CreatedSeconds'][i]=word(h['created'])
    if document is not None:result['Flags']|=DOCUMENT;text(MAX_SETS*3,document)
    text(MAX_SETS*3+1,reject_scope);text(MAX_SETS*3+2,reject_key)
    return result
