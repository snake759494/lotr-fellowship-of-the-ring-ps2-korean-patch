"""반지의 제왕: 반지 원정대 (SLUS-20520) 한글 패치 빌드

1. 번역(translation/ui_ko.tsv, sub_ko.tsv) -> 사용 음절 집합 -> 2바이트 코드(B0-C8, A1-FE)
2. 한글 글리프 페이지(256x64, 8bpp) 생성: 세리프(폰트 0, 메뉴 음절) / 산세리프(폰트 1, 전체)
3. ELF: 글리프 데이터와 한글 지원 문자열 그리기/너비 코드를 .bss 뒤에 붙이고 힙 시작을 뒤로 민다
4. XDU(UI) / SDU(자막) 문자열을 원래 크기·오프셋 그대로 교체(엔진은 크기가 바뀌면 적재 실패)
5. 원본 ISO 복사 후 변경 파일 기록(ISO9660 + UDF)
"""
import os, sys, struct, shutil, subprocess, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from srsc import parse
from texts import *
import kfont_gen

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
ISO_IN = "Lord of the Rings, The - The Fellowship of the Ring (USA).iso"
ISO_OUT = "Lord_of_the_Rings_Fellowship_of_the_Ring_KO.iso"
OUT = 'work/out'
KFONT_DIR = 'tools/kfont'
warn = []


