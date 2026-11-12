"""Offline comparison evidence and rendering regressions. Browser proof is separate."""

import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
FIXTURES = ROOT / 'fixtures'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


research = load('dashboard_research', 'research.py')
dashboard = load('dashboard_renderer', 'render_dashboard.py')
compare = load('dashboard_comparison', 'compare_media.py')
page = load('dashboard_legacy_page', 'render_page.py')


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subjects = research.read_json(FIXTURES / 'subjects.json')['subjects']
        cls.reports = [research.research(s['id'], FIXTURES) for s in cls.subjects]
        cls.html = dashboard.render_dashboard(cls.reports)

    def article(self, sid, aid):
        report = next(r for r in self.reports if r['subject']['id'] == sid)
        return next(a for a in report['comparisons'] if a['article_id'] == aid)

    def extract(self, subject, body):
        article = {'body': body, 'date': '2026-10-23'}
        return compare.extract_fields(subject, article, research.sentences, research.stated_identity, research.age_at)

    def test_all_twenty_nine_articles_appear_once_under_their_named_subject(self):
        articles = [a['article_id'] for r in self.reports for a in r['comparisons']]
        self.assertEqual(sorted(articles), [f'ART-{i:03}' for i in range(1, 30)])

    def test_every_media_value_has_verbatim_sentence_and_value_substring(self):
        for report in self.reports:
            for article in report['comparisons']:
                original = research.read_article(FIXTURES / 'articles' / (article['article_id'] + '.md'))
                self.assertEqual(article['body'], original['body'])
                for field, cell in article['fields'].items():
                    with self.subTest(article=article['article_id'], field=field):
                        if cell['value'] is not None:
                            self.assertIn(cell['source_sentence'], original['body'])
                            self.assertIn(cell['value'], cell['source_sentence'])
                            self.assertIn(cell['source_sentence'], research.sentences(original['body']))

    def test_every_not_stated_cell_has_no_value_or_sentence(self):
        cells = [c for r in self.reports for a in r['comparisons'] for c in a['fields'].values()]
        missing = [c for c in cells if c['status'] == 'Not stated']
        self.assertTrue(missing)
        for cell in missing:
            self.assertIsNone(cell['value'])
            self.assertIsNone(cell['source_sentence'])

    def test_story_rows_copy_metadata_and_do_not_claim_identity_agreement(self):
        self.assertIn("part_in_story:'Their part in the story'", self.html)
        self.assertIn("stage:'Stage'", self.html)
        self.assertIn('Article context, not an identity comparison', self.html)
        self.assertIn('article.story_evidence[field]', self.html)
        for report in self.reports:
            for article in report['comparisons']:
                for field in ('part_in_story', 'stage'):
                    sentence = article['story_evidence'][field]
                    if article[field] == 'not stated':
                        self.assertIsNone(sentence)
                    else:
                        self.assertIn(sentence, article['body'].splitlines())

    def test_story_renderer_rejects_missing_or_fabricated_evidence(self):
        for field, value in (('stage', 'invented'), ('event_id', 'EVT-1')):
            reports = copy.deepcopy(self.reports)
            reports[0]['comparisons'][0][field] = value
            with self.assertRaises(ValueError):
                dashboard.render_dashboard(reports)
        for value in (None, 'Invented sentence.'):
            reports = copy.deepcopy(self.reports)
            reports[0]['comparisons'][0]['story_evidence']['stage'] = value
            with self.assertRaises(ValueError):
                dashboard.render_dashboard(reports)
        reports = copy.deepcopy(self.reports)
        reports[0]['comparisons'][2]['story_evidence']['stage'] = 'Invented sentence.'
        with self.assertRaises(ValueError):
            dashboard.render_dashboard(reports)

    def run_decision_logic(self, javascript):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Installed Node needed to execute pure JavaScript decision tests')
        source = dashboard.DECISION_LOGIC + '\nconst reports=JSON.parse(require("fs").readFileSync(0,"utf8"));\n' + javascript
        proc = subprocess.run([node, '-e', source], input=json.dumps(self.reports), text=True,
                              capture_output=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_actual_js_decision_logic_rejects_blank_reasons_and_invalid_choices(self):
        result = self.run_decision_logic('''
          const base={subject:'SUB-002',article:'ART-004',choice:'Not our person',
            reason:'Age differs',support:['age','position'],time:'2026-10-31T01:00:00Z'};
          const invalid=[{reason:''},{reason:'  \\n\\t'},{reason:null},{reason:'x'.repeat(601)},
            {choice:'auto-dismiss'},{article:'ART-999'},{subject:'SUB-999'},
            {support:['guessed']},{support:['age','age']},{time:''}];
          const rejected=invalid.map(p=>{try { recordArticleDecision([], {...base,...p},reports); return false; }
            catch (_) { return true; }});
          console.log(JSON.stringify(rejected));
        ''')
        self.assertEqual(result, [True] * 10)
        self.assertIn("save.dataset.requiresReason='true'", self.html)
        self.assertIn('!note.value.trim()', self.html)

    def test_actual_js_decision_replaces_only_one_article_and_does_not_change_reports(self):
        result = self.run_decision_logic('''
          const before=JSON.stringify(reports), first={subject:'SUB-002',article:'ART-004',choice:'Not our person',
            reason:'  Age differs: 67 versus 39.  ',support:['age','position'],time:'2026-10-31T01:00:00Z'};
          let saved=recordArticleDecision([],first,reports);
          saved=recordArticleDecision(saved,{...first,article:'ART-005',choice:'Need more info',support:['age']},reports);
          saved=recordArticleDecision(saved,{...first,choice:'Investigate',reason:'Review the age evidence.'},reports);
          const restored=JSON.parse(JSON.stringify(saved)).reduce((acc,d)=>recordArticleDecision(acc,d,reports),[]);
          console.log(JSON.stringify({saved,restored,unchanged:JSON.stringify(reports)===before}));
        ''')
        self.assertTrue(result['unchanged'])
        self.assertEqual(result['saved'], result['restored'])
        self.assertEqual(len(result['saved']), 2)
        actual = next(d for d in result['saved'] if d['article'] == 'ART-004')
        self.assertEqual(actual['choice'], 'Investigate')
        self.assertEqual(actual['support'], ['age', 'position'])
        self.assertEqual(actual['supporting_cells'][0]['status'], 'Different')

    def test_article_decision_controls_keep_cell_marks_and_export_separate(self):
        for choice in ('Not our person', 'Our person, not relevant', 'Need more info', 'Investigate'):
            self.assertIn(choice, self.html)
        self.assertIn('A Different on role or employer alone is weak evidence. A Different on age or a hard identifier is strong.', self.html)
        self.assertIn('Tick the row chips that support your reason', self.html)
        self.assertIn('cell_marks:decisions,article_decisions:articleDecisions', self.html)
        self.assertIn('localStorage.setItem(articleStorageKey', self.html)
        self.assertIn('recordArticleDecision(articleDecisions, d, data.reports)', self.html)

    def test_base_event_groups_join_only_confirmed_links_not_raw_event_ids(self):
        for report in self.reports:
            groups = dashboard.event_groups(report)
            confirmed = [link for link in report['links'] if link['tier'] == 'CONFIRMED']
            self.assertEqual(len(groups), len(report['comparisons']) - len(confirmed))
            self.assertEqual(sorted(aid for g in groups for aid in g['article_ids']),
                             sorted(a['article_id'] for a in report['comparisons']))
            for group in groups:
                self.assertEqual(len(group['marks']), len(group['article_ids']))
                if len(group['article_ids']) > 1:
                    self.assertEqual(set(group['article_ids']),
                                     {aid for link in confirmed for aid in
                                      (link['article_id'], link['to_article_id'])})
        groups = dashboard.event_groups(self.reports[2])
        linked = next(g for g in groups if g['event_id'] == 'EVT-007')
        self.assertEqual(linked['article_ids'], ['ART-007', 'ART-009'])
        self.assertIn("group.scope='colgroup'", self.html)
        self.assertIn('group.colSpan=event.article_ids.length', self.html)

    def test_timeline_dates_and_source_sentences_and_labels_are_copied(self):
        for report in self.reports:
            groups = dashboard.event_groups(report)
            articles = {a['article_id']: a for a in report['comparisons']}
            self.assertEqual(sum(len(g['marks']) for g in groups), len(articles))
            findings = {r['article_id']: r for r in report['findings']}
            findings.update({r['resolution']['article_id']: r['resolution'] for r in report['findings'] if 'resolution' in r})
            for group in groups:
                self.assertEqual([m['date'] for m in group['marks']], sorted(m['date'] for m in group['marks']))
                for mark in group['marks']:
                    article = articles[mark['article_id']]
                    self.assertEqual(mark['date'], article['date'])
                    self.assertIn(mark['source_sentence'], research.sentences(article['body']))
                    if mark['article_id'] not in findings:
                        self.assertEqual(mark['line'], article['headline'])
                    else:
                        record = findings[mark['article_id']]
                        self.assertEqual(mark['source_sentence'], record['quote'])
                        label = 'reported delisting' if record.get('state') == 'reported delisting' else record['event']
                        self.assertTrue(mark['line'].startswith(label))
                        if ' · ' in mark['line']:
                            self.assertIn(mark['line'].split(' · ', 1)[1], record['quote'])
        self.assertLess(self.html.index('id="timeline"'), self.html.index('id="comparison"'))
        self.assertIn('openArticle(article,null,b,mark.source_sentence)', self.html)

    def test_timeline_closure_and_unknown_status_endings_use_report_not_clock(self):
        closed = next(g for g in dashboard.event_groups(self.reports[2]) if g['event_id'] == 'EVT-007')
        self.assertEqual(closed['ending'], 'case closed')
        unknown = next(g for g in dashboard.event_groups(self.reports[3]) if g['event_id'] == 'EVT-016')
        self.assertEqual(unknown['ending'], 'Dated finding, no follow-up found in supplied sources, status unknown.')
        ordinary = next(g for g in dashboard.event_groups(self.reports[1]) if g['event_id'] == 'EVT-019')
        self.assertIsNone(ordinary['ending'])

    def test_timeline_is_stable_when_comparisons_are_reordered(self):
        report = copy.deepcopy(self.reports[2])
        report['comparisons'].reverse()
        self.assertEqual(dashboard.event_groups(report), dashboard.event_groups(self.reports[2]))

    def test_phone_controls_show_one_article_without_rewriting_cells(self):
        for text in ('id="article-picker"', 'id="previous-article"', 'id="next-article"',
                     '.media-col:not(.selected)', 'table { width:100%; }',
                     "n.dataset.article===id", 'phone.addEventListener'):
            self.assertIn(text, self.html)
        self.assertIn("table.append(el('colgroup'))", self.html)
        self.assertIn("$('comparison').scrollLeft=0", self.html)

    def test_namesake_still_excluded_and_age_is_a_real_differentiator(self):
        article = self.article('SUB-002', 'ART-004')
        self.assertEqual(article['fields']['name']['status'], 'Same')
        self.assertEqual(article['fields']['age']['value'], '67')
        self.assertEqual(article['fields']['age']['subject_value'], '39')
        self.assertEqual(article['fields']['age']['status'], 'Different')
        self.assertEqual(article['fields']['position']['status'], 'Different')
        self.assertIn('Exclude', article['verdict'])

    def test_age_agrees_only_where_stated(self):
        self.assertEqual(self.article('SUB-002', 'ART-006')['fields']['age']['status'], 'Same')
        cell = self.article('SUB-002', 'ART-005')['fields']['age']
        self.assertIsNone(cell['value'])
        self.assertEqual(cell['status'], 'Not stated')

    def test_age_uses_article_date_not_run_date(self):
        self.assertEqual(self.article('SUB-002', 'ART-020')['fields']['age']['subject_value'], '38')
        self.assertEqual(self.article('SUB-002', 'ART-006')['fields']['age']['subject_value'], '39')

    def test_age_birthday_boundary_and_leap_day(self):
        subject = self.subjects[1]
        self.assertEqual(research.age_at(subject, '2026-04-15'), '38')
        self.assertEqual(research.age_at(subject, '2026-04-16'), '39')
        leap = {**subject, 'date_of_birth': '2000-02-29'}
        self.assertEqual(research.age_at(leap, '2025-02-28'), '24')
        self.assertEqual(research.age_at(leap, '2025-03-01'), '25')
        with self.assertRaises(ValueError):
            research.age_at(subject, '1900-01-01')

    def test_company_key_people_are_stated_not_inferred(self):
        fields = self.article('SUB-001', 'ART-003')['fields']
        self.assertEqual(set(fields), {'name', 'profile', 'key_people'})
        self.assertEqual(fields['key_people']['value'], 'Lim Chuen Vek')
        self.assertEqual(fields['key_people']['source_sentence'], 'Its director is Lim Chuen Vek.')
        self.assertEqual(fields['key_people']['status'], 'Same')
        self.assertIsNone(self.article('SUB-001', 'ART-001')['fields']['key_people']['value'])

    def test_person_profile_is_explicit_and_not_inferred_from_role(self):
        self.assertEqual(self.article('SUB-002', 'ART-005')['fields']['profile']['status'], 'Same')
        self.assertEqual(self.article('SUB-002', 'ART-004')['fields']['profile']['status'], 'Different')
        self.assertIsNone(self.article('SUB-002', 'ART-006')['fields']['profile']['value'])

    def test_unstated_employer_is_not_guessed_from_other_mentions(self):
        fields = self.extract(self.subjects[3], 'Ravi Selvam, a commodity trader, attended a talk. MNO Bunkering Pte. Ltd. sponsored it.')
        self.assertEqual(fields['position']['value'], 'commodity trader')
        self.assertIn('Employer not stated', fields['position']['comparison_note'])
        self.assertNotIn('MNO', fields['position']['value'])

    def test_missing_context_never_copies_subject_values(self):
        fields = self.extract(self.subjects[1], 'Tan Wei Quen attended a model display.')
        for field in ('profile', 'age', 'position'):
            self.assertEqual(fields[field]['status'], 'Not stated')
            self.assertIsNone(fields[field]['value'])

    def test_namesake_and_follow_up_both_have_different_stated_age(self):
        different = [a['article_id'] for r in self.reports for a in r['comparisons']
                     if a['fields'].get('age', {}).get('status') == 'Different']
        self.assertEqual(different, ['ART-004', 'ART-026'])

    def test_original_verdicts_are_kept_including_linked_closure(self):
        for report in self.reports:
            by_id = {a['article_id']: a for a in report['comparisons']}
            for finding in report['findings']:
                self.assertEqual(by_id[finding['article_id']]['verdict'], finding['assessment'])
                if 'resolution' in finding:
                    self.assertEqual(by_id[finding['resolution']['article_id']]['verdict'], finding['assessment'])
            for exclusion in report['excluded_articles']:
                self.assertEqual(by_id[exclusion['article_id']]['verdict'], exclusion['reason'])

    def test_sources_keep_execution_result_freshness_and_snapshot_separate(self):
        article = self.article('SUB-004', 'ART-017')
        self.assertEqual(article['source_status'], {'execution': 'completed', 'result': 'possible hit',
                         'freshness': 'stale', 'as_of': '2025-09-01'})

    def test_pages_and_reports_do_not_expose_private_identifiers_or_places(self):
        output = self.html + json.dumps(self.reports) + ''.join(research.render(r) + page.render_page(r, 'local.json') for r in self.reports)
        self.assertNotRegex(output, r'(?i)district|\bcity\b|registration[_ ]number|date[_ ]of[_ ]birth|\bdob\b|SYN-SG-')
        for subject in self.subjects:
            for field in ('date_of_birth', 'registration_number'):
                if field in subject:
                    self.assertNotIn(subject[field], output)
        # Owner deny list is test data, never displayed in output.
        for term in ('Jurong', 'Woodlands', 'Tuas', 'Pasir Panjang', 'Singapore'):
            self.assertNotIn(term.casefold(), output.casefold())

    def test_renderer_is_deterministic_and_leaves_reports_unchanged(self):
        before = copy.deepcopy(self.reports)
        self.assertEqual(self.html, dashboard.render_dashboard(self.reports))
        self.assertEqual(before, self.reports)

    def test_saved_current_pages_and_reports_have_no_private_fields_or_places(self):
        phase4 = ROOT / 'evidence/phase-4'
        outputs = [p for p in phase4.rglob('*') if p.is_file() and p.suffix == '.html'
                   or p.is_file() and 'reports' in p.parts and p.suffix in ('.json', '.md')]
        self.assertTrue(outputs)
        for path in outputs:
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotRegex(text, r'(?i)district|\bcity\b|registration[_ ]number|date[_ ]of[_ ]birth|SYN-SG-')
                for term in ('Jurong', 'Woodlands', 'Tuas', 'Pasir Panjang', 'Singapore'):
                    self.assertNotIn(term.casefold(), text.casefold())
                for subject in self.subjects:
                    for key in ('date_of_birth', 'registration_number'):
                        if key in subject:
                            self.assertNotIn(subject[key], text)

    def test_renderer_rejects_filled_missing_cells_and_ungrounded_evidence(self):
        for key, value in (('value', 'Guessed'), ('source_sentence', 'Invented sentence.')):
            reports = copy.deepcopy(self.reports)
            cell = reports[1]['comparisons'][1]['fields']['age']
            cell[key] = value
            with self.assertRaises(ValueError):
                dashboard.render_dashboard(reports)
        reports = copy.deepcopy(self.reports)
        reports[1]['comparisons'][0]['fields']['name']['source_sentence'] = 'Invented sentence.'
        with self.assertRaises(ValueError):
            dashboard.render_dashboard(reports)

    def test_no_external_resources_and_browser_storage_is_local(self):
        self.assertNotRegex(self.html, r'https?://|@import|url\s*\(')
        for required in ("default-src 'none'", "connect-src 'none'", 'localStorage.setItem',
                         'Copy my decisions', 'source-sentence', 'scrollIntoView', 'showModal'):
            self.assertIn(required, self.html)

    def test_untrusted_html_cannot_break_out_of_json_data_block(self):
        reports = copy.deepcopy(self.reports)
        reports[0]['subject']['name'] = '</script><img src=x onerror=alert(1)>'
        html = dashboard.render_dashboard(reports)
        self.assertNotIn('<img', html)
        self.assertEqual(html.count('</script>'), 2)
        data = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(json.loads(data[1])['reports'][0]['subject']['name'], reports[0]['subject']['name'])

    def test_cli_writes_real_dashboard_and_fails_without_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for report in self.reports:
                (folder / (report['subject']['id'] + '.json')).write_text(json.dumps(report))
            out = folder / 'dashboard.html'
            command = [sys.executable, str(SCRIPTS / 'render_dashboard.py'), '--reports', str(folder), '--out', str(out)]
            proc = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(out.read_text(), self.html)
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'render_dashboard.py'), '--reports', tmp,
                                   '--out', str(Path(tmp) / 'dashboard.html')], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertFalse((Path(tmp) / 'dashboard.html').exists())


if __name__ == '__main__':
    unittest.main()
