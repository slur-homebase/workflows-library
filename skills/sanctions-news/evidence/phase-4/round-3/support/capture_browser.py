"""Local Chrome proof over OS pipes only. No debugging port, package or server."""
import base64
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[6]
EVIDENCE = ROOT / 'skills/sanctions-news/evidence/phase-4'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


class Chrome:
    def __init__(self, profile):
        child_read, self.write = os.pipe()
        self.read, child_write = os.pipe()
        self.proc = subprocess.Popen(
            ['bash', '-c', 'exec "$@" 3<&' + str(child_read) + ' 4>&' + str(child_write),
             'chrome-pipe', CHROME, '--headless', '--remote-debugging-pipe',
             '--user-data-dir=' + profile, '--no-first-run', '--no-default-browser-check',
             '--disable-background-networking', '--disable-component-update', '--disable-sync',
             '--disable-extensions', '--disable-default-apps', '--metrics-recording-only',
             '--host-resolver-rules=MAP * ~NOTFOUND', '--no-proxy-server', 'about:blank'],
            pass_fds=(child_read, child_write), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(child_read)
        os.close(child_write)
        self.buffer = b''
        self.number = 0
        self.events = []

    def call(self, method, params=None, session=None):
        self.number += 1
        payload = {'id': self.number, 'method': method, 'params': params or {}}
        if session:
            payload['sessionId'] = session
        os.write(self.write, json.dumps(payload).encode() + b'\0')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            while b'\0' in self.buffer:
                raw, self.buffer = self.buffer.split(b'\0', 1)
                if not raw:
                    continue
                message = json.loads(raw)
                if message.get('id') == self.number:
                    if 'error' in message:
                        raise RuntimeError(message['error'])
                    return message.get('result', {})
                self.events.append(message)
            ready, _, _ = select.select([self.read], [], [], max(0, deadline - time.monotonic()))
            if ready:
                chunk = os.read(self.read, 1048576)
                if not chunk:
                    raise RuntimeError('Chrome pipe closed')
                self.buffer += chunk
        raise TimeoutError(method)

    def close(self):
        try:
            self.call('Browser.close')
        finally:
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=10)
            os.close(self.read)
            os.close(self.write)


PROBE = r"""(() => {
  const width = document.documentElement.clientWidth;
  const visible = el => {
    for (let p = el; p; p = p.parentElement) {
      if (p.tagName === 'DETAILS' && !p.open &&
          !p.querySelector(':scope > summary').contains(el)) return false;
    }
    return true;
  };
  const rect = el => visible(el) ? el.getBoundingClientRect() :
    {width: 0, height: 0, left: 0, right: 0, top: 0, bottom: 0};
  const outside = [...document.querySelectorAll('main *')].filter(el => {
    const r = rect(el); return r.width > 0 && (r.left < -0.5 || r.right > width + 0.5);
  }).map(el => ({tag: el.tagName, class: el.className, text: el.textContent.slice(0,80)}));
  const overlaps = [];
  for (const parent of document.querySelectorAll('.sources,.overview,.readings,.comparison,.cards')) {
    const children = [...parent.children];
    for (let i = 0; i < children.length; i++) for (let j = i+1; j < children.length; j++) {
      const a = rect(children[i]), b = rect(children[j]);
      if (Math.min(a.right,b.right)-Math.max(a.left,b.left)>0.5 &&
          Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>0.5)
        overlaps.push({parent: parent.className, i, j});
    }
  }
  const fragments = [];
  const walker = document.createTreeWalker(document.querySelector('main'),NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.textContent.trim() || !visible(node.parentElement)) continue;
    const range = document.createRange(); range.selectNodeContents(node);
    for (const r of range.getClientRects()) if (r.width>0 && r.height>0)
      fragments.push({left:r.left,right:r.right,top:r.top,bottom:r.bottom,text:node.textContent.trim().slice(0,45)});
  }
  const textOverlaps = [];
  for(let i=0;i<fragments.length;i++) for(let j=i+1;j<fragments.length;j++) {
    const a=fragments[i], b=fragments[j];
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 &&
       Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)
      textOverlaps.push([a.text,b.text]);
  }
  return {clientWidth:width,scrollWidth:document.documentElement.scrollWidth,
    documentHeight:document.documentElement.scrollHeight, outside, overlaps, textOverlaps,
    sources:document.querySelectorAll('.source').length,
    labels:document.querySelectorAll('.source .label').length,
    readingWidths:[...document.querySelectorAll('.readings')].map(n=>[...n.children].map(c=>rect(c).width)),
    resourceEntries:performance.getEntriesByType('resource').map(r=>r.name)};
})()"""


