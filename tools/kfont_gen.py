"""한글 글리프 페이지(8bpp 256x256 텍스처) 생성

글리프 k(0부터) -> 코드 바이트 (0xB0 + k//94, 0xA1 + k%94)
페이지(256xPH) 논리 좌표: 0행은 비우고 셀은 y=1부터.
텍스처는 아래에서 위로 저장(원본 폰트와 동일하게 상하 반전).
"""
import struct, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 폰트 슬롯 0: 세리프(INTERFCE 194, 페이지 245/246, 행 높이 29, 기준선 23)
# 폰트 슬롯 1: 산세리프(INTERFCE 195, 페이지 212, 행 높이 23, 기준선 18)
SETS = [
    dict(name='serif', ttf='SeoulHangangEB.ttf', cw=22, ch=23, adv=21, dy=2, top=1, bot=22, size=None),
    dict(name='sans', ttf='NanumSquareNeo-cBd.ttf', cw=16, ch=17, adv=16, dy=3, top=1, bot=16, size=None),
]
LEVELS = 24
PH = 64                         # 페이지 높이(VRAM 부담을 줄이려 256x64)


def level_index(L):
    if L < 8:
        return 32 + L
    if L < 16:
        return 40 + (L - 8)
    return 56 + (L - 16)


def palette():
    pal = np.zeros((256, 4), np.uint8)
    pal[:] = (255, 255, 255, 0)
    for L in range(LEVELS):
        a = round(L * 128 / (LEVELS - 1))     # 메모리 형식(0..0x80)
        pal[level_index(L)] = (255, 255, 255, a)
    pal[48:56] = pal[40:48]       # CLUT 스위즐(8-15 <-> 16-23) 무관하게 동일
    return pal


def fit_font(path, top, bot):
    """'한'·'뷁' 등의 잉크 높이가 bot-top 이 되도록 크기 결정"""
    want = bot - top
    best = None
    for sz in range(8, 40):
        f = ImageFont.truetype(path, sz)
        h = 0
        for ch in '한글뷁읽':
            b = f.getbbox(ch)
            h = max(h, b[3] - b[1])
        if h <= want:
            best = sz
    return best


def render_set(cfg, chars):
    path = os.path.join(ROOTDIR, cfg['ttf'])
    size = cfg['size'] or fit_font(path, cfg['top'], cfg['bot'])
    f = ImageFont.truetype(path, size)
    # 기준 세로 위치: 대표 글자 잉크 영역의 위쪽을 top 에 맞춤
    ys = [f.getbbox(c) for c in '한글뷁읽']
    ink_top = min(b[1] for b in ys); ink_bot = max(b[3] for b in ys)
    oy = cfg['top'] + ((cfg['bot'] - cfg['top']) - (ink_bot - ink_top)) // 2 - ink_top
    cw, ch = cfg['cw'], cfg['ch']
    cols = 256 // cw
    rows = (PH - 1) // ch
    per = cols * rows
    npages = (len(chars) + per - 1) // per
    pages = [np.full((PH, 256), level_index(0), np.uint8) for _ in range(npages)]
    glyphs = []
    for k, c in enumerate(chars):
        img = Image.new('L', (cw * 4, ch * 4), 0)
        dr = ImageDraw.Draw(img)
        b = f.getbbox(c)
        gw = b[2] - b[0]
        ox = (cfg['adv'] - gw) // 2 - b[0]
        dr.text((ox, oy), c, font=f, fill=255)
        a = np.array(img)[:ch, :cw].astype(np.float32) / 255.0
        lv = np.clip(np.round(a * (LEVELS - 1)), 0, LEVELS - 1).astype(int)
        pg, i = divmod(k, per)
        x0 = (i % cols) * cw; y0 = 1 + (i // cols) * ch
        lut = np.array([level_index(L) for L in range(LEVELS)], np.uint8)
        pages[pg][y0:y0 + ch, x0:x0 + cw] = lut[lv]
        glyphs.append(a)
    ks = (npages, per, cols, cw, ch, cfg['adv'], cfg['dy'])
    return pages, ks, size


def preview(pages, path):
    pal = palette()
    ims = []
    for p in pages[:2]:
        a = pal[p][..., 3].astype(np.uint8) * 2
        ims.append(Image.fromarray(255 - a))
    w = sum(i.width for i in ims)
    out = Image.new('L', (w, 256), 255)
    x = 0
    for i in ims:
        out.paste(i, (x, 0)); x += i.width
    out.save(path)
