"""XDU(UI)와 SDU(자막) 텍스트 추출/공용 함수"""
import struct, glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from srsc import parse

ROOT = 'work/orig'
BS = chr(92)


def xdu_files():
    return sorted(glob.glob(ROOT + '/ENGLISH/**/*.XDU', recursive=True))


def sdu_files():
    return sorted(glob.glob(ROOT + '/ENGLISH/**/*.SDU', recursive=True))


def rel(f):
    return os.path.relpath(f, ROOT).replace(BS, '/')


def xdu_strings(d, e):
    p = e['off']; end = p + e['size']; out = []
    while p < end:
        l = struct.unpack_from('<H', d, p)[0]
        out.append(d[p + 2:p + 2 + l]); p += 2 + l
    return out


def cstr(b):
    return b.split(b'\0')[0]


def sub_entry(d, e):
    b = d[e['off']:e['off'] + e['size']]
    if struct.unpack_from('<I', b, 0)[0] & 0x2000:
        L = struct.unpack_from('<H', b, 0x30)[0]
        return cstr(b[0x32:0x32 + L])
    return None


def dec(b):
    return b.decode('cp1252', errors='replace')


_E = {BS: BS + BS, '\t': BS + 't', '\n': BS + 'n', '\r': BS + 'r'}
_U = {BS: BS, 't': '\t', 'n': '\n', 'r': '\r'}


def esc(s):
    return ''.join(_E.get(c, c) for c in s)


def unesc(s):
    out = []; i = 0
    while i < len(s):
        if s[i] == BS and i + 1 < len(s):
            c = s[i + 1]
            out.append(_U.get(c, BS + c)); i += 2
        else:
            out.append(s[i]); i += 1
    return ''.join(out)
