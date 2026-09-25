#!/usr/bin/env python3
"""규칙 카드 예시 SVG v3 — 표본 문서 조각을 그리고, 규칙이 적용된 실제 자리에 동그라미·밑줄·번호를 찍고, 오른쪽에 '무엇이 고려됐나'를 번호별로 설명한다.
사용: render.py <cards.json> <fragments.json> <annotations.json> <outdir>  →  <outdir>/svg/<card_id>.svg + <outdir>/kinds.json
글자 폭은 widths.json(Noto Sans KR 실측, em 단위)으로 어림하고 각 줄에 textLength 를 박아 어떤 글꼴에서도 자리가 같게 한다."""
import json, sys, os, re, html, math
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 800, 450
# 색 — 주석 층(표시·배지·설명·딱지)은 문서지능 브랜드 토큰(workspace/ui-tokens.css)과 같은 값을 쓴다:
#   잉크 --ai-color-ink · 보조 --ai-color-muted · 선 --ai-color-line · 패널 --ai-color-agent-panel ·
#   표시 --ai-color-signal · 지킴 --ai-color-status-fg · 어긋남 --ai-color-issue(선)·--ai-color-issue-ink(글자).
# NAVY 만은 **표본 문서 자신의 색**(보고서·슬라이드 CSS 의 남색)이라 앱 토큰이 아니다 — 문서 조각을 그릴 때만 쓴다.
INK, SUB, LINE, SOFT, NAVY, ACC, OK, BAD, PAPER = '#101B33', '#5b6577', '#e7e9ee', '#f8f9fb', '#1F3864', '#1E67F0', '#267a68', '#E75757', '#FFFFFF'
BAD_INK = '#913F48'   # --ai-color-issue-ink(issue 60% + ink) — 흰 바탕 위 붉은 글자의 대비를 지킨다
FONT = "'Noto Sans KR','Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
# 700 이상 굵기는 앱 헤딩 글꼴(ui-tokens.css 의 self-host 'Noto Sans KR Display', 700-900 서브셋)을 먼저 쓴다 —
# 규칙마당 페이지 안에 인라인으로 들어가면 앱·랜딩과 같은 헤딩 얼굴이 된다. 그 아래 굵기에는 절대 안 붙인다.
FONT_HEAD = "'Noto Sans KR Display','Noto Sans KR','Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
esc = lambda s: html.escape(str(s if s is not None else ''), quote=True)
# ---------- 글자 폭 ----------
try: WID = json.load(open(os.path.join(HERE, 'widths.json'), encoding='utf-8'))
except Exception: WID = {}
DEF = {'hangul': 0.96, 'ascii_up': 0.68, 'ascii_low': 0.55, 'digit': 0.58, 'space': 0.26, 'punct': 0.32, 'cjk_punct': 0.5, 'sym': 0.9, 'brack': 0.45}
def cls(ch):
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F: return 'hangul'
    if ch.isupper() and o < 128: return 'ascii_up'
    if ch.islower() and o < 128: return 'ascii_low'
    if ch.isdigit(): return 'digit'
    if ch == ' ': return 'space'
    if ch in '<>[]{}': return 'brack'
    if ch in '·…「」『』、。': return 'cjk_punct'
    if o < 128: return 'punct'
    if 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF: return 'hangul'
    return 'sym'
def cw(ch, weight):
    wk = str(min((400, 500, 700, 800), key=lambda w: abs(w - weight)))
    t = WID.get(wk, {}); k = cls(ch)
    per = t.get(k, {}).get('per', {})
    if ch in per: return per[ch]
    return t.get(k, {}).get('avg', DEF[k])
def tw(s, size, weight=400): return sum(cw(ch, weight) for ch in s) * size
def wrap(s, width, size, weight=400, maxlines=None):
    """어절 단위로 접고, 한 어절이 폭을 넘으면 글자 단위로 자른다."""
    words = s.split(' '); lines = []; cur = ''
    for w in words:
        cand = (cur + ' ' + w) if cur else w
        if tw(cand, size, weight) <= width: cur = cand; continue
        if cur: lines.append(cur)
        cur = ''
        while tw(w, size, weight) > width:
            k = len(w)
            while k > 1 and tw(w[:k], size, weight) > width: k -= 1
            lines.append(w[:k]); w = w[k:]
        cur = w
    if cur: lines.append(cur)
    if maxlines and len(lines) > maxlines:
        lines = lines[:maxlines]; last = lines[-1]
        while tw(last + '…', size, weight) > width and len(last) > 1: last = last[:-1]
        lines[-1] = last + '…'
    return lines or ['']