def run():
    rows = []
    with tempfile.TemporaryDirectory(prefix='phase4-chrome-') as profile:
        chrome = Chrome(profile)
        try:
            version = chrome.call('Browser.getVersion')
            for width in (1100, 500):
                for sid in ['SUB-001', 'SUB-002', 'SUB-003', 'SUB-004', 'SUB-005', 'index']:
                    target = chrome.call('Target.createTarget', {'url': 'about:blank'})['targetId']
                    session = chrome.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
                    chrome.call('Page.enable', session=session)
                    chrome.call('Network.enable', session=session)
                    chrome.call('Network.setBlockedURLs', {'urls': ['http://*', 'https://*']}, session)
                    chrome.call('Emulation.setDeviceMetricsOverride',
                                {'width': width, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False}, session)
                    path = EVIDENCE / 'reports' / (sid + '.html')
                    navigation = chrome.call('Page.navigate', {'url': path.as_uri()}, session)
                    if navigation.get('errorText'):
                        raise RuntimeError(navigation)
                    for _ in range(100):
                        ready = chrome.call('Runtime.evaluate', {'expression': 'document.readyState', 'returnByValue': True}, session)
                        if ready['result'].get('value') == 'complete':
                            break
                        time.sleep(.05)
                    else:
                        raise RuntimeError('Page not ready: ' + str(path))
                    result = chrome.call('Runtime.evaluate', {'expression': PROBE, 'returnByValue': True}, session)
                    if 'exceptionDetails' in result:
                        raise RuntimeError(result)
                    data = result['result']['value']
                    data.update({'subject': sid, 'viewport': {'width': width, 'height': 1000}})
                    assert data['clientWidth'] == width, data
                    assert data['scrollWidth'] == width, data
                    assert not data['outside'] and not data['overlaps'] and not data['textOverlaps'], data
                    assert not data['resourceEntries'], data
                    for sizes in data['readingWidths']:
                        assert len(sizes) == 3 and max(sizes)-min(sizes)<1, data
                    if sid != 'index':
                        assert data['sources'] == 5 and data['labels'] == 15, data
                    if sid in {'SUB-002', 'SUB-005'}:
                        image = chrome.call('Page.captureScreenshot', {
                            'format': 'png', 'captureBeyondViewport': True,
                            'clip': {'x': 0, 'y': 0, 'width': width, 'height': data['documentHeight'], 'scale': 1}}, session)
                        out = EVIDENCE / (sid + '-' + str(width) + '.png')
                        raw = base64.b64decode(image['data'])
                        assert raw[:8] == b'\x89PNG\r\n\x1a\n'
                        dimensions = struct.unpack('>II', raw[16:24])
                        assert dimensions == (width, data['documentHeight']), dimensions
                        out.write_bytes(raw)
                        data['screenshot'] = str(out.relative_to(ROOT))
                        data['png_dimensions'] = list(dimensions)
                    rows.append(data)
                    print(sid, width, 'PASS', data.get('png_dimensions', ''), flush=True)
                    chrome.call('Target.closeTarget', {'targetId': target})
            attempted = [event for event in chrome.events if event.get('method') == 'Network.requestWillBeSent'
                         and event['params']['request']['url'].startswith(('http://', 'https://'))]
            assert not attempted, attempted
        finally:
            chrome.close()
    proof = {'browser': version, 'transport': 'OS debugging pipes, no port or network connection',
             'external_requests_attempted': 0, 'pages': rows}
    out = EVIDENCE / 'browser-checks.json'
    out.write_text(json.dumps(proof, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    run()
