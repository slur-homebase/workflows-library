"""Exercise actual offline Chrome clicks, persistence, copy and source highlights."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import time


ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
PAGE = OUT / 'dashboard.html'
SCRATCH = Path.home() / '.hermes/profiles/bellion/cache/scratch'
spec = importlib.util.spec_from_file_location('dashboard_browser_pipe', OUT.parent / 'capture_browser.py')
assert spec and spec.loader
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


def evaluate(chrome, session, expression):
    result = chrome.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True,
                                             'awaitPromise': True, 'userGesture': True}, session)
    assert 'exceptionDetails' not in result, result
    return result['result'].get('value')


def ready(chrome, session, fresh=False):
    expression = "document.readyState === 'complete' && !!document.querySelector('table')"
    if fresh:
        expression += ' && !window.__beforeReload'
    for _ in range(100):
        if evaluate(chrome, session, expression):
            return
        time.sleep(.03)
    raise AssertionError('Dashboard not ready')


def click(chrome, session, selector):
    point = evaluate(chrome, session, '''(() => {
      const n=document.querySelector(%s); if (!n) throw new Error('Missing click target');
      n.scrollIntoView({block:'center',inline:'center'});
      const r=n.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
    })()''' % json.dumps(selector))
    chrome.call('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, **point}, session)
    chrome.call('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, **point}, session)


def screenshot(chrome, session, name, width):
    raw = base64.b64decode(chrome.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False}, session)['data'])
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', raw[16:24]) == (width, 900)
    path = OUT / name
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'dimensions': [width, 900],
            'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    rows, shots = [], []
    with tempfile.TemporaryDirectory(prefix='dashboard-chrome-', dir=SCRATCH) as profile:
        chrome = browser.Chrome(profile)
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
                # Reset test state without racing a second navigation. The actual
                # persistence test below must wait for a new document, not the old DOM.
                evaluate(chrome, session, "localStorage.clear(); decisions=[]; choose('SUB-002')")
                report = json.loads((OUT.parent / 'reports/SUB-002.json').read_text())
                # Prove every media cell and each column header opens the correct text.
                count, grounded, missing = 0, 0, 0
                for article in report['comparisons']:
                    for field, cell in article['fields'].items():
                        selector = f'.cell-open[data-article="{article["article_id"]}"][data-field="{field}"]'
                        click(chrome, session, selector)
                        actual = evaluate(chrome, session, '''(() => {
                          const m=document.querySelector('mark'); const r=m?.getBoundingClientRect();
                          const box=document.querySelector('#article-text').getBoundingClientRect();
                          return {open:document.querySelector('dialog').open,mark:m?.textContent || null,
                            visible:!r || (r.bottom>box.top && r.top<box.bottom),
                            body:document.querySelector('#article-text').textContent,
                            meta:document.querySelector('#article-meta').textContent}; })()''')
                        assert actual['open'] and actual['visible'], actual
                        assert actual['body'] == article['body'], actual
                        assert actual['mark'] == cell['source_sentence'], actual
                        assert article['outlet'] in actual['meta'] and article['date'] in actual['meta'], actual
                        if cell['source_sentence']:
                            grounded += 1
                        else:
                            missing += 1
                        count += 1
                        click(chrome, session, '#close-panel')
                    click(chrome, session, f'.article-open[data-article="{article["article_id"]}"]')
                    assert evaluate(chrome, session, "document.querySelector('dialog').open && document.querySelector('#article-text').textContent") == article['body']
                    click(chrome, session, '#close-panel')
                # Capture comparison from its heading, with the subject fixed on the left.
                evaluate(chrome, session, "document.querySelector('.scroll').scrollLeft=0; document.querySelector('#subject-name').scrollIntoView({block:'start'})")
                shots.append(screenshot(chrome, session, f'SUB-002-{width}-table.png', width))
                click(chrome, session, '.cell-open[data-article="ART-004"][data-field="age"]')
                shots.append(screenshot(chrome, session, f'SUB-002-{width}-article.png', width))
                panel = evaluate(chrome, session, '''(() => { const r=document.querySelector('dialog').getBoundingClientRect();
                  return {x:r.x,width:r.width,height:r.height,mark:document.querySelector('mark').textContent}; })()''')
                if width == 500:
                    assert panel['x'] == 0 and panel['width'] == width and panel['height'] == 900, panel
                else:
                    assert panel['x'] > 0 and panel['width'] < width, panel
                click(chrome, session, '#close-panel')
                # Actual mouse click opens judgment controls. Select/change and type a note.
                key = '#SUB-002-ART-005-age'
                click(chrome, session, 'tr[data-field="age"] td:has(select[data-article="ART-005"]) summary')
                evaluate(chrome, session, f"document.querySelector('{key}').value = \"Can't tell\"; document.querySelector('{key}').dispatchEvent(new Event('change',{{bubbles:true}}))")
                click(chrome, session, key + '-note')
                chrome.call('Input.insertText', {'text': 'Age is not stated; verify before deciding.'}, session)
                saved = evaluate(chrome, session, "JSON.parse(localStorage.getItem(storageKey))")
                assert len(saved) == 1 and saved[0]['choice'] == "Can't tell", saved
                assert saved[0]['note'] == 'Age is not stated; verify before deciding.', saved
                assert set(saved[0]) == {'subject', 'article', 'field', 'choice', 'note', 'time'}
                evaluate(chrome, session, 'window.__beforeReload = true')
                chrome.call('Page.reload', session=session)
                ready(chrome, session, fresh=True)
                persisted = evaluate(chrome, session, f"({{choice:document.querySelector('{key}').value,note:document.querySelector('{key}-note').value,cell:document.querySelector('.cell-open[data-article=\"ART-005\"][data-field=\"age\"]').textContent}})")
                assert persisted['choice'] == "Can't tell" and persisted['note'] == saved[0]['note'], persisted
                assert 'Not stated' in persisted['cell'], persisted
                # File pages have a clipboard origin in Chrome. Grant only the test page permission.
                chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-read'}, 'setting': 'granted'})
                chrome.call('Browser.setPermission', {'permission': {'name': 'clipboard-write'}, 'setting': 'granted'})
                click(chrome, session, '#copy')
                for _ in range(100):
                    if evaluate(chrome, session, "document.querySelector('#notice').textContent.includes('copied')"):
                        break
                    time.sleep(.03)
                exported = evaluate(chrome, session, "document.querySelector('#export').value")
                copied = evaluate(chrome, session, 'navigator.clipboard.readText()')
                assert json.loads(exported) == saved == json.loads(copied), (exported, copied)
                layout = evaluate(chrome, session, '''({width:document.documentElement.clientWidth,
                    scrollWidth:document.documentElement.scrollWidth,
                    resources:performance.getEntriesByType('resource').map(r=>r.name)})''')
                assert layout['width'] == layout['scrollWidth'] == width, layout
                assert not layout['resources'], layout
                rows.append({'width': width, 'height': 900, 'subject': 'SUB-002',
                             'real_mouse_cell_clicks': count, 'highlight_equals_source_sentence': grounded,
                             'not_stated_without_highlight': missing, 'column_header_clicks': len(report['comparisons']),
                             'persisted_decision': saved[0], 'missing_cell_stays_not_stated': True,
                             'copied_json_read_back_from_clipboard': True, 'panel': panel, 'layout': layout})
                print(f'SUB-002 {width}x900: {count} cell clicks, {grounded} exact highlights, {missing} unstated cells; reload persistence and clipboard PASS', flush=True)
                chrome.call('Target.closeTarget', {'targetId': target})
            external = [e for e in chrome.events if e.get('method') == 'Network.requestWillBeSent'
                        and e['params']['request']['url'].startswith(('http://', 'https://'))]
            errors = [e for e in chrome.events if e.get('method') == 'Runtime.exceptionThrown']
            assert not external, external
            assert not errors, errors
        finally:
            chrome.close()
    proof = {'browser': version, 'transport': 'OS debugging pipes, file page, no server or external resources',
             'html_sha256': hashlib.sha256(PAGE.read_bytes()).hexdigest(),
             'external_requests_attempted': len(external), 'javascript_errors': len(errors),
             'pages': rows, 'screenshots': shots}
    (OUT / 'browser-checks.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('External requests attempted: 0; JavaScript errors: 0; screenshots: ' + str(len(shots)))


if __name__ == '__main__':
    main()
