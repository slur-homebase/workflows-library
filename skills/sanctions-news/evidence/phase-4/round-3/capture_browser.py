"""Offline Chrome round-3 proof. Installed browser + stdlib CDP; no server/install."""

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PAGE = OUT / 'dashboard.html'
SPEC = importlib.util.spec_from_file_location('round3_previous_browser', OUT / 'support/round-2/capture_browser.py')
assert SPEC and SPEC.loader
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
browser = previous.previous.browser
evaluate, click, ready = previous.evaluate, previous.click, previous.ready


def open_page(chrome, page, width):
    target = chrome.call('Target.createTarget', {'url': 'about:blank'})['targetId']
    session = chrome.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
    for domain in ('Page', 'Network', 'Runtime'):
        chrome.call(domain + '.enable', session=session)
    chrome.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*']}, session)
    chrome.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 900,
                'deviceScaleFactor': 1, 'mobile': False}, session)
    chrome.call('Page.navigate', {'url': page.as_uri()}, session)
    ready(chrome, session)
    evaluate(chrome, session, 'localStorage.clear(); decisions=[]; articleDecisions=[]; linkDecisions=[]; drawTimeline()')
    return target, session


def screenshot(chrome, session, sid, width, kind):
    evaluate(chrome, session, 'window.scrollTo(0,0)')
    height = 900 if kind == 'top' else evaluate(chrome, session, 'document.documentElement.scrollHeight')
    raw = base64.b64decode(chrome.call('Page.captureScreenshot', {
        'format': 'png', 'captureBeyondViewport': True,
        'clip': {'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1}}, session)['data'])
    assert raw[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', raw[16:24]) == (width, height)
    path = OUT / f'{sid}-{width}-{kind}.png'
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'dimensions': [width, height],
            'sha256': hashlib.sha256(raw).hexdigest()}


LAYOUT = r'''(() => {
  const visible=n=>n.getBoundingClientRect().width>0;
  const targets=[...document.querySelectorAll('.timeline-node,.timeline-edge,.timeline-mark,.link-card,.link-card textarea,.link-actions button')].filter(visible);
  return {width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,
    marks:document.querySelectorAll('.timeline-mark').length,lanes:document.querySelectorAll('.event-lane').length,
    outside:targets.filter(n=>{const r=n.getBoundingClientRect();return r.left<0 || r.right>innerWidth+.5;}).map(n=>n.className),
    clipped:targets.filter(n=>n.scrollWidth>n.clientWidth+1).map(n=>n.className),
    mediaColumns:[...document.querySelectorAll('thead .media-col')].filter(visible).map(n=>n.dataset.article),
    resources:performance.getEntriesByType('resource').map(r=>r.name)};
})()'''


def edge_selector(link, scope='.timeline-edge'):
    return scope + '[data-link="' + link['article_id'] + '--' + link['to_article_id'] + '"]'


def prove_links(chrome, session, report):
    sid = report['subject']['id']
    evaluate(chrome, session, f'choose({json.dumps(sid)})')
    snapshot = '({data:JSON.stringify(data),summary:document.querySelector("#summary").textContent,count:document.querySelector("#article-count").textContent,findings:document.querySelector(".report-finding-count").textContent})'
    baseline = evaluate(chrome, session, snapshot)
    baseline_lanes = evaluate(chrome, session, 'document.querySelectorAll(".event-lane").length')
    rows = []
    for link in report['links']:
        card = edge_selector(link, '.link-card')
        edge = edge_selector(link)
        click(chrome, session, edge)
        reasons = evaluate(chrome, session, f'''(() => {{const n=document.querySelector({json.dumps(card)}); return {{open:n.querySelector('details').open,reasons:[...n.querySelectorAll('li')].map(n=>n.textContent),border:getComputedStyle(document.querySelector({json.dumps(edge)})).borderTopStyle}};}})()''')
        assert reasons['open'] and reasons['reasons'] == link['reasons'], reasons
        assert reasons['border'] == ('solid' if link['tier'] == 'CONFIRMED' else 'dashed'), reasons
        if link['tier'] == 'CONFIRMED':
            assert evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelectorAll("[data-link-choice]").length') == 0
            rows.append({'link': link, 'algorithm_solid_and_reasons_exact': True})
            continue
        assert evaluate(chrome, session, f'[...document.querySelector({json.dumps(card)}).querySelectorAll("button")].every(n=>n.disabled)')
        # Deliberately bypass disabled state: save validation must still reject it.
        evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelector("[data-link-choice=Confirm]").disabled=false')
        before = evaluate(chrome, session, 'JSON.stringify(linkDecisions)')
        click(chrome, session, card + ' [data-link-choice="Confirm"]')
        assert evaluate(chrome, session, 'JSON.stringify(linkDecisions)') == before
        click(chrome, session, card + ' textarea')
        chrome.call('Input.insertText', {'text': '   \n\t'}, session)
        assert evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelector("[data-link-choice=Reject]").disabled')
        evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelector("textarea").value=""')
        reason = 'Relationship reviewed against the supplied authority and matter evidence.'
        click(chrome, session, card + ' textarea')
        chrome.call('Input.insertText', {'text': reason}, session)
        click(chrome, session, card + ' [data-link-choice="Confirm"]')
        assert evaluate(chrome, session, f'getComputedStyle(document.querySelector({json.dumps(edge)})).borderTopStyle') == 'solid'
        assert evaluate(chrome, session, f'document.querySelector({json.dumps(edge)}).textContent.includes("Analyst confirmed")')
        # No suggestion, including a human-confirmed one, manufactures a closure.
        endings_before = evaluate(chrome, session, '[...current.events].filter(e=>e.ending).map(e=>e.ending).sort()')
        endings_view = evaluate(chrome, session, '[...document.querySelectorAll(".lane-ending")].map(n=>n.dataset.ending).sort()')
        assert endings_view == endings_before, (endings_before, endings_view)
        count_saved = evaluate(chrome, session, 'linkDecisions.length')
        click(chrome, session, card + ' [data-link-choice="Reject"]')
        rejected = evaluate(chrome, session, f'''({{edge:!!document.querySelector({json.dumps(edge)}),lanes:document.querySelectorAll('.event-lane').length,choice:linkDecisions.find(d=>d.subject==={json.dumps(sid)} && linkKey(d)==={json.dumps(link['article_id']+'--'+link['to_article_id'])}).choice}})''')
        assert not rejected['edge'] and rejected['choice'] == 'Reject', rejected
        assert evaluate(chrome, session, 'linkDecisions.length') == count_saved
        # Reject must yield exactly the graph with this edge removed; if there is
        # another path, the endpoints may remain joined by that other evidence.
        expected = connected_components(report, [link])
        actual = evaluate(chrome, session, '[...document.querySelectorAll(".event-lane")].map(n=>n.dataset.articles.split(",").sort()).sort((a,b)=>a[0].localeCompare(b[0]))')
        assert actual == expected, (actual, expected)
        assert evaluate(chrome, session, snapshot) == baseline
        # Both rejection and confirmation persist after a genuinely fresh document.
        for choice in ('Reject', 'Confirm'):
            if choice == 'Confirm':
                click(chrome, session, card + ' [data-link-choice="Confirm"]')
            saved = evaluate(chrome, session, 'linkDecisions')
            evaluate(chrome, session, 'window.__beforeReload=true')
            chrome.call('Page.reload', session=session)
            ready(chrome, session, fresh=True)
            assert evaluate(chrome, session, 'linkDecisions') == saved
            assert evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelector("textarea").value') == reason
            assert evaluate(chrome, session, f'document.querySelector({json.dumps(card)}).querySelector("[aria-pressed=true]").textContent') == choice
            expected_style = 'solid' if choice == 'Confirm' else None
            actual_style = evaluate(chrome, session, f'(() => {{const n=document.querySelector({json.dumps(edge)});return n ? getComputedStyle(n).borderTopStyle : null;}})()')
            assert actual_style == expected_style
        # Leave the edge pending again for independent next-edge split checks.
        evaluate(chrome, session, f'linkDecisions=linkDecisions.filter(d=>!(d.subject==={json.dumps(sid)} && linkKey(d)==={json.dumps(link["article_id"]+"--"+link["to_article_id"])})); localStorage.setItem(linkStorageKey,JSON.stringify(linkDecisions)); drawTimeline()')
        rows.append({'link': link, 'blank_and_whitespace_rejected': True, 'exact_reasons_on_edge_tap': True,
                     'confirm_solid_reject_removes_edge': True, 'rejected_components': expected,
                     'confirm_and_reject_survive_fresh_reload': True, 'report_unchanged': True,
                     'no_suggested_case_closure': True})
    assert evaluate(chrome, session, 'document.querySelectorAll(".event-lane").length') == baseline_lanes
    return rows


def reject_decoy_proof(chrome, session, report):
    """Exercise all decoy edges, including the alternative-path rejection case."""
    decoys = [link for link in report['links'] if link['article_id'] == 'ART-023']
    assert len(decoys) == 3 and all(link['tier'] == 'SUGGESTED' for link in decoys)
    baseline = evaluate(chrome, session, 'JSON.stringify(data)')
    reason = ('Different Bonded Storage Order 2026 and false-inventory storage conduct; '
              'not the Dual-Use Routing Order 2025 routing matter.')
    for link in decoys:
        card = edge_selector(link, '.link-card')
        click(chrome, session, card + ' textarea')
        chrome.call('Input.insertText', {'text': reason}, session)
        click(chrome, session, card + ' [data-link-choice="Reject"]')
    components = evaluate(chrome, session,
        '[...document.querySelectorAll(".event-lane")].map(n=>n.dataset.articles.split(",").sort()).sort((a,b)=>a[0].localeCompare(b[0]))')
    assert components == connected_components(report, decoys)
    assert ['ART-023'] in components
    assert evaluate(chrome, session, 'JSON.stringify(data)') == baseline
    saved = evaluate(chrome, session, 'linkDecisions')
    assert len(saved) == 3 and all(d['choice'] == 'Reject' and d['reason'] == reason for d in saved)
    evaluate(chrome, session, 'window.__beforeReload=true')
    chrome.call('Page.reload', session=session)
    ready(chrome, session, fresh=True)
    assert evaluate(chrome, session, 'linkDecisions') == saved
    assert evaluate(chrome, session,
        '[...document.querySelectorAll(".event-lane")].some(n=>n.dataset.articles==="ART-023")')
    evaluate(chrome, session, 'linkDecisions=[];localStorage.setItem(linkStorageKey,"[]");drawTimeline()')
    return {'builder_test_inputs_not_BH_decisions': saved,
            'all_three_decoy_suggestions_rejected': True,
            'decoy_separate_after_fresh_reload': True, 'report_unchanged': True,
            'components': components}


def connected_components(report, rejected=()):
    roots = {a['article_id']: a['article_id'] for a in report['comparisons']}
    def root(aid):
        while roots[aid] != aid:
            aid = roots[aid]
        return aid
    for link in report['links']:
        if link not in rejected:
            roots[root(link['article_id'])] = root(link['to_article_id'])
    groups = {}
    for aid in roots:
        groups.setdefault(root(aid), []).append(aid)
    return sorted(sorted(ids) for ids in groups.values())


def export_proof(chrome, session, reports):
    suggested = [(r, l) for r in reports for l in r['links'] if l['tier'] == 'SUGGESTED']
    assert suggested, 'Round-3 browser proof needs real suggested links'
    report, link = suggested[0]
    evaluate(chrome, session, f'choose({json.dumps(report["subject"]["id"])}); linkDecisions=[];')
    card = edge_selector(link, '.link-card')
    click(chrome, session, card + ' textarea')
    chrome.call('Input.insertText', {'text': 'Keep these related reports together for analyst review, not a finding change.'}, session)
    click(chrome, session, card + ' [data-link-choice="Confirm"]')
    # Keep all three human collections populated together; their independent
    # controls must coexist and survive a fresh document without changing cells.
    article = report['comparisons'][0]
    aid = article['article_id']
    evaluate(chrome, session, 'selectArticle(' + json.dumps(aid) + ')')
    article_box = '.decision-box[data-article="' + aid + '"]'
    click(chrome, session, article_box + ' [data-decision-choice="Investigate"]')
    click(chrome, session, article_box + ' textarea')
    chrome.call('Input.insertText', {'text': 'Review the original evidence; the relationship judgment is separate.'}, session)
    click(chrome, session, article_box + ' [data-requires-reason]')
    missing = next((a, field) for a in report['comparisons'] for field, cell in a['fields'].items()
                   if cell['status'] == 'Not stated')
    missing_article, field = missing
    evaluate(chrome, session, 'selectArticle(' + json.dumps(missing_article['article_id']) + ')')
    cell = 'tr[data-field="' + field + '"] td[data-article="' + missing_article['article_id'] + '"]'
    click(chrome, session, cell + ' summary')
    evaluate(chrome, session, '(() => {const n=document.querySelector(' + json.dumps(cell + ' select') + ');n.value="Can\'t tell";n.dispatchEvent(new Event("change",{bubbles:true}));})()')
    click(chrome, session, cell + ' textarea')
    chrome.call('Input.insertText', {'text': 'Missing source detail requires review, not an automatic fill.'}, session)
    saved = evaluate(chrome, session, '({cell_marks:decisions,article_decisions:articleDecisions,link_decisions:linkDecisions})')
    assert saved['link_decisions'] and saved['cell_marks'] and saved['article_decisions']
    evaluate(chrome, session, 'window.__beforeReload=true')
    chrome.call('Page.reload', session=session)
    ready(chrome, session, fresh=True)
    assert evaluate(chrome, session, '({cell_marks:decisions,article_decisions:articleDecisions,link_decisions:linkDecisions})') == saved
    assert evaluate(chrome, session, 'document.querySelector(' + json.dumps(cell + ' .chip') + ').textContent') == 'Not stated'
    chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-read'}, 'setting': 'granted'})
    chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-write'}, 'setting': 'granted'})
    click(chrome, session, '#copy')
    for _ in range(100):
        if evaluate(chrome, session, 'document.querySelector("#notice").textContent.includes("copied")'):
            break
        time.sleep(.03)
    assert json.loads(evaluate(chrome, session, 'navigator.clipboard.readText()')) == saved
    assert json.loads(evaluate(chrome, session, 'document.querySelector("#export").value')) == saved
    # Force both clipboard methods to fail; the visible JSON remains usable.
    evaluate(chrome, session, "Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(new Error('blocked'))}}); document.execCommand=()=>false")
    click(chrome, session, '#copy')
    assert evaluate(chrome, session, '!document.querySelector("#export").hidden && document.querySelector("#notice").textContent.includes("blocked")')
    assert json.loads(evaluate(chrome, session, 'document.querySelector("#export").value')) == saved
    return {'separate_collections': True, 'all_three_nonempty_survive_reload': True,
            'clipboard_read_back_equal': True, 'blocked_clipboard_text_fallback': True, 'saved': saved}


def storage_failure_proof(chrome, session, reports):
    report, link = next((r, l) for r in reports for l in r['links'] if l['tier'] == 'SUGGESTED')
    evaluate(chrome, session, 'choose(' + json.dumps(report['subject']['id']) + ')')
    card = edge_selector(link, '.link-card')
    before = evaluate(chrome, session, 'localStorage.getItem(linkStorageKey)')
    evaluate(chrome, session, 'window.__realSetItem=Storage.prototype.setItem; Storage.prototype.setItem=function(){throw new Error("storage unavailable")}')
    click(chrome, session, card + ' [data-link-choice="Reject"]')
    assert evaluate(chrome, session, 'localStorage.getItem(linkStorageKey)') == before
    assert evaluate(chrome, session, 'document.querySelector(' + json.dumps(card + ' .save-state') + ').textContent.includes("In memory only")')
    click(chrome, session, '#copy')
    exported = json.loads(evaluate(chrome, session, 'document.querySelector("#export").value'))
    assert next(d for d in exported['link_decisions'] if d['subject'] == report['subject']['id']
                and d['article_id'] == link['article_id'] and d['to_article_id'] == link['to_article_id'])['choice'] == 'Reject'
    evaluate(chrome, session, 'Storage.prototype.setItem=window.__realSetItem;window.__beforeReload=true')
    chrome.call('Page.reload', session=session)
    ready(chrome, session, fresh=True)
    assert evaluate(chrome, session, 'JSON.stringify(linkDecisions)') == before
    return {'storage_failure_shown_without_false_saved_claim': True,
            'in_memory_decision_exportable': True, 'prior_stored_decision_unchanged': True}


def main():
    reports = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT / 'reports').glob('SUB-*.json'))]
    assert reports and PAGE.is_file(), 'Parent must generate round-3 reports and dashboard first'
    assert all('links' in r for r in reports), 'Use round-3 reports with explicit links'
    rows, shots, exports = [], [], []
    with tempfile.TemporaryDirectory(prefix='round3-chrome-', dir=os.environ['TMPDIR']) as profile:
        chrome = browser.Chrome(profile)
        try:
            version = chrome.call('Browser.getVersion')
            for width in (1100, 500):
                target, session = open_page(chrome, PAGE, width)
                for report in reports:
                    sid = report['subject']['id']
                    evaluate(chrome, session, f'choose({json.dumps(sid)}); window.scrollTo(0,0)')
                    layout = evaluate(chrome, session, LAYOUT)
                    assert layout['width'] == layout['scrollWidth'] == width and not layout['outside'] and not layout['clipped'] and not layout['resources'], layout
                    assert layout['marks'] == len(report['comparisons'])
                    assert layout['lanes'] == len(connected_components(report))
                    if width == 500:
                        assert len(layout['mediaColumns']) == 1
                    if sid in ('SUB-001', 'SUB-002'):
                        shots.extend(screenshot(chrome, session, sid, width, kind) for kind in ('top', 'full'))
                    links = prove_links(chrome, session, report)
                    decoy = reject_decoy_proof(chrome, session, report) if sid == 'SUB-001' else None
                    for mark in evaluate(chrome, session, 'current.events.flatMap(e=>e.marks)'):
                        click(chrome, session, '.timeline-mark[data-article="' + mark['article_id'] + '"]')
                        article = next(a for a in report['comparisons'] if a['article_id'] == mark['article_id'])
                        previous.assert_article(chrome, session, article, mark['source_sentence'])
                    rows.append({'subject': sid, 'width': width, 'layout': layout,
                                 'links': links, 'decoy_rejection': decoy})
                    print(sid, width, 'PASS: layout, edges, reasons, required decisions, reload and exact timeline sources', flush=True)
                exports.append({'width': width, **export_proof(chrome, session, reports),
                                **storage_failure_proof(chrome, session, reports)})
                chrome.call('Target.closeTarget', {'targetId': target})
            external = [e for e in chrome.events if e.get('method') == 'Network.requestWillBeSent'
                        and e['params']['request']['url'].startswith(('http://', 'https://'))]
            errors = [e for e in chrome.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not external and not errors, (external, errors)
        finally:
            chrome.close()
    proof = {'browser': version, 'transport': 'OS debugging pipes, local file, no server',
             'dashboard_sha256': hashlib.sha256(PAGE.read_bytes()).hexdigest(),
             'external_requests_attempted': len(external), 'javascript_errors': len(errors),
             'pages': rows, 'exports': exports, 'screenshots': shots}
    (OUT / 'browser-checks.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('PASS:', len(shots), 'screenshots; zero external requests; zero JavaScript errors')


if __name__ == '__main__':
    main()
