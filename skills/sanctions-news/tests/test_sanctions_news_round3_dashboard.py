"""Round-3 dashboard edge semantics, immutable reports and real offline browser proof."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'evidence/phase-4/round-3/test-baseline'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard = load('round3_dashboard_renderer', ROOT / 'scripts/render_dashboard.py')
capture = load('round3_dashboard_browser', ROOT / 'evidence/phase-4/round-3/capture_browser.py')


def reports_fixture():
    # Use the frozen baseline, not in-flight current research/fixture changes.
    reports = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(FROZEN.glob('SUB-*.json'))]
    for report in reports:
        report['links'] = dashboard.report_links(report)
    # The old closure pair deliberately shares an event_id. Downgrade its edge
    # in this isolated test to prove a raw id or existing resolution cannot
    # manufacture a round-3 confirmed lane or closure.
    reports[2]['links'][0]['tier'] = 'SUGGESTED'
    reports[2]['links'][0]['reasons'] = ['Same stated authority.', 'Shared matter words, without affirmative reference.']
    # A second isolated graph edge exercises repeated reloads and multiple
    # decisions. Renderer tests trust a supplied edge; research eligibility is
    # tested separately against article evidence, not inferred by this view.
    reports[2]['links'].append({'article_id': 'ART-016', 'to_article_id': 'ART-008',
                                'tier': 'SUGGESTED', 'reasons': ['Isolated invented graph test edge.']})
    # Retain another real algorithm pair in a separate report for browser solid
    # edge checks without changing any body or identity comparison cell.
    clone = copy.deepcopy(reports[2])
    clone['subject']['id'] = 'SUB-901'
    clone['links'][0]['tier'] = 'CONFIRMED'
    reports.append(clone)
    return reports


class Round3DashboardTest(unittest.TestCase):
    def setUp(self):
        self.reports = reports_fixture()
        self.report = self.reports[2]
        self.link = self.report['links'][0]

    def payload(self, report=None):
        html = dashboard.render_dashboard([report or self.report])
        match = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
        assert match is not None
        return json.loads(match[1])['reports'][0]

    def js(self, source):
        node = shutil.which('node')
        if not node:
            self.skipTest('Installed Node needed; no package install attempted')
        proc = subprocess.run([node, '-e', dashboard.DECISION_LOGIC + '\nconst reports=JSON.parse(require("fs").readFileSync(0,"utf8"));\n' + source],
                              input=json.dumps([self.payload()]), text=True, capture_output=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_same_raw_event_id_does_not_join_round3_articles(self):
        groups = dashboard.event_groups(self.report)
        opening = next(g for g in groups if 'ART-007' in g['article_ids'])
        closure = next(g for g in groups if 'ART-009' in g['article_ids'])
        self.assertIsNot(opening, closure)
        self.assertNotEqual(opening['event_id'], closure['event_id'])
        self.assertNotIn('case closed', [g['ending'] for g in groups])

    def test_empty_explicit_links_prevent_raw_id_and_resolution_join(self):
        self.report['links'] = []
        groups = dashboard.event_groups(self.report)
        self.assertEqual(len(groups), len(self.report['comparisons']))
        self.assertFalse(any(g['ending'] == 'case closed' for g in groups))

    def test_only_algorithm_confirmed_can_join_and_copy_closure_ending(self):
        self.link['tier'] = 'CONFIRMED'
        group = next(g for g in dashboard.event_groups(self.report) if 'ART-007' in g['article_ids'])
        self.assertEqual(group['article_ids'], ['ART-007', 'ART-009'])
        self.assertEqual(group['ending'], 'case closed')

    def test_legacy_resolution_remains_supported_without_raw_edge_inference(self):
        self.report.pop('links')
        links = dashboard.report_links(self.report)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['tier'], 'CONFIRMED')
        self.assertEqual(links[0]['article_id'], 'ART-009')
        self.assertEqual(links[0]['to_article_id'], 'ART-007')

    def test_malformed_edges_and_non_forward_dates_are_rejected(self):
        invalid = [None, {}, 'edge', [{'tier': 'SUGGESTED'}]]
        invalid += [[{**self.link, **change}] for change in (
            {'tier': 'confirmed'}, {'article_id': 'ART-999'}, {'to_article_id': self.link['article_id']},
            {'article_id': self.link['to_article_id'], 'to_article_id': self.link['article_id']},
            {'reasons': []}, {'reasons': [' ']}, {'reasons': [None]}, {'reasons': 'reason'},
            {'article_id': []})]
        invalid.append([self.link, copy.deepcopy(self.link)])
        for links in invalid:
            report = copy.deepcopy(self.report)
            report['links'] = links
            with self.subTest(links=links), self.assertRaises(ValueError):
                dashboard.render_dashboard([report])
        report = copy.deepcopy(self.report)
        dates = {a['article_id']: a['date'] for a in report['comparisons']}
        for article in report['comparisons']:
            if article['article_id'] == self.link['article_id']:
                article['date'] = dates[self.link['to_article_id']]
        with self.assertRaises(ValueError):
            dashboard.render_dashboard([report])

    def test_duplicate_article_id_is_rejected_before_building_graph(self):
        self.report['comparisons'].append(copy.deepcopy(self.report['comparisons'][0]))
        with self.assertRaisesRegex(ValueError, 'Repeated article id'):
            dashboard.render_dashboard([self.report])

    def test_decisions_require_reason_valid_edge_choice_time_and_length(self):
        result = self.js('''
          const report=reports[0], link=report.links[0], base={subject:report.subject.id,
            ...link,choice:'Confirm',reason:'Reviewed authority and matter.',time:'2026-10-31T03:00:00Z'};
          const invalid=[{reason:''},{reason:'  \\n\\t'},{reason:null},{reason:'x'.repeat(601)},
            {choice:'CONFIRMED'},{article_id:'ART-999'},{to_article_id:'ART-999'},
            {subject:'SUB-999'},{time:''},{time:null}];
          console.log(JSON.stringify(invalid.map(p=>{try{recordLinkDecision([],{...base,...p},reports);return false;}catch(_){return true;}})));
        ''')
        self.assertEqual(result, [True] * 10)

    def test_pending_confirm_and_reject_are_visual_only_and_reversible(self):
        result = self.js('''
          const report=reports[0], link=report.links[0], before=JSON.stringify(report);
          const base={subject:report.subject.id,...link,choice:'Confirm',reason:'  Same matter.  ',time:'2026-10-31T03:00:00Z'};
          const pending=timelineGroups(report,[]);
          let saved=recordLinkDecision([],base,reports);
          const confirmed=timelineGroups(report,saved);
          saved=recordLinkDecision(saved,{...base,choice:'Reject',reason:'Different matter.'},reports);
          const rejected=timelineGroups(report,saved);
          const restored=JSON.parse(JSON.stringify(saved)).reduce((acc,d)=>recordLinkDecision(acc,d,reports),[]);
          console.log(JSON.stringify({unchanged:before===JSON.stringify(report),saved,restored,
            pending,confirmed,rejected}));
        ''')
        self.assertTrue(result['unchanged'])
        self.assertEqual(result['saved'], result['restored'])
        self.assertEqual(len(result['saved']), 1)
        self.assertEqual(result['saved'][0]['choice'], 'Reject')
        self.assertEqual(result['saved'][0]['suggested_tier'], 'SUGGESTED')
        self.assertEqual(result['saved'][0]['suggested_reasons'], self.link['reasons'])
        self.assertEqual(result['pending'], result['confirmed'])
        self.assertEqual(len(result['rejected']), len(result['confirmed']) + 1)
        self.assertFalse(any('case closed' in g['endings'] for g in result['confirmed']))
        self.assertFalse(any('case closed' in g['endings'] for g in result['rejected']))

    def test_decision_cannot_override_algorithm_confirmed_link(self):
        self.link['tier'] = 'CONFIRMED'
        result = self.js('''
          try {recordLinkDecision([],{subject:reports[0].subject.id,...reports[0].links[0],
            choice:'Reject',reason:'No.',time:'2026-10-31T03:00:00Z'},reports); console.log('false');}
          catch(_){console.log('true');}
        ''')
        self.assertTrue(result)

    def test_multiple_incoming_links_preserved_and_rejection_removes_only_its_edge(self):
        articles = sorted(self.report['comparisons'], key=lambda a:(a['date'], a['article_id']))
        extra = {'article_id': articles[-1]['article_id'], 'to_article_id': articles[1]['article_id'],
                 'tier': 'SUGGESTED', 'reasons': ['Independent shared matter.']}
        self.report['links'].append(extra)
        self.assertEqual(len(self.payload()['links']), len(self.report['links']))
        result = self.js('''
          const r=reports[0], l=r.links[0], decisions=recordLinkDecision([],{subject:r.subject.id,...l,
            choice:'Reject',reason:'Different inquiry.',time:'2026-10-31T03:00:00Z'},reports);
          console.log(JSON.stringify(timelineGroups(r,decisions).map(g=>g.article_ids)));
        ''')
        self.assertEqual(sorted(a for group in result for a in group), sorted(a['article_id'] for a in self.report['comparisons']))

    def test_groups_and_edges_are_stable_under_report_article_and_link_reordering(self):
        original = dashboard.event_groups(self.report)
        self.report['comparisons'].reverse()
        self.report['links'].reverse()
        self.assertEqual(dashboard.event_groups(self.report), original)

    def test_identical_bytes_no_mutation_no_network_and_safe_reason_text(self):
        self.link['reasons'].append('</script><img src=x onerror=alert(1)>')
        before = copy.deepcopy(self.reports)
        first = dashboard.render_dashboard(self.reports)
        self.assertEqual(first.encode(), dashboard.render_dashboard(self.reports).encode())
        self.assertEqual(self.reports, before)
        self.assertNotRegex(first, r'https?://|@import|url\s*\(')
        self.assertNotIn('<img', first)
        self.assertEqual(first.count('</script>'), 2)
        for token in ('link_decisions:linkDecisions', 'localStorage.setItem(linkStorageKey',
                      'recordLinkDecision(linkDecisions, d, data.reports)', 'border-top:3px dashed',
                      '.timeline-edge.edge-confirmed,.timeline-edge.edge-analyst-confirmed',
                      'suggested, analyst to confirm'):
            self.assertIn(token, first)
        payload = self.payload()
        self.assertEqual(payload['summary'], self.report['summary'])
        self.assertEqual(payload['finding_count'], len(self.report['findings']))

    def test_stated_settlement_stage_row_opens_verbatim_line(self):
        research = load('settlement_stage_research', ROOT / 'scripts/research.py')
        fixtures = ROOT / 'fixtures'
        report = research.research('SUB-001', fixtures)
        articles = {a['article_id']: a for a in report['comparisons']}
        for aid in ('ART-022', 'ART-028'):
            article = articles[aid]
            original = research.read_article(fixtures / 'articles' / (aid + '.md'))
            self.assertEqual(article['stage'], 'settlement')
            self.assertEqual(article['part_in_story'], 'not stated')
            self.assertIsNone(article['story_evidence']['part_in_story'])
            self.assertEqual(article['story_evidence']['stage'], original['body'].splitlines()[0])
            self.assertIn('agreed to settle', article['story_evidence']['stage'])
        executable = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        if not executable.is_file():
            self.skipTest('Installed Chrome needed; no install attempted')
        with tempfile.TemporaryDirectory(prefix='settlement-stage-test-', dir=os.environ.get('TMPDIR')) as temp:
            folder = Path(temp)
            page = folder / 'dashboard.html'
            page.write_text(dashboard.render_dashboard([report]), encoding='utf-8')
            chrome = capture.browser.Chrome(str(folder / 'profile'))
            try:
                for width in (1100, 500):
                    target, session = capture.open_page(chrome, page, width)
                    for aid in ('ART-022', 'ART-028'):
                        with self.subTest(article=aid, width=width):
                            capture.evaluate(chrome, session, 'selectArticle(' + json.dumps(aid) + ')')
                            selector = '.cell-open[data-field="stage"][data-article="' + aid + '"]'
                            actual = capture.evaluate(chrome, session, '''(() => {
                              const n=document.querySelector(''' + json.dumps(selector) + ''');
                              return {value:n.querySelector('.value').textContent,
                                      status:n.querySelector('.chip').textContent};
                            })()''')
                            self.assertEqual(actual, {'value': 'settlement', 'status': 'Stated'})
                            capture.click(chrome, session, selector)
                            capture.previous.assert_article(chrome, session, articles[aid],
                                                            articles[aid]['story_evidence']['stage'])
                    chrome.call('Target.closeTarget', {'targetId': target})
                self.assertFalse([e for e in chrome.events if e.get('method') == 'Runtime.exceptionThrown'])
                self.assertFalse([e for e in chrome.events if e.get('method') == 'Network.requestWillBeSent'
                                  and e['params']['request']['url'].startswith(('http://', 'https://'))])
            finally:
                chrome.close()

    def test_actual_installed_chrome_persistence_rejection_export_and_widths(self):
        executable = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        if not executable.is_file():
            self.skipTest('Installed Chrome needed; no install attempted')
        with tempfile.TemporaryDirectory(prefix='round3-dashboard-test-', dir=os.environ.get('TMPDIR')) as temp:
            folder = Path(temp)
            page = folder / 'dashboard.html'
            page.write_text(dashboard.render_dashboard(self.reports), encoding='utf-8')
            chrome = capture.browser.Chrome(str(folder / 'profile'))
            try:
                for width in (1100, 500):
                    target, session = capture.open_page(chrome, page, width)
                    for report in (self.report, self.reports[-1]):
                        capture.evaluate(chrome, session, 'choose(' + json.dumps(report['subject']['id']) + ')')
                        layout = capture.evaluate(chrome, session, capture.LAYOUT)
                        self.assertEqual(layout['width'], width)
                        self.assertEqual(layout['scrollWidth'], width)
                        self.assertFalse(layout['outside'], layout)
                        self.assertFalse(layout['clipped'], layout)
                        self.assertFalse(layout['resources'], layout)
                        self.assertEqual(layout['marks'], len(report['comparisons']))
                        if width == 500:
                            self.assertEqual(len(layout['mediaColumns']), 1)
                        capture.prove_links(chrome, session, report)
                    capture.export_proof(chrome, session, self.reports)
                    capture.storage_failure_proof(chrome, session, self.reports)
                    chrome.call('Target.closeTarget', {'targetId': target})
                self.assertFalse([e for e in chrome.events if e.get('method') == 'Runtime.exceptionThrown'])
                self.assertFalse([e for e in chrome.events if e.get('method') == 'Network.requestWillBeSent'
                                  and e['params']['request']['url'].startswith(('http://', 'https://'))])
            finally:
                chrome.close()


if __name__ == '__main__':
    unittest.main()
