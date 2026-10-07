import struct
def parse(d):
    assert d[:4]==b'SRSC'
    diroff=struct.unpack_from('<I',d,6)[0]
    hdr=d[10:16]
    n=(len(d)-diroff)//14
    ents=[]
    for i in range(n):
        a,t,i1,i2,off,sz=struct.unpack_from('<BBHHII',d,diroff+i*14)
        ents.append(dict(a=a,t=t,id=i1,x=i2,off=off,size=sz))
    return diroff,hdr,ents
if __name__=='__main__':
    import sys,collections
    for fn in sys.argv[1:]:
        d=open(fn,'rb').read()
        diroff,hdr,ents=parse(d)
        c=collections.Counter((e['a'],e['t'],e['x']) for e in ents)
        print(fn,len(d),hex(diroff),(len(d)-diroff)%14,hdr.hex(),dict(c))
