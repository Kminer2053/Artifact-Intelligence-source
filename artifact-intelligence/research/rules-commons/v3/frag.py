#!/usr/bin/env python3
"""v3 조각 추출 — 카드마다 그릴 '표본 문서 조각'을 요소 목록(id·role·text)으로 뽑는다. 주석(동그라미·설명)은 뒤 단계가 element_id/span 으로 가리킨다."""
import json, sys, re
from pathlib import Path
strip = lambda s: re.sub(r'</?[A-Za-z][^>]*>', '', str(s or ''))
def clean(s, n=None):
    s = re.sub(r'\s+', ' ', strip(s)).strip(); return s if n is None or len(s) <= n else s[:n - 1] + '…'
# 표본은 이 폴더의 samples.json(합성·익명 ○○공사) 한 곳에서만 읽는다.
_S = json.load(open(Path(__file__).resolve().parent / 'samples.json', encoding='utf-8'))
S1 = _S['onepage']; SG = _S['gongmun']; SF = _S['fullreport']; SR = _S['regulation']; SP_ = _S['press']; SS = _S['slides']
NAME = {'한 장 보고서': S1['title'], '시행문(공문)': SG['제목'], '풀버전 보고서': SF['표지']['제목'].replace('\n', ' '), '규정·내규': SR['제명'], '보도자료': SP_['제목'], '발표 슬라이드': SS['표지']['제목']}
def genre_of(c):
    for g in ('발표 슬라이드', '시행문(공문)', '보도자료', '규정·내규', '풀버전 보고서', '한 장 보고서'):
        if g in (c.get('doc_types') or []): return g
    return '한 장 보고서'
E = lambda i, role, text, **k: dict(id=i, role=role, text=clean(text), **k)
def items_of(g):
    if g == '시행문(공문)': return [(x.get('level', 1), x.get('text', '')) for x in SG['본문']]
    if g == '풀버전 보고서':
        out = []
        for bl in SF['요약']['블록'][:1]:
            for it in bl['항목']: out.append((1, it['text'])); out += [(2, s) for s in it.get('세부', [])]
        return out
    if g == '보도자료': return [(x.get('level', 1), x.get('text', '')) for x in SP_['본문']]
    if g == '규정·내규': return [(1 if x.get('level') == '조' else 2, (f"제N조({x.get('제목')}) " if x.get('level') == '조' else '') + x.get('text', '')) for x in SR['본문'] if x.get('text')]
    if g == '발표 슬라이드':
        for s in SS['슬라이드']:
            if s.get('레이아웃') == '본문': return [(x.get('level', 1), x.get('text', '')) for x in s['항목']]
    sec = S1['sections'][0]
    return [(x.get('level', 2), strip(x.get('html', ''))) for x in sec['items']]
def ladder(g, n=4, pre='i'):
    out = []
    for k, (lv, t) in enumerate(items_of(g)[:n]):
        lv = int(lv) if str(lv).isdigit() else 1; lv = max(1, min(3, lv))
        out.append(E(f'{pre}{k+1}', f'item{lv}', t, level=lv))
    return out
def outline_of(g):
    if g == '시행문(공문)': return ['두문(기관명·수신·제목)', '본문', '붙임', '발신명의', '수신자란']
    if g == '풀버전 보고서': return ['표지', '요약'] + [c['제목'] for c in SF['장']][:5]
    if g == '보도자료': return ['제목', '부제', '리드'] + [x['text'] for x in SP_['본문'] if x.get('level') == 1][:3]
    if g == '규정·내규': return ['제명'] + [f"제N장 {x.get('제목')}" for x in SR['본문'] if x.get('level') == '장'][:4] + ['부칙']
    if g == '발표 슬라이드': return ['표지'] + [s.get('레이아웃', '') for s in SS['슬라이드']][:7]
    return ['제목', '요약박스'] + [s['heading'] for s in S1['sections']][:5] + ['붙임']
def onepage_head(faded_summary=False):
    return [E('title', 'title', S1['title']), E('byline', 'byline', S1['byline']), E('summary', 'summary', S1['summary'], faded=faded_summary)]
def onepage_doc():
    out = onepage_head(); k = 0
    for s in S1['sections'][:2]:
        out.append(E(f'h{k+1}', 'heading', s['heading']))
        for j, it in enumerate(s['items'][:2]): out.append(E(f'h{k+1}i{j+1}', f'item{it.get("level",2)}', strip(it['html']), level=it.get('level', 2)))
        k += 1
    return out
