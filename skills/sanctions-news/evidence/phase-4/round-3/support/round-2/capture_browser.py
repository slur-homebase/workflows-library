"""Offline Chrome proof for round-2 events, decisions, sources and phone layout."""

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import time

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
PAGE = OUT / 'dashboard.html'
SPEC = importlib.util.spec_from_file_location('previous_dashboard_browser', OUT.parent / 'dashboard/capture_browser.py')
assert SPEC and SPEC.loader
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
evaluate = previous.evaluate
click = previous.click
ready = previous.ready


def screenshot(chrome, session, sid, width, kind):
    height = 900 if kind == 'top' else evaluate(chrome, session, 'document.documentElement.scrollHeight')
    raw = base64.b64decode(chrome.call('Page.captureScreenshot', {
        'format': 'png', 'captureBeyondViewport': True,
        'clip': {'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1}}, session)['data'])
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', raw[16:24]) == (width, height)
    path = OUT / f'{sid}-{width}-{kind}.png'
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'dimensions': [width, height],
            'sha256': hashlib.sha256(raw).hexdigest()}


LAYOUT = r'''(() => {
  const visible=n=>n.getBoundingClientRect().width>0;
  const rect=n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width};};
  const outside=[...document.querySelectorAll('.timeline-mark,.timeline-line,.event-lane,.article-controls')]
    .filter(visible).filter(n=>{const r=rect(n); return r.left<0 || r.right>innerWidth+.5;}).map(n=>n.className);
  const clipped=[...document.querySelectorAll('.timeline-mark,.timeline-line')]
    .filter(n=>n.scrollWidth>n.clientWidth+1).map(n=>n.textContent);
  return {width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,
    timelineMarks:document.querySelectorAll('.timeline-mark').length,
    lanes:document.querySelectorAll('.event-lane').length,
    headers:[...document.querySelectorAll('.event-headers [data-event]')].map(n=>({event:n.dataset.event,count:n.colSpan,text:n.textContent,visible:visible(n)})),
    mediaColumns:[...document.querySelectorAll('thead .media-col')].filter(visible).map(n=>n.dataset.article),
    columnWidths:[...document.querySelectorAll('thead .media-col')].filter(visible).map(n=>n.getBoundingClientRect().width),
    tableScrollLeft:document.querySelector('#comparison').scrollLeft,
    timelineFont:getComputedStyle(document.querySelector('.timeline-line')).fontSize,
    timelineTop:document.querySelector('#timeline').getBoundingClientRect().top+scrollY,
    tableWidth:document.querySelector('table').getBoundingClientRect().width,
    outside,clipped,resources:performance.getEntriesByType('resource').map(r=>r.name)};
})()'''


def assert_article(chrome, session, article, sentence):
    actual = evaluate(chrome, session, r'''(() => {
      const mark=document.querySelector('mark'), r=mark?.getBoundingClientRect(), box=document.querySelector('#article-text').getBoundingClientRect();
      return {open:document.querySelector('dialog').open,body:document.querySelector('#article-text').textContent,
        sentence:mark?.textContent || null,visible:!r || (r.bottom>box.top && r.top<box.bottom)};
    })()''')
    assert actual == {'open': True, 'body': article['body'], 'sentence': sentence, 'visible': True}, actual
    click(chrome, session, '#close-panel')


def decisions_proof(chrome, session, width):
    evaluate(chrome, session, "choose('SUB-002'); selectArticle('ART-004'); window.__baseline=JSON.stringify(data); window.__chips=[...document.querySelectorAll('.cell-open .chip')].map(n=>n.textContent); window.__count=document.querySelector('#article-count').textContent")
    box = '.decision-box[data-article="ART-004"]'
    click(chrome, session, box + ' [data-decision-choice="Not our person"]')
    assert evaluate(chrome, session, f'document.querySelector({json.dumps(box + " [data-requires-reason]")}).disabled')
    # Even bypassing the disabled UI cannot bypass the pure save validation.
    evaluate(chrome, session, f'document.querySelector({json.dumps(box + " [data-requires-reason]")}).disabled=false')
    click(chrome, session, box + ' [data-requires-reason]')
    assert evaluate(chrome, session, 'articleDecisions.length') == 0
    click(chrome, session, '#SUB-002-ART-004-reason')
    chrome.call('Input.insertText', {'text': 'Age is 67 in the article; our subject was 39 at publication.'}, session)
    click(chrome, session, box + ' input[value="age"]')
    click(chrome, session, box + ' [data-requires-reason]')
    first = evaluate(chrome, session, 'JSON.parse(localStorage.getItem(articleStorageKey))')
    assert len(first) == 1 and first[0]['choice'] == 'Not our person' and first[0]['support'] == ['age'], first
    assert first[0]['supporting_cells'][0]['status'] == 'Different'
    # Change the decision without adding another one or altering evidence/counts.
    for choice in ('Our person, not relevant', 'Need more info', 'Investigate'):
        click(chrome, session, box + f' [data-decision-choice="{choice}"]')
        click(chrome, session, box + ' [data-requires-reason]')
        assert evaluate(chrome, session, 'articleDecisions.length') == 1
    assert evaluate(chrome, session, "JSON.stringify(data)===window.__baseline && JSON.stringify([...document.querySelectorAll('.cell-open .chip')].map(n=>n.textContent))===JSON.stringify(window.__chips) && document.querySelector('#article-count').textContent===window.__count")
    # Retain the existing cell judgment path independently of the article decision.
    evaluate(chrome, session, "selectArticle('ART-005')")
    click(chrome, session, 'tr[data-field="age"] td[data-article="ART-005"] summary')
    evaluate(chrome, session, '''document.querySelector('#SUB-002-ART-005-age').value="Can't tell";
      document.querySelector('#SUB-002-ART-005-age').dispatchEvent(new Event('change',{bubbles:true}))''')
    click(chrome, session, '#SUB-002-ART-005-age-note')
    chrome.call('Input.insertText', {'text': 'Age is not stated in this article.'}, session)
    saved = evaluate(chrome, session, '({article_decisions:articleDecisions,cell_marks:decisions})')
    assert len(saved['cell_marks']) == 1 and len(saved['article_decisions']) == 1
    evaluate(chrome, session, 'window.__beforeReload=true')
    chrome.call('Page.reload', session=session)
    ready(chrome, session, fresh=True)
    assert evaluate(chrome, session, '({article_decisions:articleDecisions,cell_marks:decisions})') == saved
    persisted = evaluate(chrome, session, '''({reason:document.querySelector('#SUB-002-ART-004-reason').value,
      choice:document.querySelector('.decision-box[data-article="ART-004"] [aria-pressed=true]').textContent,
      age:document.querySelector('.cell-open[data-article="ART-005"][data-field="age"] .chip').textContent,
      support:document.querySelector('.decision-box[data-article="ART-004"] input[value="age"]').checked})''')
    assert persisted['reason'] == saved['article_decisions'][0]['reason'] and persisted['choice'] == 'Investigate'
    assert persisted['age'] == 'Not stated' and persisted['support']
    chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-read'}, 'setting': 'granted'})
    chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-write'}, 'setting': 'granted'})
    click(chrome, session, '#copy')
    for _ in range(100):
        if evaluate(chrome, session, "document.querySelector('#notice').textContent.includes('copied')"):
            break
        time.sleep(.03)
    exported = evaluate(chrome, session, "document.querySelector('#export').value")
    copied = evaluate(chrome, session, 'navigator.clipboard.readText()')
    assert json.loads(exported) == json.loads(copied) == saved
    return {'width': width, 'blank_reason_rejected_even_when_ui_bypassed': True,
            'all_four_choices_saved_with_reason': True, 'single_decision_replaces_previous': True,
            'reports_chips_and_counts_unchanged': True, 'fresh_document_reload_persisted': True,
            'cell_marks_separate': True, 'clipboard_read_back_equal': True, 'saved': saved}


def main():
    rows, shots, choices = [], [], []
    reports = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT / 'reports').glob('SUB-*.json'))}
    with tempfile.TemporaryDirectory(prefix='round2-chrome-', dir=os.environ['TMPDIR']) as profile:
        chrome = previous.browser.Chrome(profile)
        try:
            version = chrome.call('Browser.getVersion')
            for width in (1100, 500):
                target = chrome.call('Target.createTarget', {'url': 'about:blank'})['targetId']
                session = chrome.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
                for domain in ('Page', 'Network', 'Runtime'):
                    chrome.call(domain + '.enable', session=session)
                chrome.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*']}, session)
                chrome.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 900,
                            'deviceScaleFactor': 1, 'mobile': False}, session)
                chrome.call('Page.navigate', {'url': PAGE.as_uri() + '#SUB-002'}, session)
                ready(chrome, session)
                evaluate(chrome, session, 'localStorage.clear(); decisions=[]; articleDecisions=[];')
                for sid, report in reports.items():
                    evaluate(chrome, session, f'choose({json.dumps(sid)}); window.scrollTo(0,0);')
                    layout = evaluate(chrome, session, LAYOUT)
                    assert layout['width'] == layout['scrollWidth'] == width, layout
                    assert not layout['outside'] and not layout['clipped'] and not layout['resources'], layout
                    assert layout['timelineMarks'] == len(report['comparisons']), layout
                    assert layout['lanes'] == len({a['event_id'] for a in report['comparisons']}), layout
                    assert len(layout['headers']) == layout['lanes'], layout
                    assert layout['tableScrollLeft'] == 0, layout
                    if width == 500:
                        assert len(layout['mediaColumns']) == 1 and layout['tableWidth'] <= 476, layout
                    else:
                        assert all(abs(w-250)<1 for w in layout['columnWidths']), layout
                    if sid == 'SUB-003' and width == 1100:
                        group = next(g for g in layout['headers'] if g['event'] == 'EVT-007')
                        assert group['count'] == 2 and group['text'] == 'EVT-007 · 2 articles', group
                    if sid in ('SUB-002', 'SUB-003'):
                        shots.extend(screenshot(chrome, session, sid, width, kind) for kind in ('top', 'full'))
                    timeline = evaluate(chrome, session, 'current.events.flatMap(e=>e.marks)')
                    by_id = {a['article_id']: a for a in report['comparisons']}
                    for mark in timeline:
                        click(chrome, session, f'.timeline-mark[data-article="{mark["article_id"]}"]')
                        assert_article(chrome, session, by_id[mark['article_id']], mark['source_sentence'])
                    cell_count = 0
                    for article in report['comparisons']:
                        aid = article['article_id']
                        evaluate(chrome, session, f'selectArticle({json.dumps(aid)})')
                        for field in [*article['fields'], 'part_in_story', 'stage']:
                            sentence = article['story_evidence'][field] if field in ('part_in_story', 'stage') else article['fields'][field]['source_sentence']
                            click(chrome, session, f'.cell-open[data-article="{aid}"][data-field="{field}"]')
                            assert_article(chrome, session, article, sentence)
                            cell_count += 1
                        click(chrome, session, f'.article-open[data-article="{aid}"]')
                        assert_article(chrome, session, article, None)
                    if width == 500:
                        for article in report['comparisons']:
                            evaluate(chrome, session, f'selectArticle({json.dumps(article["article_id"])})')
                            one = evaluate(chrome, session, LAYOUT)
                            assert one['mediaColumns'] == [article['article_id']] and one['tableWidth'] <= 476, one
                            assert one['scrollWidth'] == 500, one
                        evaluate(chrome, session, "selectArticle(document.querySelector('#article-picker').options[0].value)")
                        order = evaluate(chrome, session, "[...document.querySelector('#article-picker').options].map(n=>n.value)")
                        for aid in order[1:]:
                            click(chrome, session, '#next-article')
                            assert evaluate(chrome, session, 'selectedArticle') == aid
                        if len(order) > 1:
                            click(chrome, session, '#previous-article')
                            assert evaluate(chrome, session, 'selectedArticle') == order[-2]
                    rows.append({'subject': sid, 'width': width, 'layout': layout,
                                 'exact_timeline_highlights': len(timeline), 'cell_clicks': cell_count,
                                 'exact_story_highlights_or_unstated': 2 * len(report['comparisons']),
                                 'headline_clicks': len(report['comparisons'])})
                    print(sid, width, 'PASS:', len(timeline), 'timeline marks;', cell_count, 'cell clicks; one event header per id', flush=True)
                choices.append(decisions_proof(chrome, session, width))
                print(width, 'PASS: blank reason blocked, four choices, one saved article decision, unchanged chips/counts, reload and clipboard', flush=True)
                chrome.call('Target.closeTarget', {'targetId': target})
            external = [e for e in chrome.events if e.get('method') == 'Network.requestWillBeSent'
                        and e['params']['request']['url'].startswith(('http://', 'https://'))]
            errors = [e for e in chrome.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not external and not errors, (external, errors)
        finally:
            chrome.close()
    proof = {'browser': version, 'transport': 'OS debugging pipes, file page, no server',
             'dashboard_sha256': hashlib.sha256(PAGE.read_bytes()).hexdigest(),
             'external_requests_attempted': len(external), 'javascript_errors': len(errors),
             'pages': rows, 'decisions': choices, 'screenshots': shots}
    (OUT / 'browser-checks.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('PASS:', len(shots), 'screenshots; zero external requests; zero JavaScript errors')


if __name__ == '__main__':
    main()