# ---------- SVG 조각 ----------
class Canvas:
    def __init__(self): self.parts = []; self.hits = {}  # element_id -> dict(lines=[(text,x,y,size,weight,width)], box=(x,y,w,h), cells={})
    def add(self, s): self.parts.append(s)
    def text(self, x, y, s, size, weight=400, color=INK, anchor='start', opacity=1, ls=0, italic=False):
        if s == '': return 0
        width = tw(s, size, weight) + ls * max(0, len(s) - 1)
        ax = x if anchor == 'start' else (x - width / 2 if anchor == 'middle' else x - width)
        st = (f"font-family:{FONT_HEAD};" if weight >= 700 else '') + f'font-size:{size}px;font-weight:{weight};fill:{color}' + (f';letter-spacing:{ls}px' if ls else '') + (';font-style:italic' if italic else '') + (f';opacity:{opacity}' if opacity < 1 else '')
        self.add(f'<text x="{ax:.1f}" y="{y:.1f}" textLength="{width:.1f}" lengthAdjust="spacing" xml:space="preserve" style="{st}">{esc(s)}</text>')
        return width
    def rect(self, x, y, w, h, fill='none', stroke='none', sw=1, rx=0, dash='', opacity=1):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"' + (f' stroke-dasharray="{dash}"' if dash else '') + (f' opacity="{opacity}"' if opacity < 1 else '') + '/>')
    def line(self, x1, y1, x2, y2, stroke=INK, sw=1, dash=''):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"' + (f' stroke-dasharray="{dash}"' if dash else '') + ' stroke-linecap="round"/>')
    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">'
                f'<rect width="{W}" height="{H}" fill="{PAPER}"/>' + ''.join(self.parts) + '</svg>')
