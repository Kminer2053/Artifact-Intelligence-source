#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
문서지능 규칙 카드(cards.json) -> 경량 md 스킬 프로토타입 빌더.

입력: ../../cards.json (스크립트 기준 상대경로, 227장, Agent Skills 프로토타입 소스)
출력: ./artifact-intelligence-rules/  (Agent Skills 스펙 준수 디렉터리)

재실행하면 출력 디렉터리를 통째로 비우고 다시 만든다 — 이 스크립트가 만든
파일만 그 디렉터리에 남는다. 소스 카드(cards.json)는 읽기만 한다.

스펙 참고: https://agentskills.io/specification
"""
import json
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_PATH = next((p for p in (os.path.join(SCRIPT_DIR, "..", "cards.json"), os.path.join(SCRIPT_DIR, "..", "..", "cards.json")) if os.path.exists(p)), os.path.join(SCRIPT_DIR, "..", "cards.json"))
OUT_DIR = os.path.join(SCRIPT_DIR, "artifact-intelligence-rules")
SKILL_NAME = "artifact-intelligence-rules"

# 6개 장르: (cards.json 의 doc_types 표기, 표시용 한글 이름, 파일명 영문 slug)
GENRES = [
    ("한 장 보고서", "한 장 보고서", "onepage"),
    ("풀버전 보고서", "풀버전 보고서", "fullreport"),
    ("시행문(공문)", "시행문(공문)", "gongmun"),
    ("규정·내규", "규정·내규", "regulation"),
    ("보도자료", "보도자료", "press"),
    ("발표 슬라이드", "발표 슬라이드", "slides"),
]
COMMON_DOC_TYPE = "공통"

# 부분(part) 표시 순서 — 판정부터 시작해 실제로 문서를 써 내려가는 순서를 따른다.
PART_ORDER = [
    "판정·유형",
    "문서 전체 구성",
    "제목·표지",
    "수신·발신·결재선",
    "요약(두괄)",
    "본문 글머리·위계",
    "문장 표현",
    "표",
    "그림·도식·차트",
    "여백·판면",
    "글꼴·크기",
    "붙임·별첨",
]

# 체크리스트에서 우선하는 value_kind 순서 (값·문구 우선, 12줄 이내)
CHECKLIST_PRIORITY = {"값": 0, "문구": 1, "판단": 2, "구조": 3}
CHECKLIST_MAX_LINES = 12


def load_cards():
    with open(CARDS_PATH, "r", encoding="utf-8") as f:
        cards = json.load(f)
    return cards


def group_by_part(cards):
    """part -> 카드 리스트 (PART_ORDER 순, 각 부분 안에서는 card_id 순)."""
    buckets = {}
    for c in cards:
        buckets.setdefault(c.get("part", ""), []).append(c)
    for part in buckets:
        buckets[part].sort(key=lambda c: c["card_id"])
    ordered = []
    for part in PART_ORDER:
        if part in buckets:
            ordered.append((part, buckets.pop(part)))
    # PART_ORDER 에 없는 부분이 새로 생기면 뒤에 이어 붙인다(누락 방지).
    for part, items in sorted(buckets.items()):
        ordered.append((part, items))
    return ordered


def render_card(c):
    """카드 한 장 -> md 한 단락. before/after 있으면 한 줄 더."""
    title = c.get("title", "").strip()
    rule = c.get("rule", "").strip()
    why = c.get("why", "").strip()
    line = f"**{title}** — {rule}"
    if why:
        line += f" (왜: {why})"
    out = [line]
    before = c.get("before", "").strip()
    after = c.get("after", "").strip()
    if before and after:
        out.append(f"전: {before} / 후: {after}")
    return "\n".join(out)


def render_sections(cards):
    """부분별 섹션 md 본문(헤딩 제외 카드 목록부터)을 만든다."""
    sections = group_by_part(cards)
    parts_md = []
    for part, items in sections:
        parts_md.append(f"## {part}\n")
        for c in items:
            parts_md.append(render_card(c))
            parts_md.append("")
    return "\n".join(parts_md).rstrip() + "\n"


def build_common_md(common_cards):
    header = (
        f"# 공통 규칙\n\n"
        f"장르에 상관없이 적용되는 규칙 {len(common_cards)}장. "
        f"장르별 파일(references/onepage.md 등)과 함께 읽는다.\n\n"
    )
    return header + render_sections(common_cards)


def build_genre_md(doc_type_label, display_name, genre_cards, common_count):
    header = (
        f"# {display_name} 규칙\n\n"
        f"{display_name}에 적용되는 규칙 {len(genre_cards)}장. "
        f"공통 규칙 {common_count}장은 [common.md](common.md)에 있다.\n\n"
    )
    return header + render_sections(genre_cards)


def build_checklist_md(display_name, slug, genre_cards):
    ranked = sorted(
        genre_cards,
        key=lambda c: (CHECKLIST_PRIORITY.get(c.get("value_kind", ""), 9), c["card_id"]),
    )
    selected = ranked[:CHECKLIST_MAX_LINES]
    lines = [f"# 체크리스트 — {display_name} ({slug})\n"]
    lines.append(
        f"쓰고 나서 스스로 검사한다. 규칙 카드 {len(genre_cards)}장 중 "
        f"값·문구 우선 {len(selected)}개.\n"
    )
    for c in selected:
        lines.append(f"- [ ] {c['title'].strip()}")
    return "\n".join(lines) + "\n"


def build_judgement_hint(cards):
    """SKILL.md 에 넣을 장르 판정 힌트 — part '판정·유형' 카드에서 10줄 이내로 압축."""
    detect_ids = [
        "detect-01",
        "detect-02",
        "detect-03",
        "detect-04",
        "detect-05",
        "detect-06",
    ]
    by_id = {c["card_id"]: c for c in cards if c.get("part") == "판정·유형"}
    lines = [
        "1. 사용자가 장르를 직접 말했으면(\"공문으로\", \"보도자료로\") 분석 없이 그대로 따른다.",
        "2. 참조할 양식 파일을 줬으면 신호 판정을 건너뛰고 그 양식을 쓴다.",
        "3. 둘 다 없을 때만 아래 신호로 판정한다.",
        "   - 시행문(공문): '~기 바랍니다' 결문, '수신:'·'귀 부서' 표기, 통보·지시·협조 동사.",
        "   - 규정·내규: '제N조(제목)'·부칙·별표 구조, '제정'·'개정'·'시행한다' 낱말.",
        "   - 보도자료: '보도자료'·'엠바고' 낱말, 배포처 표기, 개조식이 아닌 서술형 문체.",
        "   - 발표 슬라이드: '발표'·'브리핑'·'PT'·'PPT'·'슬라이드'·'장표' 낱말, 화면 투영 용도.",
        "   - 한 장 보고서 vs 풀버전: 분량이 아니라 5분 안에 판단해야 하면 1p, "
        "근거·과정까지 펴야 하면 풀버전으로 가른다.",
        "4. 신호가 겹치거나 애매하면 짐작하지 말고 \"이 문서를 받는 사람이 읽고 "
        "나서 무엇을 해야 하나요?\"라고 되묻는다.",
    ]
    assert len(lines) <= 10, f"장르 판정 힌트가 10줄을 넘었다: {len(lines)}줄"
    # 참고용으로 실제 근거 카드 id를 남긴다(본문 줄 수에는 포함하지 않음).
    return "\n".join(lines), detect_ids


def build_skill_md(cards, genre_counts, common_count):
    hint_lines, hint_source_ids = build_judgement_hint(cards)
    total = len(cards)

    genre_rows = []
    for _, display_name, slug in GENRES:
        genre_rows.append(
            f"- `references/{slug}.md` — {display_name} 규칙 {genre_counts[slug]}장 "
            f"/ `references/checklist-{slug}.md` — 자가 검사 체크리스트"
        )

    version = os.environ.get("RULES_SKILL_VERSION") or "dev"
    body = f"""---
