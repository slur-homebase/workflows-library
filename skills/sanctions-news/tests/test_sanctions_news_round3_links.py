"""Text-grounded relationship gates and non-application of suggestions."""

import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures'
SCRIPTS = ROOT / 'scripts'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


research = load('round3_links_research', 'research.py')
dashboard = load('round3_links_dashboard', 'render_dashboard.py')
page = load('round3_links_page', 'render_page.py')


def without_annotations(value):
    if isinstance(value, dict):
        return {key: without_annotations(item) for key, item in value.items()
                if key not in ('link', 'links')}
    if isinstance(value, list):
        return [without_annotations(item) for item in value]
    return value


class Round3LinksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subjects = research.read_json(FIXTURES / 'subjects.json')['subjects']
        cls.sources = research.read_json(FIXTURES / 'sources.json')['sources']
        cls.articles = {p.stem: research.read_article(p)
                        for p in sorted((FIXTURES / 'articles').glob('*.md'))}
        cls.reports = {s['id']: research.research(s['id'], FIXTURES) for s in cls.subjects}

    def candidate(self, sid, aid):
        article = self.articles[aid]
        subject = next(s for s in self.subjects if s['id'] == sid)
        quote = next(sentence for sentence in research.sentences(article['body'])
                     if subject['name'] in sentence)
        source = next(s for s in self.sources if s['id'] == article['source_id'])
        return {'article_id': aid, 'date': article['date'], 'quote': quote,
                'body': article['body'], 'event': research.classify(quote),
                'source': source['name'],
                'identity_check': research.identity(subject, quote, article['date'])}

    def test_new_front_matter_is_json_valid_under_completed_snapshot(self):
        sources = {s['id']: s for s in self.sources}
        for number in range(21, 30):
            article = self.articles['ART-%03d' % number]
            lines = (FIXTURES / article['fixture_file']).read_text().splitlines()
            end = lines.index('---', 1)
            metadata = dict((key, json.loads(value)) for key, value in
                            (line.split(': ', 1) for line in lines[1:end]))
            self.assertEqual(set(metadata), {'id', 'source_id', 'date', 'headline',
                                             'subject_ids', 'part_in_story', 'stage', 'event_id'})
            source = sources[metadata['source_id']]
            self.assertEqual(source['execution'], 'completed')
            self.assertLessEqual(metadata['date'], source['as_of'])
            self.assertNotRegex(article['body'], r'ART-\d|first reported|earlier report|previous report')

    def test_every_reason_recomputed_from_exact_article_sentences(self):
        # Use the declared stop-word policy, but independently tokenize and
        # subtract evidence. Do not call matter_words or article_links here.
        words = lambda text: set(re.findall(r'(?i)\b[a-z]{4,}\b', text.lower()))
        outlet_words = set().union(*(words(s['name']) for s in self.sources))
        self.assertTrue({'according', 'sanctions', 'investigating', 'name', 'settle'}
                        <= research.MATTER_STOP_WORDS)
        for subject in self.subjects:
            report = self.reports[subject['id']]
            for link in report['links']:
                earlier = self.candidate(subject['id'], link['to_article_id'])
                later = self.candidate(subject['id'], link['article_id'])
                with self.subTest(pair=(earlier['article_id'], later['article_id'])):
                    self.assertEqual(earlier['identity_check']['decision'], 'matched')
                    self.assertEqual(later['identity_check']['decision'], 'matched')
                    self.assertLess(earlier['date'], later['date'])
                    authority = next(reason.removeprefix('Same authority: ') for reason in link['reasons']
                                     if reason.startswith('Same authority: '))
                    self.assertTrue(all(authority in record['quote'] for record in (earlier, later)))
                    self.assertIn('Matched subject identity: ' + subject['name'], link['reasons'])
                    self.assertIn('Publication date order: ' + earlier['date'] + ' < ' + later['date'], link['reasons'])
                    token_sets, orders = [], []
                    for record in (earlier, later):
                        found_orders = set(re.findall(r'(?:under the|of the) ([A-Z][A-Za-z -]* Order [0-9]{4})', record['quote']))
                        orders.append(found_orders)
                        excluded = words(subject['name']) | outlet_words | words(authority)
                        for order in found_orders:
                            excluded |= words(order)
                        token_sets.append(words(record['quote']) - excluded - research.MATTER_STOP_WORDS)
                    shared = sorted(token_sets[0] & token_sets[1])
                    shared_reasons = [reason for reason in link['reasons'] if reason.startswith('Shared matter words: ')]
                    self.assertEqual(shared_reasons, ['Shared matter words: ' + ', '.join(shared)] if len(shared) >= 3 else [])
                    for token in shared:
                        self.assertGreaterEqual(len(token), 4)
                        self.assertNotIn(token, words(subject['name']) | outlet_words | research.MATTER_STOP_WORDS)
                    common_orders = orders[0] & orders[1]
                    self.assertEqual([r.removeprefix('Same legal order: ') for r in link['reasons']
                                      if r.startswith('Same legal order: ')], sorted(common_orders))
                    self.assertTrue(common_orders or len(shared) >= 3)
                    if link['tier'] == 'CONFIRMED':
                        self.assertTrue(research.same_case(earlier, later))
                    else:
                        self.assertEqual(link['tier'], 'SUGGESTED')
                        self.assertFalse(research.same_case(earlier, later))

    def test_link_computation_never_changes_counts_summary_rows_or_source_results(self):
        for subject in self.subjects:
            sid = subject['id']
            with patch.object(research, 'article_links', side_effect=AssertionError('disabled')):
                plain = research.research(sid, FIXTURES, compute_links=False)
            linked = self.reports[sid]
            self.assertEqual(len(plain['findings']), len(linked['findings']))
            self.assertEqual(plain['summary'], linked['summary'])
            self.assertEqual(without_annotations(plain), without_annotations(linked))
            self.assertEqual(page.answer_counts(plain), page.answer_counts(linked))
            self.assertEqual(page.answer_sentence(plain), page.answer_sentence(linked))

    def test_only_existing_explicit_closure_is_confirmed(self):
        links = [link for report in self.reports.values() for link in report['links']]
        self.assertEqual(len(links), 17)
        self.assertEqual(sum(link['tier'] == 'SUGGESTED' for link in links), 16)
        self.assertEqual([(l['article_id'], l['to_article_id']) for l in links if l['tier'] == 'CONFIRMED'],
                         [('ART-009', 'ART-007')])
        old = self.candidate('SUB-003', 'ART-007')
        later = self.candidate('SUB-003', 'ART-009')
        self.assertTrue(research.same_case(old, later))
        for mutation in ('reference', 'authority', 'order', 'date'):
            changed = copy.deepcopy(later)
            if mutation == 'reference':
                changed['body'] = changed['quote']
            elif mutation == 'authority':
                changed['quote'] = changed['quote'].replace('Enforcement Agency C', 'Enforcement Agency Z')
            elif mutation == 'order':
                changed['quote'] = changed['quote'].replace('Vessel Services Order 2024', 'Quay Services Order 2024')
            else:
                changed['date'] = old['date']
            self.assertFalse(research.same_case(old, changed), mutation)
        changed = {**later, 'body': later['quote']}
        subject = next(s for s in self.subjects if s['id'] == 'SUB-003')
        link = research.article_links([old, changed], subject, [s['name'] for s in self.sources])[0]
        self.assertEqual(link['tier'], 'SUGGESTED')

    def test_suggestion_gates_do_not_use_event_ids_or_possible_identity(self):
        old = self.candidate('SUB-001', 'ART-002')
        later = self.candidate('SUB-001', 'ART-021')
        subject = self.subjects[0]
        outlets = [s['name'] for s in self.sources]
        self.assertEqual(len(research.article_links([old, later], subject, outlets)), 1)
        for decision in ('insufficient', 'excluded'):
            for index in (0, 1):
                records = copy.deepcopy([old, later])
                records[index]['identity_check']['decision'] = decision
                self.assertEqual(research.article_links(records, subject, outlets), [])
        changed = {**later, 'quote': later['quote'].replace('Customs Agency A', 'Customs Agency Z')}
        self.assertEqual(research.article_links([old, changed], subject, outlets), [])
        # With neither legal-order overlap nor three words, no recency-only link.
        changed = {**later, 'quote': 'The Customs Agency A said ABC Components Pte. Ltd. faces a sanctions investigation over gemstones.'}
        self.assertEqual(research.article_links([old, changed], subject, outlets), [])
        changed = {**later, 'date': old['date']}
        self.assertEqual(research.article_links([old, changed], subject, outlets), [])

    def test_three_unique_word_threshold_and_same_order_alternative(self):
        old = self.candidate('SUB-001', 'ART-002')
        later = self.candidate('SUB-001', 'ART-021')
        subject, outlets = self.subjects[0], [s['name'] for s in self.sources]
        prefix = 'The Customs Agency A said ABC Components Pte. Ltd. '
        # Explicit hand-authored unit inputs isolate the lexical threshold.
        earlier = {**old, 'quote': prefix + 'copper cargoes storage.'}
        for phrase, expected in (('copper cargoes cargoes cargoes.', 0),
                                 ('copper cargoes storage.', 1)):
            newer = {**later, 'quote': prefix + phrase}
            self.assertEqual(len(research.article_links([earlier, newer], subject, outlets)), expected)
        earlier['quote'] = prefix + 'copper under the Cargo Handling Order 2026.'
        newer = {**later, 'quote': prefix + 'gemstones under the Cargo Handling Order 2026.'}
        links = research.article_links([earlier, newer], subject, outlets)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['tier'], 'SUGGESTED')
        self.assertIn('Same legal order: Cargo Handling Order 2026', links[0]['reasons'])
        self.assertFalse(any(r.startswith('Shared matter words: ') for r in links[0]['reasons']))

    def test_decoy_is_suggested_not_confirmed_and_no_namesake_or_stale_links(self):
        links = [link for report in self.reports.values() for link in report['links']]
        decoys = [l for l in links if l['article_id'] == 'ART-023']
        self.assertEqual(len(decoys), 3)
        self.assertTrue(all(l['tier'] == 'SUGGESTED' for l in decoys))
        self.assertTrue(all(not any(r.startswith('Same legal order: ') for r in l['reasons']) for l in decoys))
        self.assertFalse(any({'ART-004', 'ART-026', 'ART-017'} & {l['article_id'], l['to_article_id']} for l in links))
        old = next(f for f in self.reports['SUB-004']['findings'] if f['article_id'] == 'ART-017')
        self.assertEqual(old['state'], 'historical status unknown')
        self.assertNotIn('resolution', old)

    def test_suggested_delisting_does_not_close_prior_case_in_any_view(self):
        report = self.reports['SUB-002']
        self.assertFalse(any('resolution' in f for f in report['findings']))
        self.assertFalse(any(f['state'] == 'cleared' for f in report['findings']))
        self.assertNotIn('earlier case is closed', page.answer_sentence(report))
        for group in dashboard.event_groups(report):
            self.assertNotEqual(group['ending'], 'case closed')
            for mark in group['marks']:
                self.assertNotIn('case closed', mark['line'])
        for aid in ('ART-025', 'ART-029'):
            finding = next(f for f in report['findings'] if f['article_id'] == aid)
            self.assertEqual(finding['state'], 'reported delisting')
            self.assertTrue(finding['article_context'])


if __name__ == '__main__':
    unittest.main()