# ---------- 문서 조각 그리기 ----------
ST = {  # role: (size, weight, color, indent, marker)
    'title': (19, 800, INK, 0, ''), 'byline': (11.5, 400, SUB, 0, ''), 'heading': (14.5, 700, INK, 0, '□ '),
    'item1': (13.5, 700, INK, 0, '□ '), 'item2': (13, 400, INK, 16, '○ '), 'item3': (12, 400, '#333', 32, '- '),
    'caption': (12.5, 700, INK, 0, ''), 'source': (10.5, 400, SUB, 0, ''), 'note': (12, 400, SUB, 0, ''),
    'org': (19, 800, INK, 0, ''), 'sig': (16, 800, INK, 0, ''), 'cover_title': (22, 800, INK, 0, ''), 'cover_sub': (13, 400, SUB, 0, ''), 'cover_info': (11, 400, SUB, 0, ''),
    'kicker': (10.5, 700, NAVY, 0, ''), 'headline': (19, 800, INK, 0, ''), 'subhead': (12.5, 400, SUB, 0, ''), 'lead': (12.5, 400, INK, 0, ''),
    'slide_head': (16, 800, NAVY, 0, ''), 'attach': (13, 400, INK, 0, ''), 'endmark': (13, 400, INK, 0, ''), 'step': (13, 700, INK, 0, ''), 'ladder': (13, 700, INK, 0, ''),
}
def draw_fragment(cv, frag, px, py, pw, ph):
    """조각의 요소를 (px,py,pw,ph) 안에 위 → 아래로 그린다. 각 요소의 줄 위치를 cv.hits 에 남긴다."""
    els = frag['elements']; g = frag['genre']; part = frag['part']
    x, y = px + 22, py + 26; inner = pw - 44
    cover = any(e['role'] == 'cover_title' for e in els) and g == '발표 슬라이드'
    if cover:
        cv.rect(px, py, pw, 150, fill=NAVY); cv.rect(px + 22, py + 30, 36, 4, fill='#fff'); y = py + 66
    if any(e['role'] == 'margin' for e in els): return draw_margins(cv, frag, px, py, pw, ph)
    if els and els[0]['role'] == 'step': return draw_steps(cv, els, px, py, pw, ph)
    if any(e['role'] == 'box' for e in els): return draw_boxes(cv, frag, px, py, pw, ph)
    if any(e['role'] == 'th' for e in els): return draw_table(cv, frag, px, py, pw, ph)
    if any(e['role'] == 'row' for e in els): return draw_gongmun(cv, frag, px, py, pw, ph)
    if any(e['role'] == 'ladder' for e in els): return draw_ladder(cv, els, px, py, pw, ph)
    center_roles = {'title', 'byline', 'org', 'sig', 'cover_title', 'cover_sub', 'cover_info'} if g != '발표 슬라이드' else {'org', 'sig'}
    for k_, e in enumerate(els):
        r = e['role']; size, weight, color, ind, mk = ST.get(r, ST['lead']); op = 0.45 if e.get('faded') else 1
        if r == 'step':
            if cover: y = max(y, py + 166)
            draw_steps(cv, [z for z in els[k_:] if z['role'] == 'step'], px, y - 30, pw, ph); break
        if cover and r in ('cover_title', 'cover_sub', 'cover_info'): color = '#fff'; op = op if r == 'cover_title' else 0.8
        if r == 'summary':
            lines = wrap(e['text'], inner - 28, 13, 400, 3); h = len(lines) * 19 + 18
            cv.rect(x, y, inner, h, fill=SOFT, stroke=INK, sw=1.2, opacity=op); lines_meta = []
            for i, ln in enumerate(lines):
                yy = y + 14 + 15 + i * 19; w = cv.text(x + 14, yy, ln, 13, 400, INK, opacity=op); lines_meta.append((ln, x + 14, yy, 13, 400, w))
            cv.hits[e['id']] = dict(lines=lines_meta, box=(x, y, inner, h)); y += h + 12; continue
        if r == 'endmark':
            w = tw(e['text'], size, weight); cv.text(x + inner - w, y + size, e['text'], size, weight, color); cv.hits[e['id']] = dict(lines=[(e['text'], x + inner - w, y + size, size, weight, w)], box=(x + inner - w, y, w, size * 1.4)); y += size * 1.7; continue
        label = mk if r in ('heading', 'item1', 'item2', 'item3') and g not in ('시행문(공문)', '규정·내규', '보도자료') else ('' if r not in ('item1', 'item2', 'item3') else ('' if g == '시행문(공문)' else mk))
        if g == '시행문(공문)' and r in ('item1', 'item2'): label = ''
        if g in ('발표 슬라이드',) and r in ('item1', 'item2'): label = '• ' if r == 'item1' else '– '
        text = label + e['text']; lh = size * 1.55
        maxw = inner - ind; lines = wrap(text, maxw, size, weight, 3 if r not in ('lead',) else 4)
        anchor = 'middle' if r in center_roles else 'start'; lines_meta = []
        for i, ln in enumerate(lines):
            yy = y + size + i * lh; xx = (px + pw / 2) if anchor == 'middle' else x + ind
            lsv = 4 if r in ('org', 'sig') else 0; w = cv.text(xx, yy, ln, size, weight, color, anchor=anchor, opacity=op, ls=lsv)
            lx = xx - w / 2 if anchor == 'middle' else xx; lines_meta.append((ln, lx, yy, size, weight, w, lsv))
        h = len(lines) * lh; cv.hits[e['id']] = dict(lines=lines_meta, box=(min(l[1] for l in lines_meta), y, max(l[5] for l in lines_meta), h))
        y += h + (8 if r in ('title', 'headline', 'cover_title', 'org') else 4)
        if r == 'title' and g == '한 장 보고서': cv.line(px + 60, y + 6, px + pw - 60, y + 6, INK, 1.5); y += 12
        if y > py + ph - 10: break
