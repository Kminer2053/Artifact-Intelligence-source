#!/usr/bin/env python3
"""규칙마당(/rules/) 산출물 빌드 — 카드·사례 데이터, 카드별 예시 SVG, 경량 규칙 스킬 zip.

원천은 research/rules-commons/ 에 있다(규칙 카드 정본 사본·주석·렌더러·스킬 빌더). 이 스크립트는
그것을 서빙용으로 굽기만 한다. index.html 은 손으로 쓰는 화면 소스라 여기서 건드리지 않는다.

    python3 rules/build.py                 # 오늘 날짜를 판(version)으로
    python3 rules/build.py --version 2026.09.25

만드는 것 (전부 rules/ 아래, serve.py GET 화이트리스트와 1:1):
  cards.json · cases.json                  규칙 카드 227장·사례 20건(원천 그대로 복사)
  img/<card_id>.svg                        카드별 주석 예시(v3/render.py — 브랜드 토큰 색)
  artifact-intelligence-rules.zip          경량 규칙 스킬(Agent Skills 스펙, 폴더째 한 벌)
zip 은 결정적으로 만든다(파일 순서 고정·시각 고정) — 같은 원천이면 바이트가 같다.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # …/rules
ROOT = HERE.parent                                     # …/skill/artifact-intelligence
SRC = ROOT / "research" / "rules-commons"
SKILL_NAME = "artifact-intelligence-rules"
ZIP_TIME = (2026, 1, 1, 0, 0, 0)                       # zip 안 파일 시각 고정(결정성)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=time.strftime("%Y.%m.%d"))
    a = ap.parse_args()

    # 1) 카드·사례
    for n in ("cards.json", "cases.json"):
        shutil.copyfile(SRC / n, HERE / n)
    cards = json.load(open(HERE / "cards.json", encoding="utf-8"))
    cases = json.load(open(HERE / "cases.json", encoding="utf-8"))

    # 2) 예시 SVG — 렌더러가 임시 폴더에 굽고, 여기로 옮긴다(옛 그림은 비운다)
    with tempfile.TemporaryDirectory() as t:
        r = subprocess.run([sys.executable, str(SRC / "v3" / "render.py"), str(HERE / "cards.json"),
                            str(SRC / "v3" / "fragments.json"), str(SRC / "v3" / "annotations.json"), t],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout, r.stderr); sys.exit("✗ 예시 SVG 렌더 실패")
        img = HERE / "img"
        shutil.rmtree(img, ignore_errors=True); img.mkdir()
        n_svg = 0
        for f in sorted(Path(t, "svg").glob("*.svg")):
            shutil.copyfile(f, img / f.name); n_svg += 1
    missing = [c["card_id"] for c in cards if not (HERE / "img" / f"{c['card_id']}.svg").exists()]
    if missing:
        sys.exit(f"✗ 예시가 없는 카드 {len(missing)}장: {missing[:5]}")

    # 3) 경량 스킬 — 빌더가 lightskill/<이름>/ 에 굽는다
    env = dict(os.environ, RULES_SKILL_VERSION=a.version)
    r = subprocess.run([sys.executable, str(SRC / "lightskill" / "build_skill.py")],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(r.stdout, r.stderr); sys.exit("✗ 경량 스킬 빌드 실패")
    skill_dir = SRC / "lightskill" / SKILL_NAME
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file())
    if not (skill_dir / "SKILL.md").exists():
        sys.exit("✗ SKILL.md 가 없다")

    # 4) zip — 폴더째(<이름>/SKILL.md …). claude.ai 업로드는 폴더 이름이 스킬 이름과 같아야 한다.
    z = HERE / f"{SKILL_NAME}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            info = zipfile.ZipInfo(f"{SKILL_NAME}/{p.relative_to(skill_dir).as_posix()}", ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())

    print(f"✓ rules/ — 카드 {len(cards)} · 사례 {len(cases)} · 예시 SVG {n_svg} · "
          f"스킬 {len(files)}파일 → {z.name} {z.stat().st_size // 1024} KB (판 {a.version})")


if __name__ == "__main__":
    main()
