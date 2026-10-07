"""PS2 IPU 인트라 프레임 인코더(이 게임 VDU 동영상용)

프레임 = 플래그 1바이트 + 매크로블록 열(슬라이스 없음) + 바이트 정렬 + 00 00 01 B0.
플래그: bit0-1 intra_dc_precision, 0x10 alternate_scan, 0x20 intra_vlc_format, 0x40 q_scale_type, 0x04 dct_type 있음.
여기서는 flags=0x02(DC 정밀도 10비트, 지그재그, 표 B-14, 선형 qscale, 프레임 DCT)로 인코딩한다.
VLC 표는 MPEG-1/2 표준(FFmpeg mpeg12data.c 와 같은 값).
"""
import numpy as np

INTRA_W = np.array([
    8, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37,
    19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34, 37, 40,
    22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58,
    26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83], np.float64).reshape(8, 8)
ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14,
          21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60,
          61, 54, 47, 55, 62, 63]
DC_LUM = [(0x4, 3), (0x0, 2), (0x1, 2), (0x5, 3), (0x6, 3), (0xe, 4), (0x1e, 5), (0x3e, 6), (0x7e, 7), (0xfe, 8), (0x1fe, 9), (0x1ff, 9)]
DC_CHR = [(0x0, 2), (0x1, 2), (0x2, 2), (0x6, 3), (0xe, 4), (0x1e, 5), (0x3e, 6), (0x7e, 7), (0xfe, 8), (0x1fe, 9), (0x3fe, 10), (0x3ff, 10)]
_B14 = [(0x3, 2), (0x4, 4), (0x5, 5), (0x6, 7), (0x26, 8), (0x21, 8), (0xa, 10), (0x1d, 12), (0x18, 12), (0x13, 12), (0x10, 12),
        (0x1a, 13), (0x19, 13), (0x18, 13), (0x17, 13), (0x1f, 14), (0x1e, 14), (0x1d, 14), (0x1c, 14), (0x1b, 14), (0x1a, 14),
        (0x19, 14), (0x18, 14), (0x17, 14), (0x16, 14), (0x15, 14), (0x14, 14), (0x13, 14), (0x12, 14), (0x11, 14), (0x10, 14),
        (0x18, 15), (0x17, 15), (0x16, 15), (0x15, 15), (0x14, 15), (0x13, 15), (0x12, 15), (0x11, 15), (0x10, 15), (0x3, 3),
        (0x6, 6), (0x25, 8), (0xc, 10), (0x1b, 12), (0x16, 13), (0x15, 13), (0x1f, 15), (0x1e, 15), (0x1d, 15), (0x1c, 15),
        (0x1b, 15), (0x1a, 15), (0x19, 15), (0x13, 16), (0x12, 16), (0x11, 16), (0x10, 16), (0x5, 4), (0x4, 7), (0xb, 10),
        (0x14, 12), (0x14, 13), (0x7, 5), (0x24, 8), (0x1c, 12), (0x13, 13), (0x6, 5), (0xf, 10), (0x12, 12), (0x7, 6),
        (0x9, 10), (0x12, 13), (0x5, 6), (0x1e, 12), (0x14, 16), (0x4, 6), (0x15, 12), (0x7, 7), (0x11, 12), (0x5, 7),
        (0x11, 13), (0x27, 8), (0x10, 13), (0x23, 8), (0x1a, 16), (0x22, 8), (0x19, 16), (0x20, 8), (0x18, 16), (0xe, 10),
        (0x17, 16), (0xd, 10), (0x16, 16), (0x8, 10), (0x15, 16), (0x1f, 12), (0x1a, 12), (0x19, 12), (0x17, 12), (0x16, 12),
        (0x1f, 13), (0x1e, 13), (0x1d, 13), (0x1c, 13), (0x1b, 13), (0x1f, 16), (0x1e, 16), (0x1d, 16), (0x1c, 16), (0x1b, 16)]
_LEVEL = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 1, 2, 3, 4, 5, 1, 2, 3, 4, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
_RUN = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
assert len(_B14) == len(_LEVEL) == len(_RUN) == 111
RL = {(r, l): c for r, l, c in zip(_RUN, _LEVEL, _B14)}
EOB = (0x2, 2)
ESC = (0x1, 6)
FLAGS = 0x02

_n = np.arange(8)
_D = np.sqrt(2 / 8) * np.cos((2 * _n[None, :] + 1) * _n[:, None] * np.pi / 16)
_D[0] /= np.sqrt(2)


class Bits:
    def __init__(self):
        self.acc = 0; self.n = 0; self.out = bytearray()

    def put(self, v, n):
        self.acc = (self.acc << n) | (v & ((1 << n) - 1)); self.n += n
        while self.n >= 8:
            self.n -= 8; self.out.append((self.acc >> self.n) & 0xff)
        self.acc &= (1 << self.n) - 1

    def align(self):
        if self.n:
            self.put(0, 8 - self.n)


def _blocks(plane):
    h, w = plane.shape
    b = plane.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).astype(np.float64)
    return np.einsum('ij,abjk,lk->abil', _D, b, _D)          # 행렬 DCT


def _dc_put(bw, diff, tab):
    a = abs(diff); size = a.bit_length()
    code, n = tab[size]; bw.put(code, n)
    if size:
        bw.put(diff if diff > 0 else diff + (1 << size) - 1, size)


def encode(y, u, v, qcode):
    """y: HxW, u/v: H/2xW/2 (uint8). qcode 1..31 (qscale = 2*qcode)."""
    H, W = y.shape
    qs = 2 * qcode
    FY, FU, FV = _blocks(y), _blocks(u), _blocks(v)

    def quant(F):
        q = np.rint(16 * F / (INTRA_W * qs)).astype(np.int64)
        q = np.clip(q, -2047, 2047)
        dc = np.clip(np.rint(F[..., 0, 0] / 2).astype(np.int64), 0, 1023)
        flat = q.reshape(q.shape[:-2] + (64,))[..., ZIGZAG]
        flat[..., 0] = dc
        return flat
    QY, QU, QV = quant(FY), quant(FU), quant(FV)
    bw = Bits(); bw.put(FLAGS, 8)
    last = [512, 512, 512]
    for my in range(H // 16):
        for mx in range(W // 16):
            if mx or my:
                bw.put(1, 1)                                   # 주소 증가 1
            if mx == 0 and my == 0:
                bw.put(1, 2); bw.put(qcode, 5)                 # 인트라 + 양자화
            else:
                bw.put(1, 1)                                   # 인트라
            blks = [(QY[2 * my, 2 * mx], 0), (QY[2 * my, 2 * mx + 1], 0), (QY[2 * my + 1, 2 * mx], 0),
                    (QY[2 * my + 1, 2 * mx + 1], 0), (QU[my, mx], 1), (QV[my, mx], 2)]
            for blk, c in blks:
                dc = int(blk[0])
                _dc_put(bw, dc - last[c], DC_LUM if c == 0 else DC_CHR); last[c] = dc
                nz = np.nonzero(blk[1:])[0]
                prev = 0
                for k in nz:
                    lvl = int(blk[1 + k]); run = int(k) - prev; prev = int(k) + 1
                    a = abs(lvl)
                    vc = RL.get((run, a))
                    if vc:
                        bw.put(vc[0], vc[1]); bw.put(1 if lvl < 0 else 0, 1)
                    else:
                        bw.put(*ESC); bw.put(run, 6); bw.put(lvl & 0xfff, 12)
                bw.put(*EOB)
    bw.align()
    return bytes(bw.out) + b'\x00\x00\x01\xb0'