def draw_margins(cv, frag, px, py, pw, ph):
    els = {e['id']: e for e in frag['elements']}
    pg_w, pg_h = 210, 297; gx, gy = px + (pw - pg_w) / 2 - 60, py + (ph - pg_h) / 2
    cv.rect(gx, gy, pg_w, pg_h, fill='#fff', stroke='#888', sw=1)
    mm = {k: (els[k].get('mm') or 20) for k in ('m_top', 'm_bottom', 'm_left', 'm_right')}
    sc = pg_w / 210
    ix, iy, iw, ih = gx + mm['m_left'] * sc, gy + mm['m_top'] * sc, pg_w - (mm['m_left'] + mm['m_right']) * sc, pg_h - (mm['m_top'] + mm['m_bottom']) * sc
    cv.rect(ix, iy, iw, ih, fill='#EEF2FA', stroke=NAVY, sw=1, dash='4 3')
    for k in range(6): cv.line(ix + 12, iy + 18 + k * 22, ix + iw - 12 - (k % 3) * 30, iy + 18 + k * 22, '#B8C0D0', 3)
    lab = {'m_top': (gx + pg_w / 2, gy + 12, 'middle'), 'm_bottom': (gx + pg_w / 2, gy + pg_h - 5, 'middle'), 'm_left': (gx + 3, gy + pg_h / 2, 'start'), 'm_right': (gx + pg_w - 3, gy + pg_h / 2, 'end')}
    for k, (lx, ly, an) in lab.items():
        e = els[k]; w0 = tw(e['text'], 9.5, 700); bx0 = lx if an == 'start' else (lx - w0 / 2 if an == 'middle' else lx - w0)
        cv.rect(bx0 - 3, ly - 9.5, w0 + 6, 12.5, fill='#fff'); w = cv.text(lx, ly, e['text'], 9.5, 700, NAVY, anchor=an)
        bx = bx0
        cv.hits[k] = dict(lines=[(e['text'], bx, ly, 9.5, 700, w)], box=(bx, ly - 10, w, 13))
    cv.hits['body'] = dict(lines=[], box=(ix, iy, iw, ih)); w = cv.text(ix + iw / 2, iy + ih / 2, '본문 판면', 11, 700, NAVY, anchor='middle', opacity=.7)
def draw_steps(cv, els, px, py, pw, ph):
    x, y = px + 22, py + 30; size = 13; rowh = 40
    for e in els:
        lab = str(e.get('n', ''))
        w = tw(e['text'], size, 700) + 42
        if x + w > px + pw - 22: x = px + 22; y += rowh + 8
        cv.rect(x, y, w, rowh, fill=SOFT, stroke=LINE, sw=1, rx=3); cv.rect(x + 8, y + 12, 16, 16, fill=NAVY, rx=3); cv.text(x + 16, y + 24, lab, 10.5, 700, '#fff', anchor='middle')
        tx = x + 32; ty = y + 25; cv.text(tx, ty, e['text'], size, 700, INK)
        cv.hits[e['id']] = dict(lines=[(e['text'], tx, ty, size, 700, w - 42)], box=(x, y, w, rowh), kind='step'); x += w + 10
def draw_boxes(cv, frag, px, py, pw, ph):
    els = frag['elements']; x, y = px + 22, py + 26
    for e in els:
        if e['role'] in ('slide_head', 'heading'): w = cv.text(x, y + 16, e['text'], 15, 800, NAVY); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + 16, 15, 800, w)], box=(x, y, w, 22)); y += 34
        if e['role'] == 'caption': w = cv.text(x, y + 12, e['text'], 11.5, 700, SUB); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + 12, 11.5, 700, w)], box=(x, y, w, 16)); y += 26
    boxes = [e for e in els if e['role'] == 'box']; n = len(boxes); gap = 48; bw = min(112, (pw - 44 - (n - 1) * gap) / max(1, n)); bh = 58
    bx = x
    for i, e in enumerate(boxes):
        cv.rect(bx, y, bw, bh, fill='#EEF3FF', stroke='#555', sw=1.2, rx=2)
        l1 = wrap(e['text'], bw - 12, 12.5, 700, 2); w = cv.text(bx + bw / 2, y + 22, l1[0], 12.5, 700, INK, anchor='middle')
        w2 = cv.text(bx + bw / 2, y + 42, e.get('sub', ''), 10, 400, SUB, anchor='middle')
        cv.hits[e['id']] = dict(lines=[(l1[0], bx + bw / 2 - w / 2, y + 22, 12.5, 700, w)], box=(bx, y, bw, bh), kind='box')
        if i < n - 1:
            cv.line(bx + bw + 8, y + bh / 2, bx + bw + gap - 12, y + bh / 2, NAVY, 1.5); cv.add(f'<polygon points="{bx+bw+gap-12:.1f},{y+bh/2-4:.1f} {bx+bw+gap-6:.1f},{y+bh/2:.1f} {bx+bw+gap-12:.1f},{y+bh/2+4:.1f}" fill="{NAVY}"/>')
            if e.get('edge'): cv.text(bx + bw + gap / 2 - 2, y + bh / 2 - 8, e['edge'], 8.5, 500, NAVY, anchor='middle')
        bx += bw + gap
    y += bh + 16
    for e in els:
        if e['role'] == 'note' and e['text']: ls = wrap(e['text'], pw - 44, 12, 400, 2); meta = []
        else: continue
        for i, ln in enumerate(ls): w = cv.text(x, y + 13 + i * 18, ln, 12, 400, SUB, italic=True); meta.append((ln, x, y + 13 + i * 18, 12, 400, w))
        cv.hits[e['id']] = dict(lines=meta, box=(x, y, pw - 44, 18 * len(ls))); y += 18 * len(ls) + 8
    for e in els:
        if e['role'] == 'source': w = cv.text(x, y + 12, e['text'], 10.5, 400, SUB); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + 12, 10.5, 400, w)], box=(x, y, w, 14))
