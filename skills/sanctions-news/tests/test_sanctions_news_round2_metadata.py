"""Round-2 source metadata and evidence carry-through; offline, stdlib only."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures'
FROZEN = ROOT / 'evidence/phase-3/fixtures-v1'
SCRIPTS = ROOT / 'scripts'
SPEC = importlib.util.spec_from_file_location('round2_research', SCRIPTS / 'research.py')
assert SPEC and SPEC.loader
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)
BASE_FIELDS = {'id', 'source_id', 'date', 'headline', 'subject_ids'}
STORY_FIELDS = {'part_in_story', 'stage', 'event_id'}
EXPECTED = {
    'ART-001': ('sanctioned', 'designation or restriction', 'EVT-001'),
    'ART-002': ('under investigation', 'investigation', 'EVT-002'),
    'ART-003': ('mentioned only', 'not stated', 'EVT-003'),
    'ART-004': ('under investigation', 'investigation', 'EVT-004'),
    'ART-005': ('mentioned only', 'not stated', 'EVT-005'),
    'ART-006': ('sanctioned', 'designation or restriction', 'EVT-006'),
    'ART-007': ('under investigation', 'investigation', 'EVT-007'),
    'ART-008': ('mentioned only', 'not stated', 'EVT-008'),
    # A cleared subject is not currently accused/investigated/sanctioned. The
    # allowed role vocabulary has no "cleared" role; do not invent one.
    'ART-009': ('not stated', 'case closed', 'EVT-007'),
    'ART-010': ('under investigation', 'investigation', 'EVT-009'),
    'ART-011': ('mentioned only', 'not stated', 'EVT-010'),
    'ART-012': ('mentioned only', 'not stated', 'EVT-011'),
    'ART-013': ('mentioned only', 'not stated', 'EVT-012'),
    'ART-014': ('mentioned only', 'not stated', 'EVT-013'),
    'ART-015': ('mentioned only', 'not stated', 'EVT-014'),
    'ART-016': ('mentioned only', 'not stated', 'EVT-015'),
    'ART-017': ('under investigation', 'investigation', 'EVT-016'),
    'ART-018': ('mentioned only', 'not stated', 'EVT-017'),
    'ART-019': ('mentioned only', 'not stated', 'EVT-018'),
    'ART-020': ('mentioned only', 'not stated', 'EVT-019'),
}


def frontmatter(path):
    """Independent fixture schema check: no production-parser assumptions."""
    lines = path.read_text(encoding='utf-8').splitlines()
    end = lines.index('---', 1)
    return dict((key, json.loads(value)) for key, value in
                (line.split(': ', 1) for line in lines[1:end]))


def evidence_records(report):
    for group in ('findings', 'possible_matches', 'excluded_articles', 'non_events'):
        for record in report[group]:
            yield record
            if 'resolution' in record:
                yield record['resolution']


class Round2MetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = {p.stem: research.read_article(p)
                        for p in sorted((FIXTURES / 'articles').glob('*.md'))}
        cls.subjects = research.read_json(FIXTURES / 'subjects.json')['subjects']
        cls.reports = [research.research(s['id'], FIXTURES) for s in cls.subjects]

    def write_article(self, folder, meta, body=None):
        path = Path(folder) / 'ART-001.md'
        if body is None:
            body = self.articles['ART-001']['body']
        path.write_text('---\n' + ''.join(key + ': ' + json.dumps(value) + '\n'
                                         for key, value in meta.items())
                        + '---\n\n' + body + '\n', encoding='utf-8')
        return path

    def test_all_twenty_have_exactly_three_new_fields_and_expected_source_values(self):
        self.assertEqual({aid for aid in self.articles if aid <= 'ART-020'}, set(EXPECTED))
        for aid, values in EXPECTED.items():
            with self.subTest(article=aid):
                meta = frontmatter(FIXTURES / 'articles' / (aid + '.md'))
                self.assertEqual(set(meta), BASE_FIELDS | STORY_FIELDS)
                self.assertEqual(tuple(meta[f] for f in ('part_in_story', 'stage', 'event_id')), values)
                self.assertIn(meta['part_in_story'], research.PARTS_IN_STORY)
                self.assertIn(meta['stage'], research.STAGES)
                self.assertRegex(meta['event_id'], r'^EVT-[0-9]{3}$')

    def test_each_stated_category_has_original_full_line_not_mapping_explanation(self):
        for aid, article in self.articles.items():
            context = research.story_context(article)
            self.assertEqual(set(context), STORY_FIELDS | {'story_evidence'})
            self.assertEqual(set(context['story_evidence']), {'part_in_story', 'stage'})
            for field in ('part_in_story', 'stage'):
                with self.subTest(article=aid, field=field):
                    sentence = context['story_evidence'][field]
                    if article[field] == 'not stated':
                        self.assertIsNone(sentence)
                    else:
                        # Each current sample's first full body line supports
                        # its stated category. Never reconstruct dotted names.
                        self.assertEqual(sentence, article['body'].splitlines()[0])
                        self.assertIn(sentence, article['body'].splitlines())
                        self.assertIn(sentence, research.sentences(article['body']))

    def test_closure_shares_only_the_explicitly_linked_event(self):
        opening, closure = (self.articles[aid] for aid in ('ART-007', 'ART-009'))
        self.assertIn('Enforcement Agency C', opening['body'])
        self.assertIn('Enforcement Agency C', closure['body'])
        self.assertIn('Vessel Services Order 2024', opening['body'])
        self.assertIn('Vessel Services Order 2024', closure['body'])
        self.assertIn('inquiry first reported by Business News A on ' + opening['date'], closure['body'])
        self.assertEqual(opening['event_id'], closure['event_id'])
        self.assertEqual(len({a['event_id'] for aid, a in self.articles.items() if aid in EXPECTED}), 19)
        # ABC's designation and Customs inquiry have different authorities;
        # Ravi's maritime and free-port inquiries have different matters too.
        self.assertNotEqual(self.articles['ART-001']['event_id'], self.articles['ART-002']['event_id'])
        self.assertNotEqual(self.articles['ART-010']['event_id'], self.articles['ART-017']['event_id'])
        self.assertNotEqual(self.articles['ART-004']['event_id'], self.articles['ART-006']['event_id'])

    def test_comparisons_and_all_evidence_record_groups_carry_source_metadata(self):
        seen_comparisons, seen_evidence = set(), set()
        for report in self.reports:
            for record in [*report['comparisons'], *evidence_records(report)]:
                aid = record['article_id']
                context = research.story_context(self.articles[aid])
                for field, value in context.items():
                    self.assertEqual(record[field], value, (aid, field))
                if 'fields' in record:
                    seen_comparisons.add(aid)
                    expected = ({'name', 'profile', 'age', 'position'}
                                if report['subject']['type'] == 'person'
                                else {'name', 'profile', 'key_people'})
                    self.assertEqual(set(record['fields']), expected)
                else:
                    seen_evidence.add(aid)
        self.assertEqual(seen_comparisons, set(self.articles))
        self.assertEqual(seen_evidence, set(self.articles))
        report = next(r for r in self.reports if r['subject']['id'] == 'SUB-003')
        finding = report['findings'][0]
        self.assertEqual(finding['event_id'], finding['resolution']['event_id'])
        self.assertEqual(finding['stage'], 'investigation')
        self.assertEqual(finding['resolution']['stage'], 'case closed')

    def test_possible_matches_also_keep_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            fixtures = Path(folder) / 'fixtures'
            shutil.copytree(FIXTURES, fixtures)
            path = fixtures / 'articles/ART-006.md'
            path.write_text(path.read_text().replace(', 39, nominee director at JKL Trading Pte. Ltd.,', ''),
                            encoding='utf-8')
            report = research.research('SUB-002', fixtures)
            record = report['possible_matches'][0]
            self.assertEqual(record['part_in_story'], 'sanctioned')
            self.assertEqual(record['stage'], 'designation or restriction')
            self.assertEqual(record['event_id'], 'EVT-006')
            self.assertIn(record['story_evidence']['part_in_story'], research.read_article(path)['body'].splitlines())

    def test_not_stated_metadata_is_never_overridden_by_body_classification(self):
        article = {**self.articles['ART-001'], 'part_in_story': 'not stated',
                   'stage': 'not stated', 'event_id': 'EVT-099'}
        with patch.object(research, 'classify', side_effect=AssertionError('not a story metadata source')):
            context = research.story_context(article)
        self.assertEqual(context, {'part_in_story': 'not stated', 'stage': 'not stated',
                                   'event_id': 'EVT-099',
                                   'story_evidence': {'part_in_story': None, 'stage': None}})
        source = {'id': 'SRC-001', 'name': 'Business News A'}
        self.assertEqual(research.evidence(article, article['body'].splitlines()[0], source)['event_id'], 'EVT-099')

    def test_category_without_support_does_not_fabricate_evidence_or_reclassify(self):
        article = {**self.articles['ART-003'], 'part_in_story': 'witness', 'stage': 'charge'}
        context = research.story_context(article)
        self.assertEqual(context['part_in_story'], 'witness')
        self.assertEqual(context['stage'], 'charge')
        self.assertEqual(context['story_evidence'], {'part_in_story': None, 'stage': None})

    def test_supported_optional_vocabulary_also_uses_verbatim_lines(self):
        cases = [
            ('accused', 'allegation', 'An invented office accused Person A of evasion.'),
            ('witness', 'charge', 'Person A testified as a witness after Person B was charged.'),
            ('sued someone', 'not stated', 'Person A sued Company B over a contract.'),
        ]
        for role, stage, line in cases:
            article = {**self.articles['ART-001'], 'part_in_story': role, 'stage': stage, 'body': line}
            context = research.story_context(article)
            self.assertEqual(context['story_evidence']['part_in_story'], line)
            self.assertEqual(context['story_evidence']['stage'], None if stage == 'not stated' else line)

    def test_parser_rejects_partial_extra_duplicate_and_invalid_metadata(self):
        original = frontmatter(FIXTURES / 'articles/ART-001.md')
        invalid = []
        for field in STORY_FIELDS:
            meta = dict(original)
            del meta[field]
            invalid.append(meta)
        invalid.append({**original, 'part_in_story_evidence': 'No fourth source field allowed.'})
        for field, values in {
            'part_in_story': ['plaintiff', 'Sanctioned', None, [], {}],
            'stage': ['conviction', 'Investigation', None, [], {}],
            'event_id': ['EVT-1', 'EVT-001x', ' EVT-001', 'EVT-001\n', 'EVT-１２３', None, [], {}],
        }.items():
            invalid.extend({**original, field: value} for value in values)
        with tempfile.TemporaryDirectory() as folder:
            for meta in invalid:
                with self.subTest(meta=meta), self.assertRaises(ValueError):
                    research.read_article(self.write_article(folder, meta))
            path = self.write_article(folder, original)
            path.write_text(path.read_text().replace('event_id: "EVT-001"',
                                                    'event_id: "EVT-001"\nevent_id: "EVT-002"'))
            with self.assertRaisesRegex(ValueError, 'Repeated field'):
                research.read_article(path)

    def test_legacy_parser_and_frozen_evidence_stay_metadata_free(self):
        paths = sorted((FROZEN / 'articles').glob('*.md'))
        self.assertEqual(len(paths), 20)
        for path in paths:
            self.assertEqual(set(frontmatter(path)), BASE_FIELDS)
            article = research.read_article(path)
            self.assertEqual(research.story_context(article), {})
            self.assertTrue(STORY_FIELDS.isdisjoint(article))
        for subject in research.read_json(FROZEN / 'subjects.json')['subjects']:
            report = research.research(subject['id'], FROZEN)
            self.assertEqual(report['skill_version'], '0.3')
            for record in evidence_records(report):
                self.assertTrue((STORY_FIELDS | {'story_evidence'}).isdisjoint(record))

    def test_metadata_cannot_change_identity_cells_verdicts_or_coverage(self):
        # Compare the exact current bodies against a metadata-free copy; the
        # only permitted report differences are the new carry-through keys.
        with tempfile.TemporaryDirectory() as folder:
            fixtures = Path(folder) / 'fixtures'
            shutil.copytree(FIXTURES, fixtures)
            for path in (fixtures / 'articles').glob('*.md'):
                text = path.read_text(encoding='utf-8')
                lines = text.splitlines(keepends=True)
                end = lines.index('---\n', 1)
                text = ''.join(line for index, line in enumerate(lines)
                               if not (0 < index < end and line.split(': ', 1)[0] in STORY_FIELDS))
                path.write_text(text, encoding='utf-8')
            for original in self.reports:
                report = copy.deepcopy(original)
                for record in [*report['comparisons'], *evidence_records(report)]:
                    for key in STORY_FIELDS | {'story_evidence'}:
                        record.pop(key)
                self.assertEqual(report['skill_version'], '0.5')
                report['skill_version'] = '0.3'
                self.assertEqual(report, research.research(report['subject']['id'], fixtures))


if __name__ == '__main__':
    unittest.main()