name: {SKILL_NAME}
metadata:
  version: "{version}"
  cards: "{total}"
  source: "https://artifact-intelligence.app/rules/"
description: 대한민국 공공기관 문서(한 장 보고서, 풀버전 보고서, 시행문(공문), 규정·내규, 보도자료, 발표 슬라이드) 작성 규칙 카드 모음. 문서 유형을 판정하고 구성·문체·디자인 규칙을 찾아 초안을 쓰고 스스로 검사할 때 쓴다. "보고서 써줘", "1페이지 보고서", "한 장 보고서", "풀버전 보고서", "공문 작성", "시행문", "규정 개정", "내규", "보도자료 작성", "발표 슬라이드 만들어줘", "발표자료", "PPT" 같은 요청에 사용한다.
---

# 문서지능 규칙마당 — 경량 스킬

## 이 스킬이 하는 일

이 스킬은 공공기관 문서를 쓸 때 지켜야 할 **규칙**만 담고 있다. 규칙 카드
{total}장을 장르별 참고 파일로 나눠 놓았을 뿐이다.

이 스킬이 **하지 않는** 일:

- HTML·PDF·HWPX·PPTX 렌더링
- 개조식 위계·45자 제한 같은 자동 게이트 검사
- 초안을 대신 완성해 파일로 내보내기

