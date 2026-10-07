# 재빌드

Python 3.13에서 검증했습니다. 저장소 루트에 해시가 일치하는 원본을 `Lord of the Rings, The - The Fellowship of the Ring (USA).iso`라는 이름으로 두고, `SeoulHangangEB.ttf`와 `NanumSquareNeo-cBd.ttf`를 별도로 준비합니다. 파일은 Git에서 제외됩니다.

```powershell
python -m pip install -r requirements.txt
python -X utf8 tools/extract.py        # 원본 ISO -> work/orig (FELLOWSH.BIN 제외)
python -X utf8 tools/extract_text.py   # 영어 원문 표 translation/ui_en.tsv, sub_en.tsv 생성
python -X utf8 tools/build.py          # 글리프·코드·문자열 생성 후 완성 ISO 빌드
```

`build.py`는 원본 ISO를 보존하고 `Lord_of_the_Rings_Fellowship_of_the_Ring_KO.iso`를 따로 만듭니다. 완성 ISO SHA-256은 README와 일치해야 합니다.

## 구성

- `translation/ui_ko.tsv`: `ui_en.tsv` 행 번호(0부터) + 한국어. 없는 행은 원문 유지.
- `translation/sub_ko.tsv`: `sub_en.tsv` 번호 + 한국어. 자막은 원래 영어 바이트 길이를 넘을 수 없습니다(한글 1자 = 2바이트). 넘으면 경고와 함께 원문이 유지됩니다.
- `tools/kfont/kwalk.c`: 한글 2바이트 지원 문자열 그리기/너비 함수, 한글 페이지 텍스처 객체 관리.
- `tools/kfont/shim.S`: 게임 EE ABI(인자 a0–a3/t0–t3, 128비트 레지스터 보존, 16바이트 스택 정렬)와 o32 C 연결.
- `tools/kfont_gen.py`: 256×64 8bpp 글리프 페이지 생성.
- `tools/build.py`: 실행 파일 확장(코드+글리프를 .bss 뒤에 두고 힙 시작 3곳 이동), XDU/SDU 제자리 교체, ISO9660+UDF 기록.
- `tools/udf.py`: UDF 파일 엔트리 갱신.

## 패치 생성/복원

```powershell
xdelta3 -e -9 -S djw -s "Lord of the Rings, The - The Fellowship of the Ring (USA).iso" Lord_of_the_Rings_Fellowship_of_the_Ring_KO.iso LOTR_Fellowship_of_the_Ring_KO_v1.0.xdelta
xdelta3 -d -s "Lord of the Rings, The - The Fellowship of the Ring (USA).iso" LOTR_Fellowship_of_the_Ring_KO_v1.0.xdelta roundtrip.iso
```

xdelta 버전/옵션에 따라 패치 바이트는 달라질 수 있지만 복원 ISO는 같아야 합니다. 생성한 게임 자료나 폰트를 커밋하지 마세요.
