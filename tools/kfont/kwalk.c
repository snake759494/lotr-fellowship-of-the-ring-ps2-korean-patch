/* 한글 2바이트(B0-C8, A1-FE) 지원 문자열 그리기/너비 계산 */
typedef struct { int *pos, *rowEnd, *rowStart, rowH, spaceW, vOff, mx, ready, r20;
                 void **pages; int pcap, pcount; int *pstart; int scap, scount; } Font;
typedef struct { const unsigned char *str; int font, spacing, maxw; int *outcnt; int draw;
                 int x, y, color; void *clip; } Ctx;
typedef struct { short npages, per, cols, cw, ch, adv, dy, tid; } KSet;

extern int g_setup(Font *f, int id);
extern int g_map(int ch);
extern int g_scale(void);                      /* float bits */
extern int g_mul(int w, int scale);            /* (int)(w*scale) */
extern void g_draw(void *tex, int x, int y, int u, int v, int w, int h, Ctx *c, int scale, int yscale);
extern int g_fmul(int a, int b);                /* float a*b (비트) */
extern const unsigned short kmap[];             /* 전체 음절 -> 세리프 세트 위치(없으면 0xFFFF) */
#define KFB 0x3fa66666                          /* 세리프 대체 시 산세리프 확대율 1.3 */
#define KFB_DY 1
#define ONE 0x3f800000

extern const KSet kset[2];
extern const unsigned char kpix[];             /* 페이지별 256xKPH 8bpp 픽셀(세트0 다음 세트1) */
extern const unsigned int kpal[256];           /* 변환 완료 팔레트(알파 0..0x80) */
#define KMAXP 160
#define KPH 64                                 /* 페이지 높이 */
#define OBJW 48                                /* 텍스처 객체 0xC0 바이트 */
__attribute__((section(".data"), aligned(16))) static unsigned int kobj[2][KMAXP][OBJW] = {{{1}}};
__attribute__((section(".data"), aligned(16))) static unsigned int kpalobj[8] = {1};

/* 이미 적재된 폰트 페이지 객체를 복제해 내장 한글 페이지를 가리키게 한다 */
static void *kpage(Font *f, int set, int page)
{
    unsigned int *o, *t, ref;
    int i, base;
    if (page >= KMAXP || page >= kset[set].npages) return 0;
    o = kobj[set][page];
    ref = 0x000b7000 + set * 0x100 + page;      /* 고유 참조값 */
    /* 엔진이 객체를 내보내며 헤더를 지운 경우 다시 초기화 */
    if (o[6] && (((unsigned char *)o)[8] & 3) == 3) {
        /* 엔진이 바인딩보다 해제를 더 많이 해 카운트가 0이 되면 헤더가 지워지므로 넉넉히 유지 */
        if ((o[1] & 0xffff) < 0x2000) o[1] = (o[1] & 0xffff0000) | 0x4000;
        return o;
    }
    t = (unsigned int *)f->pages[0];
    if (!t || (((unsigned char *)t)[8] & 3) != 3) return 0;
    if (o[6] && o[33] != 0xffffffff) {
        /* VRAM 에 살아 있는데 엔진이 리소스 헤더만 지운 경우: 헤더만 복구 */
        o[0] = ref;
        o[1] = (o[1] & 0xffff0000) | 0x4000;
        o[2] = (o[2] & ~0xffu) | 0x23;
        return o;
    }
    for (i = 0; i < OBJW; i++) o[i] = t[i];
    if (!kpalobj[2]) {
        unsigned int *tp = (unsigned int *)t[16];
        for (i = 0; i < 8; i++) kpalobj[i] = tp[i];
        kpalobj[1] = 256; kpalobj[2] = (unsigned int)kpal;
        if (kpalobj[7]) kpalobj[7] = 256;
    }
    base = 0;
    for (i = 0; i < set; i++) base += kset[i].npages;
    o[0] = ref;
    o[1] = (o[1] & 0xffff0000) | 0x4000;        /* 참조 카운트(0 이 되지 않게) */
    o[2] = (o[2] & ~0xffu) | 0x23;              /* 적재 완료, 자동 파괴 안 함 */
    o[3] = 0; o[4] = 0; o[5] = 0;
    o[9] &= ~2u;                                /* GS 레지스터 재계산 */
    o[16] = (unsigned int)kpalobj;
    for (i = 17; i < OBJW; i++) o[i] = 0;
    o[11] = KPH; o[13] = KPH;                   /* 높이 */
    o[21] = (unsigned int)(kpix + (base + page) * 256 * KPH);
    o[25] = t[25];
    o[32] = 0xffffffff; o[33] = 0xffffffff;     /* VRAM 미배정 */
    return o;
}
#define FONTS ((Font *)0x418818)

int kwalk(Ctx *c)
{
    Font *f = FONTS + c->font;
    const unsigned char *p = c->str, *q;
    int x = c->x, scale, ch;

    if (!f->ready && !g_setup(f, c->font)) { if (c->outcnt) *c->outcnt = 0; return 0; }
    scale = g_scale();
    while ((ch = *p) != 0) {
        if (c->clip && ((int *)c->clip)[2] < x) break;
        q = p;
        if (ch == 10 || ch == 13) { p++; continue; }
        if (ch == 0x5c) {
            const unsigned char *r = p + 1; int n = 0; signed char v = 0;
            while (n < 3 && (unsigned)(*r - '0') < 10) { v = (signed char)(v * 8 + *r - '0'); r++; n++; }
            if (n == 3) ch = v;
            p = r - 1;
        }
        if (ch == 9) x = x - x % 30 + 30;
        else if (ch == ' ') x += f->spaceW;
        else {
            int page, u, v, w, h, gw, dy = 0, xs = scale, ys = ONE;
            void *tex = 0;
            if (c->font < 2 && ch >= 0xB0 && ch <= 0xC8 && p[1] >= 0xA1 && p[1] != 0xFF) {
                int idx = (ch - 0xB0) * 94 + (p[1] - 0xA1), in, set = c->font, li = idx;
                const KSet *k;
                p++;
                if (set == 0) {
                    li = kmap[idx];
                    if (li == 0xffff) { set = 1; li = idx; ys = KFB; xs = g_fmul(scale, KFB); dy = KFB_DY; }
                }
                k = &kset[set];
                page = li / k->per;
                in = li % k->per;
                tex = kpage(f, set, page);
                u = (in % k->cols) * k->cw; v = 1 + (in / k->cols) * k->ch;
                w = k->cw; h = k->ch;
                if (ys == ONE) dy = k->dy;
                gw = g_mul(k->adv, xs);
            } else {
                int gi = g_map(ch), row = 0, t1, s;
                while (g_map(f->rowStart[row]) < gi) row++;
                t1 = f->pos[gi + 1] - 1;
                if (t1 < 3) t1 = f->rowEnd[row];
                page = 0;
                for (s = 1; s < f->scount && f->pstart[s] <= row; s++) page = s;
                u = f->pos[gi]; w = t1 - u; h = f->rowH;
                v = (row - f->pstart[page]) * h + f->vOff;
                gw = g_mul(w, scale) + 1;
                tex = f->pages[page];
            }
            if (c->draw && tex) g_draw(tex, x, c->y + dy, u, v, w, h, c, xs, ys);
            x += gw + c->spacing;
            if (!c->draw && c->maxw > 0 && x >= c->maxw) { p = q; break; }
        }
        p++;
    }
    if (c->outcnt) *c->outcnt = p - c->str;
    return x - c->x;
}
