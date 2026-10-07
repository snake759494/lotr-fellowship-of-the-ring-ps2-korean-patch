# 반지의 제왕: 반지 원정대 PS2 한글 패치 v1.2

**The Lord of the Rings: The Fellowship of the Ring (USA), SLUS-20520**용 비공식 한글 패치입니다.

## 다운로드 / 적용

[정식 릴리즈 v1.2](https://github.com/snake759494/lotr-fellowship-of-the-ring-ps2-korean-patch/releases/tag/v1.2)에서 `LOTR_Fellowship_of_the_Ring_KO_v1.2.xdelta` 하나를 받으세요.

수정하지 않은 북미판 원본 ISO에 xdelta3로 적용합니다. 다른 지역판·개정판·이미 한글화한 ISO에는 적용하지 않습니다. xdelta 실행 파일과 게임은 제공하지 않습니다.

```powershell
xdelta3 -d -s "Lord of the Rings, The - The Fellowship of the Ring (USA).iso" LOTR_Fellowship_of_the_Ring_KO_v1.2.xdelta Lord_of_the_Rings_Fellowship_of_the_Ring_KO.iso
Get-FileHash .\Lord_of_the_Rings_Fellowship_of_the_Ring_KO.iso -Algorithm SHA256
```

| 대상 | SHA-256 |
|---|---|
| 원본 ISO | `c966d5f65ce6308ca8c1afe0f0b8dfa2dd41b642ca7959d59034c2bce989ddb2` |
| 완성 ISO | `d3a0093bde5fd64e00b35daca62529ec98d381084a46a779e506a3c870cc570a` |
| xdelta | `41f8766ecfb2b47c7e8fe5f43ecc6b4a6898a9832a6414cc266ad6bef702610b` |

원본 ISO 크기: **2,403,368,960바이트**, 완성 ISO 크기: **2,407,677,952바이트**. 적용 후 새로 부팅하세요. 원본 게임의 세이브스테이트는 사용하지 마세요.

## 포함 내용

- 메뉴·설정·도움말·퀘스트·아이템·지명·이야기 화면 내레이션 등 UI 문자열 433항목.
- 게임 내 대사 자막 1,008종(사용처 1,016곳). 고유명사는 톨킨 정식 한국어판 용어 기준(골목쟁이집, 깊은골, 바람마루, 묵은숲, 성큼걸이 등).
- 한글 글꼴: 메뉴·제목(원본 세리프)은 서울한강 EB, 대사·내레이션(원본 산세리프)은 나눔스퀘어 네오 Bold.
- 제작진 인명, PC판 키 이름, 내부 경로는 원문 유지. 노래·반지 글귀 같은 운문은 요약한 문장으로 대신했습니다.

## 한글 표시 방식

원본은 256자만 다루는 1바이트 글꼴 엔진입니다. 문자열 그리기·너비 계산 함수를 2바이트 한글(`B0–C8`+`A1–FE`)을 처리하는 코드로 교체하고, 한글 글리프(873자)를 실행 파일 세그먼트 뒤에 붙였습니다. 이미 적재된 폰트 텍스처 객체를 복제해 픽셀만 한글 페이지로 바꿔 그립니다. 엔진이 문자열·자막 리소스 파일의 크기나 항목 위치가 바뀌면 적재에 실패하므로, 모든 항목을 원래 크기·자리에 덮어썼고 자막은 원래 영어 바이트 길이 안에 맞췄습니다. 디스크는 ISO9660과 UDF를 함께 갱신합니다. 자세한 내용은 [재빌드 안내](docs/BUILD.md).

## 검증 범위

PCSX2 2.2에서 부팅 → 저장 장치 선택 → 메인 메뉴 → 새 게임 → 인트로 영상 → 이야기 화면(줄바꿈·버튼 아이콘) → 골목쟁이집 플레이 → 일시정지·퀘스트 메뉴 → 컷신 대사 자막을 확인했습니다. 사용자가 이후 게임 진행 대사 표시를 확인했습니다. 공개 소스로 재빌드한 ISO가 정식 빌드와 SHA-256이 일치하고, xdelta 복원 ISO도 일치합니다. [검증 기록](validation/verification.json).

전체 플레이, 모든 레벨, 저장/불러오기, PS2 실기는 미검증입니다. 실행 파일 확장으로 게임 힙이 약 720KB 줄었으므로 대형 레벨에서의 메모리 여유는 확인되지 않았습니다. 정식 릴리즈 표기는 완전한 실기 QA를 뜻하지 않습니다.

## 개발 / 권리

[재빌드 안내](docs/BUILD.md) · [변경 내역](CHANGELOG.md) · [권리 및 배포 범위](RIGHTS.md).

이 저장소에는 패치 소스와 한국어 번역만 있습니다. 원본 ISO·게임 실행 파일·영어 원문·추출 바이너리·폰트·외부 실행 파일은 포함하지 않습니다. 영어 원문 표는 사용자의 원본 ISO에서 로컬로 생성합니다. 번역에는 스포일러가 있습니다.