def slide_table():
    for s in SS['슬라이드']:
        if s.get('레이아웃') == '표': return s
def slide_fig():
    for s in SS['슬라이드']:
        if s.get('레이아웃') == '도식': return s
def table_elems(tb, head_id='th'):
    hdr = tb.get('header') or []; out = [E(head_id, 'th', ' | '.join(hdr), cells=hdr)]
    for i, r in enumerate(tb.get('rows', [])[:4]): out.append(E(f'r{i+1}', 'td', ' | '.join(r), cells=r))
    return out
def frag(c):
    part, g = c['part'], genre_of(c); b, a = c.get('before') or '', c.get('after') or ''
    F = dict(card_id=c['card_id'], genre=g, part=part, mode='예시', sample=NAME[g], borrowed=None, elements=[])
    el = F['elements']
    if b and a and part != '문서 전체 구성':
        F['mode'] = '전후'; F['before'] = clean(b); F['after'] = clean(a); F['sample'] = None; return F
    if part == '제목·표지':
        if g == '발표 슬라이드': t = SS['표지']; el += [E('cover_title', 'cover_title', t['제목']), E('cover_sub', 'cover_sub', t['부제']), E('cover_info', 'cover_info', t['발표정보'])]
        elif g == '보도자료': el += [E('kicker', 'kicker', f"보도자료 · {SP_['기관명']}"), E('headline', 'headline', SP_['제목']), E('subhead', 'subhead', SP_['부제'])]
        elif g == '시행문(공문)': el += [E('org', 'org', SG['기관명']), E('to', 'row', SG['수신'], label='수신'), E('subject', 'row', SG['제목'], label='제목')]
        elif g == '풀버전 보고서': t = SF['표지']; el += [E('cover_sub', 'cover_sub', t['부제']), E('cover_title', 'cover_title', t['제목'].replace('\n', ' ')), E('cover_info', 'cover_info', f"{t['보고일']} · {t['기관명']} · {t['부서명']}")]
        elif g == '규정·내규': el += [E('title', 'title', SR['제명']), E('byline', 'byline', f"{SR['규정번호']} · {SR['기관명']}"), E('h1', 'heading', '제1조(목적)'), E('h1i1', 'item2', next(x['text'] for x in SR['본문'] if x.get('level') == '조'), level=2)]
        else: el += onepage_head(faded_summary=True)
        return F
    if part == '요약(두괄)':
        if g == '풀버전 보고서': bl = SF['요약']['블록'][0]; el += [E('h1', 'heading', bl['제목'])] + [E(f'i{i+1}', 'item2', it['text'], level=2) for i, it in enumerate(bl['항목'][:3])]
        elif g == '보도자료': el += [E('headline', 'headline', SP_['제목']), E('lead', 'lead', SP_['리드'])]
        elif g == '시행문(공문)': el += [E('subject', 'row', SG['제목'], label='제목'), E('i1', 'item1', SG['본문'][0]['text'], level=1), E('i2', 'item1', SG['본문'][1]['text'], level=1)]
        elif g == '발표 슬라이드':
            s = next(x for x in SS['슬라이드'] if x.get('레이아웃') == '본문'); el += [E('head', 'slide_head', s['헤드메시지'])] + [E(f'i{i+1}', f'item{it.get("level",1)}', it['text'], level=it.get('level', 1)) for i, it in enumerate(s['항목'][:3])]
        elif g == '규정·내규': el += [E('title', 'title', SR['제명']), E('h1', 'heading', '제1조(목적)'), E('h1i1', 'item2', next(x['text'] for x in SR['본문'] if x.get('level') == '조'), level=2)]
        else: el += onepage_head() + [E('h1', 'heading', S1['sections'][0]['heading'], faded=True)]
        return F
    def slide_src():
        s_ = next((x for x in SS['슬라이드'] if x.get('레이아웃') == '본문'), None)
        return [E('src', 'source', f"출처: {s_['출처']}")] if s_ and s_.get('출처') else []
    if part == '본문 글머리·위계':
        el += [E('title', 'title', NAME[g], faded=True)] + ladder(g, 4) + (slide_src() if g == '발표 슬라이드' else []); return F
    if part == '표':
        if g == '규정·내규': bt = SR['별표'][0]; el += [E('cap', 'caption', f"[별표 {bt['번호']}] {bt['제목']}")] + table_elems(bt['표'])
        else:
            s = slide_table(); el += [E('head', 'slide_head' if g == '발표 슬라이드' else 'heading', s['헤드메시지'] if g == '발표 슬라이드' else s['표']['캡션'])] + table_elems(s['표']) + [E('src', 'source', f"출처: {s['출처']}")]
            if g != '발표 슬라이드': F['borrowed'] = '발표 슬라이드'; F['sample'] = NAME['발표 슬라이드']
        return F
    if part == '그림·도식·차트':
        s = slide_fig(); st = s['도식']['단계']
        el += [E('head', 'slide_head' if g == '발표 슬라이드' else 'heading', s['헤드메시지']), E('cap', 'caption', s['도식']['캡션'])] + [E(f'b{i+1}', 'box', x['라벨'], sub=x.get('주체', ''), edge=x.get('전이', '')) for i, x in enumerate(st[:4])] + [E('impl', 'note', s['도식'].get('함의', '')), E('src', 'source', f"출처: {s['출처']}")]
        if g != '발표 슬라이드': F['borrowed'] = '발표 슬라이드'; F['sample'] = NAME['발표 슬라이드']
        return F
    if part == '글꼴·크기':
        src = (c.get('rule') or '') + ' ' + (c.get('source_excerpt') or ''); pairs = []; seen = set()
        for lab, pt in re.findall(r'([가-힣A-Za-z()·/]{1,12})\s*(\d+(?:\.\d+)?)\s*pt', src):
            if (lab, pt) in seen: continue
            seen.add((lab, pt)); pairs.append((lab.strip('·/'), float(pt)))
        if pairs:
            F['mode'] = '규칙 요약'; el += [E(f'f{i+1}', 'ladder', f'{lab} {pt:g}pt', pt=pt, label=lab) for i, (lab, pt) in enumerate(sorted(pairs[:5], key=lambda x: -x[1]))]
        else:
            el += [E('title', 'title', NAME[g], role_label='제목'), E('h1', 'heading', S1['sections'][0]['heading'] if g == '한 장 보고서' else outline_of(g)[2], role_label='소제목')] + [dict(x, role_label='본문') for x in ladder(g, 2)]
        return F
    if part == '여백·판면':
        src = (c.get('rule') or '') + ' ' + (c.get('source_excerpt') or '')
        side = {}
        SIDES = {'좌우': 'lr', '양옆': 'lr', '상하': 'tb', '위아래': 'tb', '상': 't', '위': 't', '위쪽': 't', '하': 'b', '아래': 'b', '아래쪽': 'b', '좌': 'l', '왼쪽': 'l', '왼': 'l', '우': 'r', '오른쪽': 'r', '오른': 'r'}
        S = '좌우|상하|위아래|양옆|오른쪽|왼쪽|위쪽|아래쪽|상|하|좌|우|위|아래'
        msrc = ' '.join(sn for sn in re.split(r'(?<=[.。])\s+|\n', src) if any(w in sn for w in ('여백', '용지', '판면', '마진')))
        for grp, val in re.findall(r'((?:' + S + r')(?:\s*[·,]\s*(?:' + S + r'))*)\s*(?:여백은|여백|은|는)?\s*(?:실효)?\s*(\d+(?:\.\d+)?)\s*mm', msrc):
            v = float(val)
            for lab in re.split(r'\s*[·,]\s*', grp):
                for k in SIDES.get(lab, ''): side.setdefault(k, v)
        mm = [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*mm', msrc)][:4]
        if not side and not mm and g == '시행문(공문)' and any(w in (c.get('rule') or '') for w in ('두문', '결문', '기관명', '발신명의', '수신자란', '결재')):
            el += [E('org', 'org', SG['기관명']), E('to', 'row', SG['수신'], label='수신'), E('via', 'row', SG['경유'] or '', label='(경유)'), E('subject', 'row', SG['제목'], label='제목'), E('sig', 'sig', SG['발신명의']), E('cc', 'row', SG['수신자란'], label='수신자')]
            F['part_note'] = '두문·결문'; return F
        if not side and not mm and g == '규정·내규':
            el += [E('title', 'title', NAME[g], faded=True)] + ladder(g, 4); F['sample'] = NAME[g]; F['mode'] = '예시'; F['part_note'] = '조문 들여쓰기'; return F
        F['mode'] = '규칙 요약' if not mm else '예시'; F['sample'] = None
        if side:
            t = side.get('t'); bt = side.get('b'); l = side.get('l'); r = side.get('r')
            pass  # 규칙이 말하지 않은 변은 숫자 없이 둔다
        elif len(mm) >= 4: t, r, bt, l = mm
        elif mm: t = r = bt = l = mm[0]
        else: t = r = bt = l = None
        el += [E('m_top', 'margin', f'상 {t:g}mm' if t else '위 여백', side='top', mm=t), E('m_bottom', 'margin', f'하 {bt:g}mm' if bt else '아래 여백', side='bottom', mm=bt), E('m_left', 'margin', f'좌 {l:g}mm' if l else '왼 여백', side='left', mm=l), E('m_right', 'margin', f'우 {r:g}mm' if r else '오른 여백', side='right', mm=r), E('body', 'bodyarea', '본문 판면')]
        return F
    if part == '붙임·별첨':
        at = SG['붙임'] if g in ('시행문(공문)', '한 장 보고서', '풀버전 보고서', '규정·내규', '발표 슬라이드') else SP_['붙임']
        if g not in ('시행문(공문)', '보도자료'): F['borrowed'] = '시행문(공문)'; F['sample'] = NAME['시행문(공문)']
        el += [E('last', 'item1', SG['본문'][-1]['text'] if g != '보도자료' else SP_['본문'][-1]['text'], faded=True, level=1)] + [E(f'at{i+1}', 'attach', f'붙임 {i+1}. {x}' if i == 0 else f'{i+1}. {x}') for i, x in enumerate(at[:2])] + [E('end', 'endmark', '끝.')]
        return F
    if part == '수신·발신·결재선':
        el += [E('org', 'org', SG['기관명']), E('to', 'row', SG['수신'], label='수신'), E('via', 'row', SG['경유'] or '', label='(경유)'), E('subject', 'row', SG['제목'], label='제목'), E('sig', 'sig', SG['발신명의']), E('cc', 'row', SG['수신자란'], label='수신자')]
        if g != '시행문(공문)': F['borrowed'] = '시행문(공문)'; F['sample'] = NAME['시행문(공문)']
        return F
    if part == '문장 표현':
        el += [E('title', 'title', NAME[g], faded=True)] + ladder(g, 3) + (slide_src() if g == '발표 슬라이드' else []); F['mode'] = '표본 문장'; return F
    if part == '문서 전체 구성':
        if '→' in a: steps = [s.strip() for s in re.split(r'→', re.sub(r'\([^)]*\)', '', a)) if s.strip()][:7]; F['sample'] = None; F['mode'] = '카드 예시'
        else: steps = outline_of(g)[:7]
        el += [E(f's{i+1}', 'step', s, n=i + 1) for i, s in enumerate(steps)]; return F
    # 판정·유형
    if g == '한 장 보고서': el += onepage_doc()
    elif g == '발표 슬라이드': t = SS['표지']; el += [E('cover_title', 'cover_title', t['제목']), E('cover_sub', 'cover_sub', t['부제'])] + [E(f'sl{i+1}', 'step', f"{s.get('레이아웃')}: {clean(s.get('헤드메시지'), 30)}", n=i + 1) for i, s in enumerate(SS['슬라이드'][:5])]
    elif g == '시행문(공문)': el += [E('org', 'org', SG['기관명']), E('subject', 'row', SG['제목'], label='제목')] + [E(f'i{i+1}', 'item1', x['text'], level=1) for i, x in enumerate(SG['본문'][:2])]
    elif g == '풀버전 보고서': t = SF['표지']; el += [E('cover_title', 'cover_title', t['제목'].replace('\n', ' ')), E('cover_sub', 'cover_sub', t['부제'])] + [E(f'ch{i+1}', 'step', ch['제목'], n=i + 1) for i, ch in enumerate(SF['장'][:5])]
    elif g == '보도자료': el += [E('headline', 'headline', SP_['제목']), E('subhead', 'subhead', SP_['부제']), E('lead', 'lead', SP_['리드'])]
    else: el += [E('title', 'title', SR['제명']), E('h1', 'heading', '제1조(목적)'), E('h1i1', 'item2', next(x['text'] for x in SR['본문'] if x.get('level') == '조'), level=2)]
    return F
if __name__ == '__main__':
    cards = json.load(open(sys.argv[1], encoding='utf-8'))
    out = {c['card_id']: frag(c) for c in cards}
    json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(out), Counter(v['mode'] for v in out.values()), 'borrowed', sum(1 for v in out.values() if v['borrowed']))
