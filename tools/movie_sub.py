"""레벨 VDU 동영상(IPU 인트라 프레임)에 한국어 자막을 입힌다.

subs(movie/subs/<이름>.tsv: 시작초 TAB 끝초 TAB 문장, 줄바꿈 \\n)가 걸린 프레임만 디코드 -> 자막 합성
-> IPU 인트라로 재인코딩. 프레임 크기·오프셋은 원본 그대로 두고(자원 파일 크기 고정), 새 프레임이
원래 자리에 들어가는 가장 고운 양자화 값을 고르고, 계수 코드를 이스케이프 코드로 바꿔 정확히 같은
바이트 수로 맞춘다. 엔진은 프레임을 끊김 없이 IPU 에 이어 넣으므로 0 바이트가 끼면 멈춘다.
"""
import os, sys, struct, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from srsc import parse
import ipu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')
SIZE = 19
STROKE = 2
LINE_H = 23
MAXW = 600
FPS = 30
Q_STEPS = [2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 17, 20, 24, 28, 31]
_font = ImageFont.truetype(FONT, SIZE)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_subs(path):
    out = []
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\r\n')
        if not line or line.startswith('#'):
            continue
        a, b, t = line.split('\t', 2)
        out.append((float(a), float(b), t))
    return out


def wrap(text):
    lines = []
    for para in text.split('\\n'):
        cur = ''
        for w in para.split(' '):
            t = (cur + ' ' + w).strip()
            if _font.getlength(t) > MAXW and cur:
                lines.append(cur); cur = w
            else:
                cur = t
        lines.append(cur)
    return lines


def render(text, W, H):
    """자막 알파(0..1)와 외곽선 알파를 W x H 로"""
    lines = wrap(text)
    fill = Image.new('L', (W, H), 0); edge = Image.new('L', (W, H), 0)
    df, de = ImageDraw.Draw(fill), ImageDraw.Draw(edge)
    bottom = H - 14
    y0 = bottom - LINE_H * len(lines)
    for i, ln in enumerate(lines):
        x = (W - _font.getlength(ln)) / 2; y = y0 + i * LINE_H
        de.text((x, y), ln, font=_font, fill=255, stroke_width=STROKE, stroke_fill=255)
        df.text((x, y), ln, font=_font, fill=255)
    return np.asarray(fill, np.float32) / 255, np.asarray(edge, np.float32) / 255


def compose(y, u, v, fill, edge):
    y = y.astype(np.float32); u = u.astype(np.float32); v = v.astype(np.float32)
    y = y * (1 - edge) + 16 * edge
    y = y * (1 - fill) + 235 * fill
    ce = edge.reshape(edge.shape[0] // 2, 2, edge.shape[1] // 2, 2).mean((1, 3))
    u = u * (1 - ce) + 128 * ce; v = v * (1 - ce) + 128 * ce
    return [np.clip(np.rint(a), 0, 255).astype(np.uint8) for a in (y, u, v)]


def decode_frames(frames, W, H, tmp):
    open(tmp, 'wb').write(b'ipum' + struct.pack('<IHHI', 0, W, H, len(frames)) + b''.join(frames))
    r = subprocess.run([ffmpeg(), '-v', 'error', '-f', 'ipu', '-i', tmp, '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'],
                       capture_output=True, check=True)
    n = W * H * 3 // 2; a = np.frombuffer(r.stdout, np.uint8)
    assert len(a) == n * len(frames), (len(a), len(frames))
    out = []
    for i in range(len(frames)):
        f = a[i * n:(i + 1) * n]
        out.append((f[:W * H].reshape(H, W), f[W * H:W * H * 5 // 4].reshape(H // 2, W // 2),
                    f[W * H * 5 // 4:].reshape(H // 2, W // 2)))
    return out


def process(vdu_bytes, subs, tmp, log=print):
    """VDU 파일 바이트 + 자막 -> 새 VDU 파일 바이트(크기 동일)"""
    d = bytearray(vdu_bytes); _, _, es = parse(bytes(d))
    hd = [x for x in es if x['a'] == 66][0]; dt = [x for x in es if x['a'] == 67][0]
    w = struct.unpack_from('<%dI' % (hd['size'] // 4), d, hd['off'])
    W, H, N = w[3], w[4], w[6]
    offs = list(w[7:7 + N]) + [dt['size']]
    base = dt['off']
    stats = []; newf = {}
    for a, b, text in subs:
        f0 = max(0, int(round(a * FPS))); f1 = min(N, int(round(b * FPS)))
        fill, edge = render(text, W, H)
        frames = [bytes(d[base + offs[k]:base + offs[k + 1]]) for k in range(f0, f1)]
        for k, (y, u, v) in zip(range(f0, f1), decode_frames(frames, W, H, tmp)):
            cap = offs[k + 1] - offs[k]
            y2, u2, v2 = compose(y, u, v, fill, edge)
            e, q = ipu.encode_exact(y2, u2, v2, cap)
            if e is None:
                raise RuntimeError(f'프레임 {k} 을 원래 크기({cap})에 맞출 수 없음')
            d[base + offs[k]:base + offs[k + 1]] = e
            stats.append(q)
    if stats:
        log(f'  자막 프레임 {len(stats)}, 양자화 평균 {sum(stats) / len(stats):.1f}, 최대 {max(stats)}')
    return bytes(d)