def draw_table(cv, frag, px, py, pw, ph):
    els = frag['elements']; x, y = px + 22, py + 26; inner = pw - 44
    for e in els:
        if e['role'] in ('slide_head', 'heading', 'caption'):
            size, wt, col = (15, 800, NAVY) if e['role'] == 'slide_head' else (13, 700, INK)
            w = cv.text(x, y + size, e['text'], size, wt, col); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + size, size, wt, w)], box=(x, y, w, size * 1.5)); y += size * 1.5 + 10
    rows = [e for e in els if e['role'] in ('th', 'td')]
    if rows:
        ncol = max(len(r.get('cells') or [r['text']]) for r in rows); cwid = inner / ncol; rh = 27
        for r in rows:
            cells = r.get('cells') or [r['text']]; fill = '#D9D9D9' if r['role'] == 'th' else '#fff'; meta = []; cmap = {}
            for j, cell in enumerate(cells):
                cx = x + j * cwid; cv.rect(cx, y, cwid, rh, fill=fill, stroke='#333', sw=1)
                t = wrap(str(cell), cwid - 10, 12, 700 if r['role'] == 'th' else 400, 1)[0]; w = cv.text(cx + cwid / 2, y + 18, t, 12, 700 if r['role'] == 'th' else 400, INK, anchor='middle')
                meta.append((t, cx + cwid / 2 - w / 2, y + 18, 12, 400, w)); cmap[str(cell)] = (cx, y, cwid, rh)
            cv.hits[r['id']] = dict(lines=meta, box=(x, y, inner, rh), cells=cmap); y += rh
        y += 8
    for e in els:
        if e['role'] == 'source': w = cv.text(x, y + 12, e['text'], 10.5, 400, SUB); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + 12, 10.5, 400, w)], box=(x, y, w, 14))
