# Third-Party Notices · 서드파티 고지

이 프로젝트의 원본 소스 코드는 MIT 라이선스입니다([LICENSE](LICENSE)). 아래 구성요소는
각자의 라이선스를 따릅니다.

---

## A. 이 저장소에 동봉되어 함께 배포되는 것

### 글꼴 (SIL Open Font License 1.1 — 전문은 [OFL.txt](OFL.txt))

| 글꼴 | 저작권 | 출처 |
|---|---|---|
| Noto Serif KR (`artifact-intelligence/fonts/NotoSerifKR.ttf`) | © 2017–2024 Adobe (http://www.adobe.com/) | https://github.com/notofonts/noto-cjk |
| Noto Sans KR (`artifact-intelligence/workspace/fonts/NotoSansKR-heading-700-900.woff2`) | © 2014–2021 Adobe, Reserved Font Name 'Source' | https://github.com/notofonts/noto-cjk |
| Pretendard (`artifact-intelligence/fonts/PretendardVariable.woff2`) | © 2023 Kil Hyung-jin, Reserved Font Name 'Pretendard' | https://github.com/orioncactus/pretendard |

세 글꼴 모두 SIL Open Font License, Version 1.1 을 따릅니다.

### HWPX 서식 데이터 (Apache License 2.0)

아래 JSON은 공개 오픈소스에서 HWPX(OWPML) 요소 순서를 추출한 파생 데이터입니다.
각 파일의 `_출처` 필드에 저장소·커밋·라이선스가 함께 기록되어 있습니다.

| 파일 | 출처 | 라이선스 |
|---|---|---|
| `artifact-intelligence/build/요소순서.json` | https://github.com/hancom-io/hwpx-owpml-model (Hancom Inc.) | Apache-2.0 |
| `artifact-intelligence/build/골든요소순서.json` | https://github.com/neolord0/hwpxlib | Apache-2.0 |

Apache-2.0 전문: https://www.apache.org/licenses/LICENSE-2.0

---

## B. 별도로 설치되어 실행되는 의존성 (이 저장소에 코드가 포함되지 않음)

설치 시점에 각 패키지 매니저로 받아오며, 저장소에는 코드가 들어 있지 않습니다
(`node_modules/`, 파이썬 `.venv/` 는 `.gitignore` 로 제외). 각자의 라이선스를 따릅니다.

### npm (`artifact-intelligence/package.json`)
- **kordoc** 4.7.1 — 파일 첨부 파싱(HWP·HWPX·PDF·XLSX·DOCX·OCR). MIT.
- **ima2-gen** — 그림 생성(웹앱 서버에 전역 설치되는 CLI, `build/imageasset.py` 가 호출). 라이선스는 해당 npm 패키지 참조.

### PyPI (`artifact-intelligence/build/requirements.txt`, `mcp/requirements.txt`)
- pillow (HPND), lxml (BSD-3-Clause), fonttools (MIT), brotli (MIT),
  python-pptx (MIT), python-hwpx (해당 패키지 참조), mcp (MIT).
- **pymupdf** 1.28.0 — **GNU AGPL-3.0**(또는 상용 라이선스). 배포·서비스 시 AGPL 조건에
  유의하세요. https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright

---

*온톨로지 지식 정본(`ontology.json`)은 이 저장소에 포함되지 않으며 정책 서버에만 있습니다.*
