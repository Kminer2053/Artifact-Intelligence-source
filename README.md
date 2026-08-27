<div align="center">

# 문서지능 · Artifact Intelligence — 소스

**대한민국 공공기관 문서를 사람과 함께 만드는 파이프라인의 전체 소스입니다.**
웹앱 · Claude Code 플러그인 · MCP 서버를 한 리포에 담았습니다.

먼저 써 보기(설치 없이) — **https://artifact-intelligence.app**

![구성](https://img.shields.io/badge/구성-웹앱·플러그인·MCP-1E67F0)
![산출](https://img.shields.io/badge/산출-6종%20문서-101B33)
![출력](https://img.shields.io/badge/출력-HTML·PDF·HWPX·PPTX-267A68)

</div>

---

## 이 리포는 무엇인가

문서지능은 의도(무엇을·누구에게·왜)와 자료(사실·수치)만 받아, 결재에 올릴 수 있는 공공기관 문서 초안을 만드는 도구입니다. 목차 설계·개조식 변환·한 장 맞춤·한글(HWPX) 변환을 규칙이 처리하고, 사람은 확인하고 고칠 데만 짚습니다. 만드는 문서는 여섯 가지 — **1페이지 보고서 · 풀버전 보고서 · 시행문 · 규정 · 보도자료 · 발표 슬라이드(PPTX)** 입니다.

이 리포는 그 파이프라인의 **소스 전체**를 공유용으로 담은 것입니다. 세 가지 표면(웹앱·플러그인·MCP)의 코드가 모두 들어 있습니다.

> **온톨로지 지식 정본(`ontology.json`)은 이 리포에 없습니다.** 개체×3요소 규칙·목차 논리 같은 지식 정본은 정책 서버(artifact-intelligence.app)에만 두고, 실행 중 필요한 조각만 그때그때 받아옵니다. 그 밖의 처리 코드(조립·검사·변환·판정 규칙)는 사용자 문서를 다루므로 — 자료를 서버로 보내지 않으려고 — 설치본에서 로컬로 돌고, 이 리포에 함께 있습니다.

## 세 표면, 하나의 코어

세 표면이 같은 코어([`workspace/api.py`](artifact-intelligence/workspace/api.py))를 공유합니다. 작업 목록을 한 곳에 적고 셋이 읽으므로, 어느 표면에서 만들든 규칙이 갈라지지 않습니다.

| 표면 | 무엇 | 어디서 도나 |
|---|---|---|
| **웹앱** | 브라우저에서 바로, 설치 없이 | 정책 서버(artifact-intelligence.app) |
| **스킬** | Claude Code 플러그인 | 설치한 컴퓨터(로컬) |
| **MCP** | Codex 등 에이전트가 도구로 호출 | 설치한 컴퓨터(로컬) |

- **온톨로지 지식**은 정책 서버에만 있고, `지식()`이 필요한 조각만 조회합니다.
- **문서 처리**(판정·조립·검사·조판·한글 변환)는 사용자 자료를 받으므로 로컬에서 돕니다 — 문서 내용은 설치한 컴퓨터를 벗어나지 않습니다(웹앱으로 쓰면 서버가 처리).

## 디렉터리 구조

```
Artifact-Intelligence-source/
├─ .claude-plugin/marketplace.json   Claude Code 마켓플레이스 등록 정보
├─ docs/promo/                       시연 영상·포스터
└─ artifact-intelligence/            ── 본체 (웹앱 + 플러그인 + MCP 가 공유) ──
   ├─ SKILL.md                       스킬 진입 지침(Claude Code 가 읽는 사용설명)
   ├─ README.md                      플러그인 설치·사용 안내
   ├─ .claude-plugin/plugin.json     플러그인 메타
   ├─ .cursor/                       Cursor 용 슬래시 명령·룰
   ├─ commands/문서지능.md            슬래시 명령 정의
   ├─ bin/bootstrap.sh               첫 기동 — 정책 토큰 발급·의존성 설치
   │
   ├─ workspace/                     ── 웹앱 · 편집기 · 공용 코어 ──
   │  ├─ api.py                      작업 목록(스킬·MCP·웹앱이 다 읽는 단일 코어)
   │  ├─ serve.py                    HTTP 서버(웹앱·편집기 구동)
   │  ├─ app.html                    웹앱 화면
   │  ├─ admin.html                  관리자 콘솔
   │  ├─ render_editor_any.py        리터칭 편집기 생성
   │  ├─ apply_edit_any.py           편집 반영·재조립
   │  └─ ui-tokens.css · icons.svg   디자인 토큰·아이콘
   │
   ├─ build/                         ── 조립·검사·변환 엔진 (py 33 · json 11 · css 7) ──
   │  ├─ assemble*.py                장르별 조립기(1p·풀버전·시행문·규정·보도자료·슬라이드)
   │  ├─ stylelint.py                문체 게이트(개조식·번역투 검사)
   │  ├─ 지어냈나.py                  사실 검증(없는 수치·이름 탐지)
   │  ├─ 판별로직.py                  장르 판정 규칙(가중치·문턱)
   │  ├─ tohwpx.py · topptx.py · tomd.py   한글(HWPX) · PPTX · Markdown 변환
   │  ├─ 화면읽기.py · 카탈로그.py     조판 측정·전이 카탈로그 생성
   │  └─ *.css                       장르별 인쇄 CSS(정본 규격)
   │
   ├─ buildplan/                     빌드플랜 설계·승인·되돌리기
   ├─ feedback/                      리터칭 역추적·동의 코퍼스
   ├─ history/                       버전·이력·diff
   ├─ personalization/               개인·부서 프로파일
   ├─ ontology/                      editor-profiles.json(편집기 프로파일)
   │                                 ※ 지식 정본 ontology.json 은 정책 서버에만 — 이 리포에 없음
   ├─ mcp/                           MCP 서버(server.py · run.sh)
   ├─ hooks/                         플러그인 훅
   └─ fonts/                         본문 폰트(Noto Serif KR · Pretendard)
```

## 파이프라인 한눈에

의도·자료 → **판별로직**이 유형·장르 판정 → **빌드플랜**(사람이 승인) → **assemble**가 3층 인스턴스로 조립 → **stylelint·지어냈나**가 문체·사실 검사 → **편집기**에서 사람이 리터칭 → **tohwpx/topptx**로 한글·발표 파일 내보내기. 사람이 고친 곳은 **feedback**이 정본에 역추적해 다음 문서에 반영합니다.

## 실행

**웹앱·편집기를 로컬에서 띄우기**
```bash
python3 artifact-intelligence/workspace/serve.py        # 기본 127.0.0.1:8642
```
온톨로지가 필요한 작업은 정책 서버 연결이 있어야 합니다(`artifact-intelligence/정책서버.conf` 또는 env `문서지능_정책서버`). 첫 기동 스크립트는 [`bin/bootstrap.sh`](artifact-intelligence/bin/bootstrap.sh)가 처리합니다(정책 토큰 발급·의존성 설치).

**Claude Code 플러그인으로 설치**
```
/plugin marketplace add Kminer2053/Artifact-Intelligence-public
/plugin install artifact-intelligence@artifact-intelligence
```

**Codex 등에서 MCP로 붙이기**
```bash
codex mcp add artifact-intelligence -- "$(pwd)/artifact-intelligence/mcp/run.sh"
```

필요 환경: 파이썬 3.10 이상. 자세한 사용법은 [`artifact-intelligence/README.md`](artifact-intelligence/README.md)와 [`artifact-intelligence/SKILL.md`](artifact-intelligence/SKILL.md)를 보세요.

## 문의

문서지능 · park2053@gmail.com