def draw_gongmun(cv, frag, px, py, pw, ph):
    els = frag['elements']; x, y = px + 22, py + 22; inner = pw - 44
    for e in els:
        r = e['role']
        if r == 'org':
            w = cv.text(px + pw / 2, y + 22, e['text'], 20, 800, INK, anchor='middle', ls=5); cv.hits[e['id']] = dict(lines=[(e['text'], px + pw / 2 - w / 2, y + 22, 20, 800, w, 5)], box=(px + pw / 2 - w / 2, y, w, 30)); y += 44
        elif r == 'row':
            lab = e.get('label', ''); rh = 30; cv.line(x, y, x + inner, y, '#333', 1); cv.text(x + 6, y + 20, lab, 12.5, 700, INK)
            t = wrap(e['text'], inner - 100, 12.5, 400, 1)[0]; w = cv.text(x + 92, y + 20, t, 12.5, 400, INK); cv.hits[e['id']] = dict(lines=[(t, x + 92, y + 20, 12.5, 400, w)], box=(x + 88, y + 2, inner - 88, rh - 4)); y += rh
            if e is [z for z in els if z['role'] == 'row'][-1] or all(z['role'] != 'row' for z in els[els.index(e) + 1:]): cv.line(x, y, x + inner, y, '#333', 1)
        elif r in ('item1', 'item2'):
            size = 12.5; lines = wrap(e['text'], inner - (0 if r == 'item1' else 18), size, 400, 3); meta = []; y += 8
            for i, ln in enumerate(lines): yy = y + size + i * 19; xx = x + (0 if r == 'item1' else 18); w = cv.text(xx, yy, ln, size, 400, INK, opacity=(0.45 if e.get('faded') else 1)); meta.append((ln, xx, yy, size, 400, w))
            cv.hits[e['id']] = dict(lines=meta, box=(x, y, inner, 19 * len(lines))); y += 19 * len(lines)
        elif r == 'sig':
            y += 16; w = cv.text(px + pw / 2, y + 18, e['text'], 16, 800, INK, anchor='middle', ls=3); cv.hits[e['id']] = dict(lines=[(e['text'], px + pw / 2 - w / 2, y + 18, 16, 800, w, 3)], box=(px + pw / 2 - w / 2, y, w, 26)); y += 34
        elif r in ('attach', 'endmark'):
            if r == 'attach': w = cv.text(x, y + 16, e['text'], 12.5, 400, INK); cv.hits[e['id']] = dict(lines=[(e['text'], x, y + 16, 12.5, 400, w)], box=(x, y + 2, w, 18)); y += 22
            else: w = tw(e['text'], 12.5, 400); cv.text(x + inner - w, y + 16, e['text'], 12.5, 400, INK); cv.hits[e['id']] = dict(lines=[(e['text'], x + inner - w, y + 16, 12.5, 400, w)], box=(x + inner - w, y + 2, w, 18)); y += 22
        if y > py + ph - 8: break
def draw_ladder(cv, els, px, py, pw, ph):
    x, y = px + 22, py + 24
    for e in els:
        size = min(30, max(11, (e.get('pt') or 12) * 1.25)); y += size + 6
        w = cv.text(x, y, e['text'], size, 700, INK); cv.hits[e['id']] = dict(lines=[(e['text'], x, y, size, 700, w)], box=(x, y - size, w, size * 1.2)); y += 6
# ---------- 표시(동그라미·밑줄·번호) ----------
def span_boxes(hit, span):
    """span 이 놓인 줄별 (x,y,w,h) 목록. 표 셀은 셀 상자, 여러 줄에 걸치면 줄마다 하나."""
    if 'cells' in hit and span:
        parts = [q.strip() for q in span.split('|')]; boxes = []
        for q in parts:
            for cell, box in hit['cells'].items():
                if q and (q == cell or q in cell): boxes.append(box); break
        if boxes:
            x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes); x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
            return [(x0, y0, x1 - x0, y1 - y0)]
    lines = hit['lines']
    if not span or not lines: return [hit['box']]
    full = ''; idx = []
    for li, ln in enumerate(lines):
        if li > 0: full += ' '; idx.append(None)
        for ci in range(len(ln[0])): full += ln[0][ci]; idx.append((li, ci))
    p = full.find(span)
    if p >= 0: pend = p + len(span) - 1
    else:
        comp = ''.join(ch for ch in full if ch != ' '); m2 = [i for i, ch in enumerate(full) if ch != ' ']; s2 = span.replace(' ', '')
        q = comp.find(s2)
        if q < 0 or not s2: return [hit['box']]
        p = m2[q]; pend = m2[q + len(s2) - 1]
    segs = {}
    for k in range(p, pend + 1):
        m = idx[k]
        if m is None: continue
        li, ci = m; segs.setdefault(li, [ci, ci]); segs[li][1] = ci
    out = []
    for li, (c0, c1) in sorted(segs.items()):
        ln = lines[li]; text, x, y, size, weight, w = ln[:6]; ls = ln[6] if len(ln) > 6 else 0
        pre = tw(text[:c0], size, weight) + ls * c0; sw = tw(text[c0:c1 + 1], size, weight) + ls * (c1 - c0)
        out.append((x + pre, y - size * 0.95, sw, size * 1.22))
    return out or [hit['box']]
def union(boxes):
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes); x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
    return (x0, y0, x1 - x0, y1 - y0)