# ---------------------------------------------------------------- 번역 로드
def load_tsv(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        k, _, v = line.partition('\t')
        out[k] = unesc(v)
    return out


ui_en = [l.rstrip('\n').split('\t') for l in open('translation/ui_en.tsv', encoding='utf-8')]
sub_en = [l.rstrip('\n').split('\t', 1) for l in open('translation/sub_en.tsv', encoding='utf-8')]
ui_ko = load_tsv('translation/ui_ko.tsv')
sub_ko = load_tsv('translation/sub_ko.tsv')

ui_map = {}          # (rel, id) -> ko
for i, (r, eid, en) in enumerate(ui_en):
    ko = ui_ko.get(str(i))
    if ko is not None and ko != '':
        ui_map[(r, int(eid))] = ko
sub_map = {}         # en text -> ko
for k, en in sub_en:
    ko = sub_ko.get(k)
    if ko:
        sub_map[unesc(en)] = ko

# ---------------------------------------------------------------- 문자 집합
chars = set()
for s in list(ui_map.values()) + list(sub_map.values()):
    for c in s:
        if 0xAC00 <= ord(c) <= 0xD7A3:
            chars.add(c)
        elif ord(c) >= 0x80:
            try:
                c.encode('cp1252')
            except UnicodeEncodeError:
                warn.append(f'인코딩 불가 문자 {c!r} U+{ord(c):04X}')
chars = sorted(chars)
assert len(chars) <= 25 * 94, len(chars)
cmap = {c: bytes([0xB0 + k // 94, 0xA1 + k % 94]) for k, c in enumerate(chars)}


def enc(s):
    out = bytearray()
    for c in s:
        if c in cmap:
            out += cmap[c]
        else:
            b = c.encode('cp1252', errors='replace')
            if 0xB0 <= b[0] <= 0xC8:
                warn.append(f'선행바이트 충돌 문자 {c!r}')
            out += b
    return bytes(out)


def pack_str(b):
    n = len(b) + 1
    while (2 + n) % 4:
        n += 1
    return struct.pack('<H', n) + b + b'\0' * (n - len(b))


changed = {}   # iso path -> bytes

# ---------------------------------------------------------------- 글리프 페이지(ELF 내장)
ksets = []; allpix = bytearray()
os.makedirs(OUT, exist_ok=True)
# 세리프(폰트 0)는 주로 메뉴·제목에 쓰이므로 40자 이하 UI 문자열의 음절만 담고,
# 나머지는 실행 중 산세리프 글리프를 확대해 대신 그린다(메모리 절약).
serif_chars = sorted({c for v in ui_map.values() if len(v) <= 40 for c in v if c in cmap})
kmap = [0xFFFF] * len(chars)
for i, c in enumerate(serif_chars):
    kmap[chars.index(c)] = i
for si, cfg in enumerate(kfont_gen.SETS):
    subset = serif_chars if si == 0 else chars
    pages, ks, size = kfont_gen.render_set(cfg, subset or ['가'])
    kfont_gen.preview(pages, f'{OUT}/kfont_{cfg["name"]}.png')
    for p in pages:
        allpix += p[::-1].tobytes()          # 원본 폰트처럼 상하 반전 저장
    ksets.append(ks)
    print(f'글꼴 {cfg["name"]}: {cfg["ttf"]} {size}px, 글자 {len(subset)}, 페이지 {len(pages)}, 셀 {cfg["cw"]}x{cfg["ch"]}')
kmap_bin = struct.pack('<%dH' % (len(kmap) + 1), *(kmap + [0xFFFF]))
open(f'{KFONT_DIR}/kmap.bin', 'wb').write(kmap_bin)
open(f'{KFONT_DIR}/kpix.bin', 'wb').write(allpix)
open(f'{KFONT_DIR}/kpal.bin', 'wb').write(kfont_gen.palette().tobytes())

# ---------------------------------------------------------------- UI 문자열(XDU)
# 엔진은 리소스 파일의 크기·오프셋이 바뀌면 문자열 적재에 실패하므로,
# 각 항목을 원래 크기 그대로 두고 그 안에 한글을 넣는다(언어 슬롯 5개 중 들어가는 만큼).
EMPTY = struct.pack('<H', 2) + b'\0\0'
nui = 0; nslot = [0] * 6
for f in xdu_files():
    d = bytearray(open(f, 'rb').read()); _, _, es = parse(bytes(d)); r = rel(f); hit = False
    for e in es:
        if e['a'] != 0 or (r, e['id']) not in ui_map:
            continue
        strs = xdu_strings(d, e)
        S = e['size']
        pk = pack_str(enc(ui_map[(r, e['id'])]))
        tail = [struct.pack('<H', len(x)) + x for x in strs[5:]]
        for c in range(5, 0, -1):
            body = pk * c + EMPTY * (5 - c) + b''.join(tail[:-1])
            last = strs[-1]
            room = S - len(body) - 2
            if room >= len(last):
                body += struct.pack('<H', room) + last + b'\0' * (room - len(last))
                break
        else:
            warn.append(f'UI 공간 부족: {r} #{e["id"]} {ui_map[(r, e["id"])][:20]}')
            continue
        assert len(body) == S
        d[e['off']:e['off'] + S] = body; nui += 1; nslot[c] += 1; hit = True
    if hit:
        changed['/' + r] = bytes(d)

# ---------------------------------------------------------------- 자막(SDU)
# 자막도 원래 길이 필드(L) 그대로, 남는 바이트는 0 으로 채운다.
nsub = 0; maxlen = 0
for f in sdu_files():
    d = bytearray(open(f, 'rb').read()); _, _, es = parse(bytes(d)); r = rel(f); hit = False
    for e in es:
        if (e['a'], e['t']) != (2, 3):
            continue
        s = sub_entry(d, e)
        if not s:
            continue
        ko = sub_map.get(dec(s))
        if ko is None:
            continue
        L = struct.unpack_from('<H', d, e['off'] + 0x30)[0]
        kb = enc(ko)
        if len(kb) > L:
            warn.append(f'자막 길이 초과: {r} #{e["id"]} {len(kb)}>{L} {ko[:20]}')
            continue
        maxlen = max(maxlen, len(kb))
        p = e['off'] + 0x32
        d[p:p + L] = kb + b'\0' * (L - len(kb)); nsub += 1; hit = True
    if hit:
        changed['/' + r] = bytes(d)
print('UI 슬롯 수 분포', nslot)
print(f'UI {nui}/{len(ui_en)}, 자막 엔트리 {nsub}, 자막 최대 {maxlen}바이트, 음절 {len(chars)}')

# ---------------------------------------------------------------- 코드
with open(f'{KFONT_DIR}/kset.h', 'w') as w:
    w.write('const KSet kset[2] = { ' + ', '.join('{%d,%d,%d,%d,%d,%d,%d,0}' % k for k in ksets) + ' };\n')
cc = [sys.executable, '-m', 'ziglang', 'cc', '-target', 'mipsel-freestanding', '-march=mips2', '-mabi=32',
      '-mno-abicalls', '-fno-pic', '-G0', '-nostdlib', '-Os', '-fno-asynchronous-unwind-tables',
      '-fno-unwind-tables', '-Wl,--build-id=none', '-Wl,-T,link.ld', '-Wl,-e,e_draw',
      '-DKDATA_HASH=0x' + hashlib.sha1(bytes(allpix) + kfont_gen.palette().tobytes() + kmap_bin).hexdigest()[:12],
      'kwalk.c', 'kset.c', 'shim.S', '-o', 'k.elf']
subprocess.run(cc, cwd=KFONT_DIR, check=True, capture_output=True)
from elfsec import sections
kaddr, kcode = sections(f'{KFONT_DIR}/k.elf')['.k']
assert kaddr == 0x466180
heap = (kaddr + len(kcode) + 0xff) & ~0xff        # 새 힙 시작(_end)

elf = bytearray(open('work/orig/SLUS_205.20', 'rb').read())
phoff = struct.unpack_from('<I', elf, 0x1c)[0]
p_type, p_off, p_va, p_pa, p_fs, p_ms, p_fl, p_al = struct.unpack_from('<8I', elf, phoff)
assert (p_off, p_va, p_fs, p_ms) == (0x1000, 0x100000, 0x300238, 0x36615c)
seg = bytearray(elf[p_off:p_off + p_fs])


def put32(va, v):
    struct.pack_into('<I', seg, va - p_va, v)


def get32(va):
    return struct.unpack_from('<I', seg, va - p_va)[0]


# 힙 시작(_end) 0x46615c -> heap (lui/addiu 쌍과 sbrk 포인터)
hi, lo = (heap + 0x8000) >> 16, heap & 0xffff
for lui_va, add_va in ((0x10006c, 0x100074), (0x35ddfc, 0x35de08)):
    wl, wa = get32(lui_va), get32(add_va)
    assert wl >> 16 == 0x3c00 | ((wl >> 16) & 0x1f) and wl & 0xffff == 0x46 and wa & 0xffff == 0x615c, (hex(wl), hex(wa))
    put32(lui_va, (wl & 0xffff0000) | hi); put32(add_va, (wa & 0xffff0000) | lo)
assert get32(0x3b6a44) == 0x46615c        # sbrk 시작 포인터
put32(0x3b6a44, heap)
print(f'코드/글리프 {len(kcode)} 바이트, 힙 시작 0x{heap:x}')
# 원래 함수 -> 새 코드 점프
assert get32(0x23f1c0) == 0x2403003c and get32(0x23f638) == 0x00a0482d
put32(0x23f1c0, 0x08000000 | (0x466180 >> 2)); put32(0x23f1c4, 0)
put32(0x23f638, 0x08000000 | (0x466188 >> 2)); put32(0x23f63c, 0)
seg += b'\0' * (kaddr - p_va - len(seg)) + kcode
new = bytearray(elf[:p_off]) + seg
struct.pack_into('<8I', new, phoff, p_type, p_off, p_va, p_pa, len(seg), len(seg), p_fl, p_al)
struct.pack_into('<I', new, 0x20, 0)       # 섹션 헤더 제거
struct.pack_into('<HHH', new, 0x2e, 0, 0, 0)
changed['/SLUS_205.20'] = bytes(new)


# ---------------------------------------------------------------- ISO
def iso_records(f):
    """경로 -> (레코드 오프셋, 시작 LBA, 크기)"""
    f.seek(16 * 2048); pvd = f.read(2048)
    assert pvd[1:6] == b'CD001'
    res = {}

    def walk(lba, size, path):
        f.seek(lba * 2048); data = f.read(size); p = 0
        while p < size:
            n = data[p]
            if n == 0:
                p = (p // 2048 + 1) * 2048; continue
            ext = struct.unpack_from('<I', data, p + 2)[0]; ln = struct.unpack_from('<I', data, p + 10)[0]
            fl = data[p + 25]; nl = data[p + 32]; name = data[p + 33:p + 33 + nl]
            if name not in (b'\0', b'\1'):
                nm = name.decode().split(';')[0]
                if fl & 2:
                    walk(ext, ln, path + '/' + nm)
                else:
                    res[path + '/' + nm] = (lba * 2048 + p, ext, ln)
            p += n
    root = pvd[156:156 + 34]
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return res, struct.unpack_from('<I', pvd, 80)[0]


def both32(v):
    return struct.pack('<I', v) + struct.pack('>I', v)


print('ISO 복사...')
tmp = ISO_OUT + '.tmp'
shutil.copyfile(ISO_IN, tmp)
from udf import UDF
with open(tmp, 'r+b') as f:
    recs, vol = iso_records(f)
    udf = UDF(f)
    end = vol
    for path, data in sorted(changed.items()):
        roff, lba, ln = recs[path]
        cap = (ln + 2047) // 2048 * 2048
        if len(data) <= cap:
            f.seek(lba * 2048); f.write(data + b'\0' * (cap - len(data)))
            newlba = lba
        else:
            newlba = end
            f.seek(newlba * 2048); f.write(data + b'\0' * ((-len(data)) % 2048))
            end += (len(data) + 2047) // 2048
        f.seek(roff + 2); f.write(both32(newlba)); f.write(both32(len(data)))
        udf.set_file(path, newlba, len(data))
    end += 1                                   # 마지막 섹터: UDF 보조 앵커
    f.seek(16 * 2048 + 80); f.write(both32(end))
    f.truncate(end * 2048)
    udf.grow(end)
os.replace(tmp, ISO_OUT)
print(f'완료: {ISO_OUT} ({end} 섹터), 변경 파일 {len(changed)}')
json.dump({'chars': ''.join(chars), 'ksets': ksets,
           'changed': sorted(changed)}, open(f'{OUT}/build_info.json', 'w', encoding='utf-8'), ensure_ascii=False)
for w_ in sorted(set(warn)):
    print('경고:', w_)
