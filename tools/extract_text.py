"""번역 원문(ui_en.tsv, sub_en.tsv) 추출"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from texts import *

ui = []
for f in xdu_files():
    d = open(f, 'rb').read(); o, h, es = parse(d)
    for e in sorted(es, key=lambda e: e['off']):
        if e['a'] != 0:
            continue
        ui.append((rel(f), e['id'], dec(cstr(xdu_strings(d, e)[0]))))
with open('translation/ui_en.tsv', 'w', encoding='utf-8') as w:
    for r, i, s in ui:
        w.write(f'{r}\t{i}\t{esc(s)}\n')

subs = collections.OrderedDict()
for f in sdu_files():
    d = open(f, 'rb').read(); o, h, es = parse(d)
    for e in sorted(es, key=lambda e: e['off']):
        if (e['a'], e['t']) != (2, 3):
            continue
        s = sub_entry(d, e)
        if s:
            subs.setdefault(dec(s), []).append(f'{rel(f)}:{e["id"]}')
with open('translation/sub_en.tsv', 'w', encoding='utf-8') as w:
    for k, s in enumerate(subs):
        w.write(f'{k}\t{esc(s)}\n')
print(len(ui), len(subs))