def badge(cv, x, y, n, color=ACC, r=7):
    for (ox, oy) in cv.__dict__.setdefault('badges', []):
        if abs(ox - x) < 16 and abs(oy - y) < 16: x, y = x + 18, y - 3
    x = min(max(x, 12), W - 12); cv.badges.append((x, y))
    cv.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#fff" stroke-width="2"/>'); cv.text(x, y + 3.3, str(n), 9.5, 700, '#fff', anchor='middle')
def mark(cv, boxes, kind, n, color=ACC, tight=False):
    """boxes: span_boxes 결과. 반환: 배지 좌표."""
    if len(boxes) > 1 and kind == 'circle': kind = 'bracket'
    x, y, w, h = union(boxes)
    if kind == 'circle' and w > 120: kind = 'bracket'
    if kind == 'circle' or (kind == 'underline' and w < 50):
        rx, ry = w / 2 + 5, h / 2 + 4; cx, cy = x + w / 2, y + h / 2
        cv.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="{color}" stroke-width="2.2" transform="rotate(-2 {cx:.1f} {cy:.1f})"/>')
        bx, by = cx + rx + 3, cy - ry
    elif kind == 'underline':
        for (x1, y1, w1, h1) in boxes: cv.line(x1, y1 + h1 + 1, x1 + w1 + 1, y1 + h1 + 1, color, 2.4)
        lx, ly, lw, lh = boxes[-1]; bx, by = lx + lw + 9, ly + lh + 1
    else:
        pad = 3 if tight else 6
        cv.rect(x - pad, y - pad, w + pad * 2, h + pad * 2, fill='none', stroke=color, sw=1.8, rx=6, dash='6 4'); bx, by = x + w + pad + 6, y - pad
    badge(cv, bx, by, n, color); return bx, by
