import struct,sys
def sections(fn):
    d=open(fn,'rb').read()
    shoff=struct.unpack_from('<I',d,0x20)[0];n=struct.unpack_from('<H',d,0x30)[0];si=struct.unpack_from('<H',d,0x32)[0]
    sh=[struct.unpack_from('<10I',d,shoff+i*40) for i in range(n)]
    names=d[sh[si][4]:sh[si][4]+sh[si][5]];out={}
    for s in sh:
        nm=names[s[0]:names.index(b'\0',s[0])].decode()
        if s[3]: out[nm]=(s[3],d[s[4]:s[4]+s[5]] if s[1]!=8 else b'')
    return out
def symbols(fn):
    d=open(fn,'rb').read()
    shoff=struct.unpack_from('<I',d,0x20)[0];n=struct.unpack_from('<H',d,0x30)[0]
    sh=[struct.unpack_from('<10I',d,shoff+i*40) for i in range(n)];res={}
    for s in sh:
        if s[1]==2:
            st=sh[s[6]]
            for i in range(s[5]//16):
                nm,val,sz,inf,oth,shn=struct.unpack_from('<IIIBBH',d,s[4]+i*16)
                name=d[st[4]+nm:d.index(b'\0',st[4]+nm)].decode()
                if name: res[name]=val
    return res
if __name__=='__main__':
    for k,(a,b) in sections(sys.argv[1]).items(): print(k,hex(a),hex(len(b)))
    print({k:hex(v) for k,v in symbols(sys.argv[1]).items() if not k.startswith('.')})