이 세 가지는 [artifact-intelligence.app](https://artifact-intelligence.app)
웹앱(또는 같은 이름의 플러그인)이 한다. 이 스킬은 그 웹앱 없이도 사람이 직접
쓰거나 다른 에이전트가 초안을 쓸 때 규칙을 참고하도록 만든 경량판이다.

## 흐름 4단계

1. **문서 유형 판정** — 사용자가 이미 장르를 말했으면 그대로 따르고, 아니면
   아래 "장르 판정 힌트"로 판정한다.
2. **규칙 읽기** — `references/common.md`와 해당 장르의 `references/<장르>.md`를
   읽는다. 부분(part)별 섹션으로 나뉘어 있다.
3. **초안 작성** — 읽은 규칙을 적용해 초안을 쓴다.
4. **자가 검사** — `references/checklist-<장르>.md`로 스스로 검사한다.

## 장르 판정 힌트

{hint_lines}

## 파일 목록

- `references/common.md` — 장르 공통 규칙 {common_count}장
{chr(10).join(genre_rows)}

전체 규칙 카드는 {total}장이며, 위 참고 파일에 장르별로 나뉘어 들어 있다.

## 최신본과 의견

규칙은 [문서지능 규칙마당](https://artifact-intelligence.app/rules/)에서 계속 다듬어진다.
이 묶음은 {version} 판이다. 최신 규칙이 필요하면 규칙마당에서 다시 내려받는다.
현장 관행과 다른 규칙을 만나면 사용자에게 규칙마당에 의견을 남길 수 있다고 알려 준다.
"""
    return body


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def self_check_frontmatter(skill_md_text):
    """Agent Skills 스펙의 name/description 규칙을 스스로 대조한다."""
    m = re.search(r"^name:\s*(.+)$", skill_md_text, re.MULTILINE)
    d = re.search(r"^description:\s*(.+)$", skill_md_text, re.MULTILINE)
    problems = []
    name = m.group(1).strip() if m else ""
    desc = d.group(1).strip() if d else ""

    if not name:
        problems.append("name 필드가 없다")
    else:
        if len(name) > 64:
            problems.append(f"name 길이 초과: {len(name)}자")
        if not NAME_RE.match(name):
            problems.append(f"name 형식 위반(소문자·숫자·하이픈, 연속 하이픈 금지): {name!r}")
        if name != os.path.basename(OUT_DIR):
            problems.append(
                f"name({name})이 디렉터리명({os.path.basename(OUT_DIR)})과 다르다"
            )

    if not desc:
        problems.append("description 필드가 없다")
    elif len(desc) > 1024:
        problems.append(f"description 길이 초과: {len(desc)}자")

    return name, desc, problems


def estimate_tokens(text):
    """대략 토큰 추정: 한글 글자수/2.2 + 그 외(영문 등) 글자수/4. '추정'이다."""
    hangul = sum(1 for ch in text if "가" <= ch <= "힣")
    other = len(text) - hangul
    return round(hangul / 2.2 + other / 4)


def write_file(rel_path, content):
    full = os.path.join(OUT_DIR, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return full


def run_skills_ref_validate(out_dir):
    try:
        result = subprocess.run(
            ["npx", "--yes", "skills-ref", "validate", out_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        return f"실행됨 (returncode={result.returncode})\n{combined.strip()}"
    except FileNotFoundError:
        return "미실행 (npx 없음)"
    except subprocess.TimeoutExpired:
        return "미실행 (60초 타임아웃)"
    except Exception as e:  # noqa: BLE001
        return f"미실행 ({e.__class__.__name__}: {e})"


def main():
    cards = load_cards()
    assert len(cards) == 227, f"카드 수가 예상과 다르다: {len(cards)}"

    common_cards = [c for c in cards if COMMON_DOC_TYPE in c.get("doc_types", [])]

    # 출력 디렉터리를 비우고 다시 만든다 — 스크립트가 만든 파일만 남긴다.
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    genre_counts = {}
    genre_cards_by_slug = {}
    for doc_type, display_name, slug in GENRES:
        genre_cards = [c for c in cards if doc_type in c.get("doc_types", [])]
        genre_cards_by_slug[slug] = genre_cards
        genre_counts[slug] = len(genre_cards)

    files_written = []

    # references/common.md
    common_md = build_common_md(common_cards)
    files_written.append(write_file(os.path.join("references", "common.md"), common_md))

    # references/<slug>.md, references/checklist-<slug>.md
    for doc_type, display_name, slug in GENRES:
        genre_cards = genre_cards_by_slug[slug]
        genre_md = build_genre_md(doc_type, display_name, genre_cards, len(common_cards))
        files_written.append(write_file(os.path.join("references", f"{slug}.md"), genre_md))

        checklist_md = build_checklist_md(display_name, slug, genre_cards)
        files_written.append(
            write_file(os.path.join("references", f"checklist-{slug}.md"), checklist_md)
        )

    # SKILL.md
    skill_md = build_skill_md(cards, genre_counts, len(common_cards))
    skill_md_path = write_file("SKILL.md", skill_md)
    files_written.append(skill_md_path)

    # ---- 측정 보고 ----
    print("=" * 70)
    print(f"소스: {os.path.abspath(CARDS_PATH)} (카드 {len(cards)}장)")
    print(f"출력: {OUT_DIR}")
    print("=" * 70)

    report_rows = []
    largest = (None, -1)
    skill_md_lines = None
    for path in sorted(files_written):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        chars = len(text)
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        tokens_est = estimate_tokens(text)
        rel = os.path.relpath(path, OUT_DIR)
        report_rows.append((rel, chars, lines, tokens_est))
        if rel == "SKILL.md":
            skill_md_lines = lines
        if rel.startswith("references" + os.sep) and not os.path.basename(rel).startswith(
            "checklist-"
        ) and chars > largest[1]:
            largest = (rel, chars)

    print(f"{'파일':32} {'글자수':>8} {'줄수':>6} {'토큰(추정)':>10}")
    for rel, chars, lines, tokens_est in report_rows:
        print(f"{rel:32} {chars:8d} {lines:6d} {tokens_est:10d}")

    print("-" * 70)
    print(f"SKILL.md 줄수: {skill_md_lines} (500줄 미만 {'통과' if skill_md_lines < 500 else '위반'})")
    print(f"가장 큰 references 파일(체크리스트 제외): {largest[0]} ({largest[1]}자)")

    # ---- skills-ref validate ----
    print("-" * 70)
    validate_result = run_skills_ref_validate(OUT_DIR)
    print(f"skills-ref validate: {validate_result}")

    # ---- 프론트매터 자체 대조 ----
    print("-" * 70)
    name, desc, problems = self_check_frontmatter(skill_md)
    print(f"name: {name!r} ({len(name)}자)")
    print(f"description: {len(desc)}자")
    if problems:
        print("프론트매터 위반:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("프론트매터 규칙(name 소문자·하이픈, description<=1024자) 통과")

    return {
        "files": [rel for rel, *_ in report_rows],
        "skill_md_lines": skill_md_lines,
        "largest_reference": largest,
        "validate_result": validate_result,
        "frontmatter_problems": problems,
    }


if __name__ == "__main__":
    result = main()
    if result["frontmatter_problems"]:
        sys.exit(1)