# ---------- 카드 하나 ----------
FITLAB = {'지킴': ('규칙대로 ✓', OK), '자리만': ('이 자리를 본다', SUB), '어긋남': ('표본이 어긋남 ✗', BAD_INK)}
def render_card(card, frag, ann):
    cv = Canvas(); g, part, mode = frag['genre'], frag['part'], frag['mode']
    src = f"표본 『{frag['sample']}』" if frag.get('sample') else ('카드의 전·후 예' if mode == '전후' else ('규칙 값으로 그린 판면 도식' if part == '여백·판면' else ('규칙 값으로 그린 글자 크기 사다리' if part == '글꼴·크기' else ("카드의 '후' 구성" if mode == '카드 예시' else '규칙 요약'))))
    if frag.get('borrowed'): src += f"({frag['borrowed']}에서 빌림)"
    cv.text(24, 20, g, 11, 700, INK); wlab = tw(g, 11, 700); cv.text(24 + wlab + 6, 20, f"· {part} · {src}", 11, 400, SUB)
    fl, fc = FITLAB.get(ann.get('fit', '자리만'), FITLAB['자리만']); fw = tw(fl, 10.5, 700) + 16
    cv.rect(W - 24 - fw, 8, fw, 18, fill='#fff', stroke=fc, sw=1, rx=9); cv.text(W - 24 - fw / 2, 21, fl, 10.5, 700, fc, anchor='middle')
    if mode == '전후':
        for k, (key, col, sym) in enumerate((('before', BAD, '전'), ('after', OK, '후'))):
            px = 24 + k * 384; pw = 368; py, ph = 36, 214
            cv.rect(px, py, pw, ph, fill='#fff', stroke=LINE, sw=1, rx=4); cv.rect(px + 14, py + 12, 30, 20, fill=col, rx=3); cv.text(px + 29, py + 26, sym, 12, 700, '#fff', anchor='middle')
            size = 16; lines = wrap(frag.get(key, ''), pw - 40, size, 500, 6); meta = []
            for i, ln in enumerate(lines): yy = py + 64 + i * 26; w = cv.text(px + 20, yy, ln, size, 500, INK); meta.append((ln, px + 20, yy, size, 500, w))
            hit = dict(lines=meta, box=(px + 20, py + 46, pw - 40, 26 * len(lines)))
            span = ann.get(f'{key}_span') or ''; lab = ann.get(f'{key}_label') or ''
            if span:
                bxs = span_boxes(hit, span); kind = 'circle' if len(span) <= 14 else 'underline'; mark(cv, bxs, kind, '✗' if key == 'before' else '○', col)
            ly = py + ph + 22; ls = wrap(lab, pw - 30, 12.5, 500, 2)
            for i, ln in enumerate(ls): cv.text(px + 14, ly + i * 19, ('✗ ' if key == 'before' else '○ ') + ln if i == 0 else ln, 12.5, 500, BAD_INK if key == 'before' else col)
    else:
        px, py, pw, ph = 24, 36, 504, 350
        cv.rect(px, py, pw, ph, fill='#fff', stroke=LINE, sw=1, rx=4)
        probe = Canvas(); draw_fragment(probe, frag, px, py, pw, ph)
        bottom = max([b['box'][1] + b['box'][3] for b in probe.hits.values()] or [py + ph]); dy = 0
        if not (any(e['role'] == 'margin' for e in frag['elements']) or (frag['genre'] == '발표 슬라이드' and any(e['role'] == 'cover_title' for e in frag['elements']))):
            dy = max(0, min(110, (py + ph - bottom - 26) / 2))
        cid = 'doc-' + re.sub(r'[^A-Za-z0-9_-]', '', card['card_id'])   # 한 페이지에 여러 장이 인라인으로 들어가도 id 가 안 겹치게
        cv.add(f'<clipPath id="{cid}"><rect x="24" y="36" width="504" height="350"/></clipPath><g clip-path="url(#{cid})">'); draw_fragment(cv, frag, px, py + dy, pw, ph - dy); cv.add('</g>')
        # 표시와 설명
        cx0, cy = 560, 44; targets = [t for t in ann.get('targets', []) if t.get('element_id') in cv.hits][:3]
        cv.text(cx0, cy + 6, '무엇이 고려됐나', 11, 700, SUB); cy += 22
        for i, t in enumerate(targets, 1):
            hit = cv.hits[t['element_id']]; boxes = span_boxes(hit, t.get('span') or '')
            kind = t.get('mark') or ('circle' if (t.get('span') and len(t['span']) <= 14) else 'bracket')
            tight = hit.get('kind') in ('box', 'step')
            if tight: kind = 'bracket'
            elif kind == 'bracket' and len(hit['lines']) <= 1 and (t.get('span') or '') == '' and hit['box'][2] < 120: kind = 'circle'
            col = BAD if str(t.get('label', '')).startswith('✗') else ACC
            bx, by = mark(cv, boxes, kind, i, col, tight=tight)
            lines = wrap(t.get('label', ''), 200, 12.5, 500, 3); h = 19 * len(lines) + 14
            badge(cv, cx0 + 10, cy + 12, i, col)
            for j, ln in enumerate(lines): cv.text(cx0 + 26, cy + 17 + j * 19, ln, 12.5, 500, INK)
            cv.line(bx + 9, by, 540, by, col, 1, dash='3 3'); cv.line(540, by, cx0 + 1, cy + 12, col, 1, dash='3 3')
            cy += h
    cap = ann.get('caption') or ''; rule = card.get('rule') or ''
    y = 406; lines = wrap(cap, W - 48, 13, 500, 2)
    for ln in lines: cv.text(24, y, ln, 13, 500, INK); y += 18
    rl = wrap('규칙  ' + rule, W - 48, 11, 400, 1)[0]; cv.text(24, min(y + 2, 444), rl, 11, 400, SUB)
    return cv.svg()
def main():
    cards = json.load(open(sys.argv[1], encoding='utf-8')); frags = json.load(open(sys.argv[2], encoding='utf-8')); anns = json.load(open(sys.argv[3], encoding='utf-8')); out = sys.argv[4]
    os.makedirs(os.path.join(out, 'svg'), exist_ok=True); kinds = {}; miss = []
    for c in cards:
        f = frags[c['card_id']]; a = anns.get(c['card_id']) or {'fit': '자리만', 'targets': [], 'caption': ''}
        if not anns.get(c['card_id']): miss.append(c['card_id'])
        open(os.path.join(out, 'svg', c['card_id'] + '.svg'), 'w', encoding='utf-8').write(render_card(c, f, a)); kinds[c['card_id']] = dict(mode=f['mode'], fit=a.get('fit'), n=len(a.get('targets', [])))
    json.dump(kinds, open(os.path.join(out, 'kinds.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('svg', len(kinds), 'missing ann', len(miss), miss[:5])
if __name__ == '__main__': main()
