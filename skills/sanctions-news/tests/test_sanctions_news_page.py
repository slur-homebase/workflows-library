"""Offline findings-page checks. Invented fixtures only; no browser dependency."""

import copy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures'
SCRIPTS = ROOT / 'scripts'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


research = load('page_research', 'research.py')
page = load('sanctions_page', 'render_page.py')


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

    def outside_details(self):
        if self.tag in {'details', 'head'}:
            return ''
        return ''.join(c.outside_details() if isinstance(c, Node) else c for c in self.children)

    def select(self, tag=None, css=None):
        result = []
        if (tag is None or self.tag == tag) and (css is None or css in self.attrs.get('class', '').split()):
            result.append(self)
        for child in self.children:
            if isinstance(child, Node):
                result.extend(child.select(tag, css))
        return result


class DOM(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'meta', 'br', 'link', 'img', 'input', 'hr', 'source', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if len(self.stack) > 1 and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class SanctionsNewsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {f'SUB-{n:03d}': research.research(f'SUB-{n:03d}', FIXTURES) for n in range(1, 6)}
        cls.pages = {sid: page.render_page(r, 'reports/' + sid + '.json', 'a' * 40)
                     for sid, r in cls.reports.items()}
        cls.doms = {sid: DOM(html).root for sid, html in cls.pages.items()}

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / 'render_page.py'), *map(str, args)],
                              capture_output=True, text=True)

    def write_reports(self, folder):
        for sid, report in self.reports.items():
            (folder / (sid + '.json')).write_text(json.dumps(report), encoding='utf-8')

    def test_every_report_renders_through_single_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_reports(folder)
            for sid in self.reports:
                out = folder / (sid + '.html')
                proc = self.cli('--report', folder / (sid + '.json'), '--out', out)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(out.read_text().startswith('<!doctype html>'))
                self.assertIn(self.reports[sid]['subject']['name'], out.read_text())

    def test_all_cli_renders_five_pages_and_linked_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_reports(folder)
            proc = self.cli('--all', folder)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(len(list(folder.glob('*.html'))), 6)
            index = DOM((folder / 'index.html').read_text()).root
            self.assertEqual(len(index.select('a')), 6)
            for sid, report in self.reports.items():
                self.assertIn(report['summary'], index.text())
                self.assertTrue((folder / (sid + '.html')).is_file())
                self.assertIn(sid + '.html', [a.attrs['href'] for a in index.select('a')])

    def test_timeline_is_the_first_landing_action_and_visible_above_findings_answers(self):
        html = page.render_index([(Path(sid + '.json'), r) for sid, r in self.reports.items()])
        root = DOM(html).root
        link = root.select('a')[0]
        self.assertEqual(link.attrs['href'], 'dashboard.html')
        self.assertEqual(link.text(), 'Open the dashboard and news timeline')
        self.assertIn(link.text(), root.outside_details())
        self.assertIn('Choose a subject, then click a dated timeline mark to read the source sentence.',
                      root.outside_details())
        self.assertLess(html.index('Open the dashboard'), html.index('<div class="cards">'))
        for sid, html in self.pages.items():
            with self.subTest(subject=sid):
                root = self.doms[sid]
                link = root.select('a')[0]
                self.assertEqual(link.attrs['href'], 'dashboard.html#' + sid)
                self.assertEqual(link.text(), 'Open this subject in the news timeline')
                self.assertIn(link.text(), root.outside_details())
                self.assertLess(html.index('Invented sample data.'), html.index(link.text()))
                self.assertLess(html.index(link.text()), html.index('<section class="answer">'))

    def test_headline_summary_is_verbatim_in_every_page(self):
        for sid, report in self.reports.items():
            self.assertEqual(self.doms[sid].select(css='headline')[0].text(), report['summary'])
            # Inline type spans must not alter the copied sentence.
            self.assertIn(report['summary'], self.doms[sid].text())

    def test_header_includes_name_date_scope_and_human_decision(self):
        for sid, report in self.reports.items():
            header = self.doms[sid].select('header')[0].text()
            for required in (report['subject']['name'], page.display_date(report['as_of'])):
                self.assertIn(required, header)
            for required in (report['as_of'], 'Invented sample data. No live news search or sanctions-list check.',
                             'Human review required. The tool chooses no disposition.'):
                self.assertIn(required, self.doms[sid].text())

    def test_all_five_sources_have_three_separate_labels_and_dates(self):
        for sid, report in self.reports.items():
            blocks = self.doms[sid].select(css='source')
            self.assertEqual(len(blocks), 5)
            for source, block in zip(report['sources'], blocks):
                self.assertIn(source['source_id'], block.text())
                self.assertIn(source['source'], block.text())
                labels = block.select(css='label')
                self.assertEqual(len(labels), 3)
                for field, label in zip(('execution', 'result', 'freshness'), labels):
                    self.assertEqual(label.attrs['data-label'], field)
                    self.assertIn(field + ': ' + source[field], label.text())
                    self.assertIn('as_of: ' + source['field_as_of'][field], label.text())
                self.assertIn('as_of: ' + source['as_of'], block.text())

    def test_status_colour_always_has_text_and_keeps_fields_independent(self):
        for root in self.doms.values():
            for label in root.select(css='label'):
                classes = label.attrs['class'].split()
                value = label.text().split(': ', 1)[1].split('as_of:')[0]
                expected = ('good' if value in {'completed', 'current'} else
                            'warn' if value in {'stale', 'possible hit'} else
                            'neutral' if value == 'no hit' else 'bad')
                self.assertIn(expected, classes)
            failed = next(s for s in root.select(css='source') if 'SRC-004' in s.text())
            self.assertIn('execution: failed', failed.text())
            self.assertIn('freshness: current', failed.text())
            self.assertIn('planned date only, nothing read', failed.text())

    def test_every_finding_and_resolution_has_exact_quote_source_article_date(self):
        for sid, report in self.reports.items():
            quotes = [n.text() for n in self.doms[sid].select('blockquote')]
            for record in report['findings']:
                for item in [record] + ([record['resolution']] if 'resolution' in record else []):
                    self.assertIn(item['quote'], quotes)
                    for key in ('date', 'source', 'source_id', 'article_id'):
                        self.assertIn(item[key], self.doms[sid].text())
                self.assertIn(record['identity_check']['identity'], self.doms[sid].text())

    def test_authorities_are_copied_from_quotes_not_renamed(self):
        for report in self.reports.values():
            for record in report['findings']:
                for item in [record] + ([record['resolution']] if 'resolution' in record else []):
                    name = page.authority(item['quote'])
                    self.assertIn(name, item['quote'])
        self.assertEqual(page.authority('No authority is named here.'),
                         'Not stated separately; see exact quote.')

    def test_full_person_identity_line_is_shown(self):
        self.assertIn('matched on name, role, employer and age', self.doms['SUB-002'].text())

    def test_special_terms_have_short_inline_meanings(self):
        self.assertIn('designation (named under a restriction)', self.doms['SUB-002'].text())
        self.assertIn('Entity means company.', self.doms['SUB-001'].text())
        self.assertIn('as_of = the snapshot or planned-check date.', self.doms['SUB-005'].text())
        self.assertIn('(saved code version)', self.doms['SUB-005'].text())

    def test_linked_story_has_both_dates_one_card_and_closed_not_open(self):
        root = self.doms['SUB-003']
        cards = root.select('article', 'linked')
        self.assertEqual(len(cards), 1)
        record = self.reports['SUB-003']['findings'][0]
        self.assertEqual(len(cards[0].select('blockquote')), 2)
        for date in (record['date'], record['resolution']['date']):
            self.assertIn(date, cards[0].text())
        self.assertIn('case closed on ' + record['resolution']['date'], cards[0].text())
        self.assertNotRegex(cards[0].text(), r'(?i)\bopen\b')
        self.assertEqual(len(root.select('article', 'finding')), 0)

    def test_dated_no_follow_up_does_not_claim_current_state(self):
        cards = self.doms['SUB-004'].select('article', 'dated')
        self.assertEqual(len(cards), 1)
        self.assertIn('dated finding, no follow-up found in supplied sources, status unknown', cards[0].text())
        self.assertNotRegex(cards[0].text(), r'(?i)\b(?:open|closed)\b')
        self.assertIn('ART-017', cards[0].text())

    def test_possible_name_only_matches_have_three_equal_unchosen_boxes(self):
        for sid in ('SUB-001', 'SUB-002'):
            report = copy.deepcopy(self.reports[sid])
            record = report['findings'].pop(0)
            record['identity_check'] = research.match_identity(report['subject'], report['subject']['name'], {})
            record['identity_status'] = research.POSSIBLE_IDENTITY
            record['assessment'] = 'Human review required.'
            report['possible_matches'] = [record]
            root = DOM(page.render_page(report, sid + '.json')).root
            section = next(s for s in root.select('section')
                           if s.select('h2') and s.select('h2')[0].text().startswith('Possible matches'))
            boxes = section.select(css='reading')
            expected = research.identity_readings(report['subject'])
            self.assertEqual([b.text() for b in boxes], expected)
            self.assertIn('Tool chooses none.', section.text())
            self.assertEqual(len(section.select('blockquote')), 1)
        self.assertIn('grid-template-columns: repeat(3, minmax(0, 1fr))', page.STYLE)

    def test_partial_identity_findings_also_show_unchosen_readings(self):
        for sid in ('SUB-001', 'SUB-003', 'SUB-004'):
            for node in self.doms[sid].select(css='readings'):
                self.assertEqual(len(node.select(css='reading')), 3)
            self.assertIn('Tool chooses none.', self.doms[sid].text())

    def test_chosen_identity_reading_is_rejected_not_endorsed(self):
        check = {'readings': research.READINGS, 'chosen_reading': 'same person'}
        with self.assertRaisesRegex(ValueError, 'unchosen'):
            page.readings(check)

    def test_excluded_person_card_compares_all_conflicting_fields_side_by_side(self):
        cards = self.doms['SUB-002'].select('article', 'excluded')
        self.assertEqual(len(cards), 2)
        subject = self.reports['SUB-002']['subject']
        for card, record in zip(cards, self.reports['SUB-002']['excluded_articles']):
            columns = [c for c in card.select(css='comparison')[0].children if isinstance(c, Node)]
            self.assertEqual(len(columns), 2)
            self.assertIn('Subject', columns[0].text())
            self.assertIn('Article', columns[1].text())
            article = record['identity_check']['stated_fields']
            for field in ('role', 'employer', 'age'):
                expected = '39' if field == 'age' else subject[field]
                self.assertIn(field + ': ' + expected, columns[0].text())
                self.assertIn(field + ': ' + article[field], columns[1].text())
            self.assertIn(record['article_id'], card.text())

    def test_nothing_found_is_never_a_clearance(self):
        html = self.pages['SUB-005']
        self.assertIn('This is not a clearance.', html)
        self.assertNotRegex(html.replace('This is not a clearance.', ''), r'(?i)clear(?:ed|ance)?')

    def test_coverage_gaps_include_source_status_and_real_date_limits(self):
        for root in self.doms.values():
            section = next(s for s in root.select('section')
                           if s.select('h2') and s.select('h2')[0].text() == 'What was not covered')
            self.assertEqual(len(section.select('article')), 3)
            for value in ('SRC-003', 'SRC-004', 'SRC-005', 'failed', 'not attempted', 'stale',
                          'Coverage stops at 2025-09-01', 'No date coverage established.',
                          'planned date only, nothing read'):
                self.assertIn(value, section.text())

    def test_footer_has_skill_version_commit_and_report_path(self):
        for sid in self.reports:
            footer = self.doms[sid].select('footer')[0].text()
            for value in ('Skill version: 0.5', 'Commit id: ' + 'a' * 40,
                          'Generated from reports/' + sid + '.json'):
                self.assertIn(value, footer)

    def test_no_forbidden_identifiers_or_real_names_from_brief(self):
        output = '\n'.join(self.pages.values())
        self.assertNotRegex(output, r'(?i)registration[_ ]number|SYN-[A-Z]+-\d+|birth[_ ]date|date[_ ]of[_ ]birth|\bdob\b|\bborn\b|nationality|national of')
        for subject in research.read_json(FIXTURES / 'subjects.json')['subjects']:
            for field in ('registration_number', 'date_of_birth'):
                if field in subject:
                    self.assertNotIn(subject[field], output)
        encoded = ('4d4153', '4d6f6e657461727920417574686f72697479', '4f464143', '4f465349', '554e',
                   '53696e6761706f7265', '4d616c6179736961', '496e646f6e65736961', '4a6f686f72',
                   '53696e6761706f726520437573746f6d73', '53696e6761706f726520506f6c696365',
                   '436f6d6d65726369616c2041666661697273', '41435241', '53747261746567696320476f6f6473',
                   '52657574657273', '537472616974732054696d6573', '427573696e6573732054696d6573',
                   '426c6f6f6d62657267', '4a75726f6e67', '576f6f646c616e6473', '54756173', '50617369722050616e6a616e67')
        for token in encoded:
            self.assertNotRegex(output, r'(?i)(?<!\w)' + re.escape(bytes.fromhex(token).decode('ascii')) + r'(?!\w)')

    def test_no_external_resource_loads_or_scripts(self):
        pages = list(self.pages.values()) + [page.render_index([(Path(sid + '.json'), r) for sid, r in self.reports.items()])]
        for html in pages:
            self.assertNotRegex(html, r'https?://|@import|url\s*\(')
            root = DOM(html).root
            for tag in ('script', 'img', 'iframe', 'link', 'object', 'embed', 'form'):
                self.assertEqual(root.select(tag), [])
            policies = [n.attrs['content'] for n in root.select('meta') if n.attrs.get('http-equiv') == 'Content-Security-Policy']
            self.assertEqual(len(policies), 1)
            self.assertIn("default-src 'none'", policies[0])

    def test_untrusted_report_text_is_escaped_not_executed(self):
        report = copy.deepcopy(self.reports['SUB-002'])
        hostile = '<script src="https://invalid.test/x"></script>&'
        report['subject']['name'] = hostile
        report['summary'] = hostile
        report['findings'][0]['quote'] = hostile
        html = page.render_page(report, hostile, hostile)
        root = DOM(html).root
        self.assertEqual(root.select('script'), [])
        self.assertEqual(root.select(css='headline')[0].text(), hostile)
        self.assertIn(hostile, root.select('blockquote')[0].text())
        self.assertNotIn('<script', html)

    def test_two_cli_runs_produce_byte_identical_pages_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_reports(folder)
            snapshots = []
            for _ in range(2):
                proc = self.cli('--all', folder)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                snapshots.append({p.name: p.read_bytes() for p in folder.glob('*.html')})
            self.assertEqual(len(snapshots[0]), 6)
            self.assertEqual(snapshots[0], snapshots[1])

    def test_renderer_does_not_modify_report_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_reports(folder)
            before = {p.name: p.read_bytes() for p in folder.glob('*.json')}
            proc = self.cli('--all', folder)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.glob('*.json')})

    def test_invalid_report_fails_before_writing_any_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_reports(folder)
            (folder / 'ZZZ-invalid.json').write_text('{}')
            proc = self.cli('--all', folder)
            self.assertEqual(proc.returncode, 1)
            self.assertIn('Page render failed', proc.stderr)
            self.assertEqual(list(folder.glob('*.html')), [])

    def test_missing_or_empty_input_is_an_explicit_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.cli('--all', tmp)
            self.assertEqual(proc.returncode, 1)
            self.assertIn('No report JSON files', proc.stderr)
            proc = self.cli('--report', Path(tmp) / 'missing.json', '--out', Path(tmp) / 'out.html')
            self.assertEqual(proc.returncode, 1)
            self.assertFalse((Path(tmp) / 'out.html').exists())

    def test_out_argument_cannot_replace_input_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'SUB-001.json'
            path.write_text(json.dumps(self.reports['SUB-001']))
            before = path.read_bytes()
            proc = self.cli('--report', path, '--out', path)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(path.read_bytes(), before)

    def test_subject_names_have_correct_tags_everywhere_in_body_and_index(self):
        subjects = research.read_json(FIXTURES / 'subjects.json')['subjects']
        roots = list(self.doms.values()) + [DOM(page.render_index(
            [(Path(sid + '.json'), r) for sid, r in self.reports.items()])).root]
        for root in roots:
            body = root.select('body')[0]
            for subject in subjects:
                spans = [n for n in body.select(css='typed-name') if n.text() == subject['name']]
                for span in spans:
                    self.assertEqual(span.attrs['data-kind'], subject['type'])
                    self.assertEqual(span.attrs['data-tag'], page.TAGS[subject['type']])
                    self.assertIn(page.TAGS[subject['type']], span.attrs['aria-label'])
                # Every occurrence in a body text node must sit in its tag span.
                def check_node(node):
                    for child in node.children:
                        if isinstance(child, Node):
                            check_node(child)
                        elif subject['name'] in child:
                            self.assertIn('typed-name', node.attrs.get('class', '').split())
                check_node(body)
        for sid, report in self.reports.items():
            self.assertEqual(self.doms[sid].select('h1')[0].select(css='typed-name')[0].attrs['data-kind'],
                             report['subject']['type'])

    def test_known_names_use_structured_types_and_unknown_names_stay_untagged(self):
        names = page.name_types(self.reports['SUB-002'])
        for name, kind in (('Tan Wei Quen', 'person'), ('JKL Trading Pte. Ltd.', 'company'),
                           ('PQR Port Services Pte. Ltd.', 'company'),
                           ('Sanctions Office of Country Y', 'authority'), ('Customs Agency A', 'authority')):
            self.assertEqual(names[name][0], kind)
        outlets = research.read_json(FIXTURES / 'sources.json')['sources']
        for outlet in outlets:
            self.assertEqual(names[outlet['name']][0], 'outlet')
        unknown = 'Unclassified Invented Name'
        self.assertEqual(page.named(unknown, names), unknown)
        report = copy.deepcopy(self.reports['SUB-002'])
        report['subject']['type'] = 'unknown'
        self.assertNotIn('typed-name', page.named(report['subject']['name'], page.name_types(report)))

    def test_company_profiles_replace_place_fields(self):
        for sid in ('SUB-001', 'SUB-003', 'SUB-005'):
            self.assertTrue(self.reports[sid]['subject']['profile'])
            self.assertNotIn('district', self.reports[sid]['subject'])
            self.assertNotIn('city', self.reports[sid]['subject'])

    def test_company_profile_conflict_compares_subject_profile(self):
        report = copy.deepcopy(self.reports['SUB-003'])
        record = report['findings'].pop()
        record['identity_check']['conflicting_fields'] = ['profile']
        record['identity_check']['stated_fields'] = {'profile': 'supplier of wooden models'}
        record['reason'] = 'The profile differs.'
        report['excluded_articles'] = [record]
        root = DOM(page.render_page(report, 'company.json')).root
        columns = root.select(css='comparison')[0].select('div')[1:]
        self.assertIn('profile: provider of vessel bunkering services', columns[0].text())
        self.assertIn('profile: supplier of wooden models', columns[1].text())

    def test_page_and_index_notices_use_placeholders_only(self):
        roots = list(self.doms.values()) + [DOM(page.render_index(
            [(Path(sid + '.json'), r) for sid, r in self.reports.items()])).root]
        for root in roots:
            self.assertIn('The sample is local in style only; no real place names are used.', root.text())
            self.assertNotIn('All names are invented', root.text())

    def test_whos_who_lists_every_known_name_exactly_once_with_a_plain_description(self):
        for sid, report in self.reports.items():
            who = self.doms[sid].select(css='who')[0]
            rows = who.select('li')
            names = page.name_types(report)
            self.assertEqual(len(rows), len(names))
            seen = []
            for row in rows:
                spans = row.select(css='typed-name')
                self.assertEqual(len(spans), 1)
                seen.append(spans[0].text())
                self.assertIn(names[spans[0].text()][1], row.text())
            self.assertEqual(set(seen), set(names))
            self.assertIn('Company, person, authority and outlet names are placeholders.', who.text())
            self.assertIn('The sample is local in style only; no real place names are used.', who.text())

    def test_no_technical_labels_or_iso_dates_outside_details(self):
        roots = list(self.doms.values()) + [DOM(page.render_index(
            [(Path(sid + '.json'), r) for sid, r in self.reports.items()])).root]
        for root in roots:
            visible = root.outside_details()
            self.assertNotRegex(visible, r'(?i)SRC-|ART-|as_of|execution')
            self.assertNotRegex(visible, r'\b\d{4}-\d{2}-\d{2}\b')

    def test_empty_sections_are_absent_not_placeholders(self):
        for sid, root in self.doms.items():
            self.assertEqual(root.select(css='empty'), [])
            self.assertNotRegex(root.text(), r'No (?:possible matches|other findings|linked closure|dated findings|conflicting identities|other mentions|source gaps)')
            for section in root.select('section'):
                if section.select(css='cards'):
                    self.assertTrue(section.select('article'))
        headings = [n.text() for n in self.doms['SUB-005'].select('h2')]
        for absent in ('What happened', 'Earlier case, now closed', 'Older report, status unknown',
                       'Possible matches (not enough evidence)', 'Same name, different company'):
            self.assertNotIn(absent, headings)

    def test_company_excluded_heading_does_not_say_person(self):
        report = copy.deepcopy(self.reports['SUB-001'])
        record = report['findings'].pop()
        record['identity_check']['conflicting_fields'] = ['profile']
        record['identity_check']['stated_fields'] = {'profile': 'supplier of wooden models'}
        record['reason'] = 'The profile differs.'
        report['excluded_articles'] = [record]
        root = DOM(page.render_page(report, 'company.json')).root
        headings = [h.text() for h in root.select('h2')]
        self.assertIn('Same name, different company', headings)
        self.assertNotIn('Same name, different person', headings)
        self.assertIn('Same name, different person', [h.text() for h in self.doms['SUB-002'].select('h2')])

    def test_answer_is_first_with_three_counted_tiles_and_original_summary_below(self):
        expected = {'SUB-001': (6, 0, 3), 'SUB-002': (4, 2, 3), 'SUB-003': (0, 1, 3),
                    'SUB-004': (3, 0, 3), 'SUB-005': (0, 0, 3)}
        for sid, root in self.doms.items():
            first = root.select('section')[0]
            self.assertIn('answer', first.attrs['class'])
            self.assertEqual(first.select('h2')[0].text(), 'The answer')
            tiles = first.select(css='overview')[0]
            self.assertEqual([int(n.text()) for n in tiles.select('strong')], list(expected[sid]))
            for label in ('Confirmed hits', 'Ruled out or closed', 'Not checked'):
                self.assertIn(label, tiles.text())
            self.assertIn(self.reports[sid]['summary'], first.text())
            self.assertEqual(first.select(css='answer-line')[0].text(), page.answer_sentence(self.reports[sid]))
        self.assertIn('This is not a clearance.', self.doms['SUB-005'].outside_details())
        self.assertIn('1 earlier case is closed', self.doms['SUB-003'].outside_details())

    def test_card_verdict_and_plain_event_come_before_closed_evidence(self):
        for root in self.doms.values():
            for card in root.select('article'):
                if not set(card.attrs.get('class', '').split()) & {'finding', 'linked', 'dated', 'excluded'}:
                    continue
                children = [c for c in card.children if isinstance(c, Node)]
                self.assertEqual([c.tag for c in children[:3]], ['h3', 'p', 'details'])
                self.assertEqual(children[2].select('summary')[0].text(), 'Show the evidence')
                self.assertTrue(children[2].select('blockquote'))
                self.assertNotIn('open', children[2].attrs)
        self.assertIn('Same person: name, role, employer and age all match.', self.doms['SUB-002'].outside_details())

    def test_all_quotes_including_exclusions_and_non_events_are_verbatim_in_details(self):
        for sid, report in self.reports.items():
            quotes = [n.text() for d in self.doms[sid].select('details') for n in d.select('blockquote')]
            for record in page.records(report):
                self.assertIn(record['quote'], quotes)

    def test_sources_have_plain_summary_dots_and_collapsed_full_statuses(self):
        for root in self.doms.values():
            self.assertIn('Checked 3 of 5 news sources. 1 failed. 1 was not run. 1 is old (last updated 1 Sep 2025).',
                          root.outside_details())
            self.assertEqual(len(root.select(css='dot')), 5)
            source_details = next(d for d in root.select('details') if d.select('summary')[0].text() == 'Source details')
            self.assertNotIn('open', source_details.attrs)
            self.assertEqual(len(source_details.select(css='source')), 5)
            self.assertEqual(len(source_details.select(css='label')), 15)

    def test_other_mentions_are_collapsed_and_counted(self):
        for sid, report in self.reports.items():
            matches = [d for d in self.doms[sid].select('details')
                       if d.select('summary')[0].text().startswith('Other mentions (not sanctions events)')]
            self.assertEqual(len(matches), bool(report['non_events']))
            if matches:
                self.assertNotIn('open', matches[0].attrs)
                self.assertEqual(matches[0].select('summary')[0].text(),
                                 'Other mentions (not sanctions events) · ' + str(len(report['non_events'])))

    def test_index_has_one_typed_row_and_one_sentence_answer_per_subject(self):
        root = DOM(page.render_index([(Path(sid + '.json'), r) for sid, r in self.reports.items()])).root
        rows = root.select('article')
        self.assertEqual(len(rows), 5)
        for row, report in zip(rows, self.reports.values()):
            self.assertIn(report['subject']['name'], row.select('a')[0].text())
            self.assertEqual(row.select(css='typed-name')[0].attrs['data-kind'], report['subject']['type'])
            self.assertIn(page.answer_sentence(report), row.outside_details())

    def test_dates_and_readable_spacing_are_fixed_without_external_fonts(self):
        self.assertEqual(page.display_date('2026-10-23'), '23 Oct 2026')
        self.assertIn('font-size: 17px; line-height: 1.6', page.STYLE)
        self.assertIn('max-width: 804px', page.STYLE)  # 760px content plus two 22px gutters.
        self.assertIn('.overview, .sources, .cards, .readings, .comparison { display: grid; gap: 24px; }', page.STYLE)

    def test_partial_identity_remains_visible_and_publication_is_not_event_date(self):
        for sid in ('SUB-001', 'SUB-003', 'SUB-004'):
            self.assertIn('identity still needs human review', self.doms[sid].select(css='answer-line')[0].text())
        self.assertIn('An inquiry was reported on 12 Aug 2025; case closed on 24 Oct 2026.',
                      self.doms['SUB-003'].outside_details())
        self.assertNotIn('Investigated on', self.doms['SUB-003'].outside_details())

    def test_standalone_outcome_does_not_close_an_unlinked_earlier_case(self):
        report = copy.deepcopy(self.reports['SUB-003'])
        resolution = report['findings'][0]['resolution']
        resolution.update(state='reported closure', assessment='A case closure was reported.')
        report['findings'] = [resolution]
        self.assertEqual(page.answer_counts(report), (1, 0, 3))
        visible = DOM(page.render_page(report, 'closure.json')).root.outside_details()
        self.assertNotIn('1 earlier case is closed', visible)
        self.assertIn('case closure was reported on 24 Oct 2026.', visible)

    def test_completed_source_with_unavailable_result_is_visibly_incomplete(self):
        report = copy.deepcopy(self.reports['SUB-005'])
        report['sources'][0]['result'] = 'unavailable'
        root = DOM(page.render_page(report, 'incomplete.json')).root
        dots = root.select(css='source-dots')[0].select('li')
        self.assertIn('incomplete', dots[0].text())
        self.assertIn('bad', dots[0].select(css='dot')[0].attrs['class'])
        self.assertIn('Checked 2 of 5 news sources.', root.outside_details())
        self.assertIn('1 ran but could not be fully read.', root.outside_details())


if __name__ == '__main__':
    unittest.main()
