"""Phase-5 entry command, portable sample and unchanged findings."""

import contextlib
from html.parser import HTMLParser
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT
SAMPLE = SKILL / 'sample'
SPEC = importlib.util.spec_from_file_location('sanctions_news_run', SKILL / 'scripts/run.py')
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def contents(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


class EntryCommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sanctions-news-entry-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.out = Path(cls.temp.name) / 'output'
        cls.proc = cls.cli('--subjects', SAMPLE / 'subjects.json', '--articles', SAMPLE / 'articles', '--out', cls.out)
        if cls.proc.returncode:
            raise AssertionError(cls.proc.stdout + cls.proc.stderr)
        cls.generated = contents(cls.out)

    @staticmethod
    def cli(*args, script=None, cwd=None):
        return subprocess.run([sys.executable, str(script or SKILL / 'scripts/run.py'), *map(str, args)],
                              cwd=cwd, capture_output=True, text=True, timeout=30)

    def inputs(self, folder, key=True):
        sample = folder / 'inputs'
        sample.mkdir()
        for name in ('subjects.json', 'sources.json') + (('answer-key.json',) if key else ()):
            shutil.copyfile(SAMPLE / name, sample / name)
        shutil.copytree(SAMPLE / 'articles', sample / 'articles')
        return sample

    def test_sample_is_the_same_input_bytes_as_repository_fixtures(self):
        original = ROOT / 'fixtures'
        for name, data in contents(SAMPLE).items():
            self.assertEqual(data, (original / name).read_bytes(), name)
        self.assertEqual(len(list((SAMPLE / 'articles').glob('*.md'))), 29)

    def test_one_line_per_step_and_complete_file_set(self):
        lines = self.proc.stdout.splitlines()
        self.assertEqual(len(lines), 9)
        self.assertEqual(sum(line.startswith('Research ') for line in lines), 5)
        for label in ('Answer key: PASS | 38/38 rows passed', 'Findings pages: PASS', 'Dashboard: PASS'):
            self.assertIn(label, self.proc.stdout)
        expected = {'index.html', 'dashboard.html'} | {
            f'SUB-{n:03d}{ext}' for n in range(1, 6) for ext in ('.json', '.md', '.html')}
        self.assertEqual(set(self.generated), expected)

    def test_all_output_bytes_equal_demo(self):
        self.assertEqual(self.generated, contents(SKILL / 'demo'))

    def test_all_html_link_targets_exist_and_resource_loads_stay_inline(self):
        class Targets(HTMLParser):
            def handle_starttag(self, tag, attrs):
                targets.extend(value for key, value in attrs if key in {'href', 'src'})

        for name, data in self.generated.items():
            if not name.endswith('.html'):
                continue
            with self.subTest(page=name):
                targets = []
                Targets().feed(data.decode())
                for target in targets:
                    url = urlsplit(target)
                    self.assertFalse(url.scheme or url.netloc, target)
                    self.assertIn(url.path or name, self.generated, target)

    def test_json_and_markdown_equal_stage_settlement_baseline(self):
        baseline = SKILL / 'evidence/phase-4/stage-settlement/reports'
        expected = contents(baseline)
        self.assertEqual(len(expected), 10)
        self.assertEqual(expected, {name: data for name, data in self.generated.items()
                                    if name.endswith(('.json', '.md'))})

    def test_portable_page_provenance_has_no_machine_or_output_path(self):
        for name, data in self.generated.items():
            if name.startswith('SUB-') and name.endswith('.html'):
                text = data.decode()
                self.assertIn(runner.RESEARCH_COMMIT, text)
                self.assertIn('reports/' + name.replace('.html', '.json'), text)
                self.assertNotIn(str(self.out), text)
                self.assertNotIn('/Users/', text)

    def test_skill_folder_runs_alone_and_demo_regenerates_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'sanctions-news'
            # No historical evidence or repository fixtures are needed to run.
            for name in ('scripts', 'sample', 'demo'):
                shutil.copytree(SKILL / name, folder / name, ignore=shutil.ignore_patterns('__pycache__'))
            proc = self.cli('--demo', script=folder / 'scripts/run.py', cwd=folder)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(self.generated, contents(folder / 'demo'))
            proc = self.cli('--subjects', 'sample/subjects.json', '--articles', 'sample/articles',
                            '--out', 'output', script=folder / 'scripts/run.py', cwd=folder)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(self.generated, contents(folder / 'output'))

    def test_optional_key_is_explicitly_skipped_and_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sample = self.inputs(folder, key=False)
            before = contents(sample)
            proc = self.cli('--subjects', sample / 'subjects.json', '--articles', sample / 'articles',
                            '--out', folder / 'output')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('Answer key: SKIP | no answer-key.json', proc.stdout)
            self.assertEqual(before, contents(sample))
            self.assertEqual(self.generated, contents(folder / 'output'))

    def test_articles_can_be_supplied_from_a_separate_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sample = self.inputs(folder, key=False)
            separate = folder / 'separate-articles'
            shutil.move(str(sample / 'articles'), separate)
            proc = self.cli('--subjects', sample / 'subjects.json', '--articles', separate,
                            '--out', folder / 'output')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(self.generated, contents(folder / 'output'))

    def test_bad_key_stops_before_rendering_or_writing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sample = self.inputs(folder)
            key_path = sample / 'answer-key.json'
            key = json.loads(key_path.read_text())
            key['subjects'][0]['expected_findings'][0]['quote'] = 'Invented incorrect answer.'
            key_path.write_text(json.dumps(key))
            proc = self.cli('--subjects', sample / 'subjects.json', '--articles', sample / 'articles',
                            '--out', folder / 'output')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Answer key: FAIL', proc.stdout)
            self.assertNotIn('Findings pages:', proc.stdout)
            self.assertFalse((folder / 'output').exists())

    def test_bad_article_is_failure_not_no_findings(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sample = self.inputs(folder)
            (sample / 'articles/ART-001.md').write_text('Invalid invented input')
            proc = self.cli('--subjects', sample / 'subjects.json', '--articles', sample / 'articles',
                            '--out', folder / 'output')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('Research SUB-001: FAIL', proc.stdout)
            self.assertFalse((folder / 'output').exists())

    def test_missing_sources_fails_without_writing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            inputs = folder / 'inputs'
            inputs.mkdir()
            shutil.copyfile(SAMPLE / 'subjects.json', inputs / 'subjects.json')
            proc = self.cli('--subjects', inputs / 'subjects.json', '--articles', SAMPLE / 'articles',
                            '--out', folder / 'output')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('sources.json', proc.stderr)
            self.assertFalse((folder / 'output').exists())

    def test_reject_empty_duplicate_and_unsafe_subject_ids(self):
        for ids in ([], ['SUB-001', 'SUB-001'], ['../escape'], ['SUB-００１']):
            with self.subTest(ids=ids), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                inputs = folder / 'inputs'
                inputs.mkdir()
                (inputs / 'subjects.json').write_text(json.dumps({'subjects': [{'id': sid} for sid in ids]}))
                proc = self.cli('--subjects', inputs / 'subjects.json', '--articles', SAMPLE / 'articles',
                            '--out', folder / 'output')
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('distinct SUB-NNN', proc.stderr)
                self.assertFalse((folder / 'output').exists())

    def test_reject_protected_or_nonempty_output_without_changes(self):
        for output in (SAMPLE, SAMPLE / 'articles', SKILL / 'evidence', SKILL / 'scripts', SKILL / 'demo'):
            with self.subTest(output=output):
                before = contents(output)
                proc = self.cli('--subjects', SAMPLE / 'subjects.json', '--articles', SAMPLE / 'articles', '--out', output)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(before, contents(output))
        before = contents(self.out)
        proc = self.cli('--subjects', SAMPLE / 'subjects.json', '--articles', SAMPLE / 'articles', '--out', self.out)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(before, contents(self.out))

    def test_reject_ambiguous_or_incomplete_flags(self):
        for args in ([], ['--subjects', 'missing'], ['--demo', '--out', 'not-allowed'], ['--reader', 'model']):
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args).returncode, 2)

    def test_every_child_failure_propagates(self):
        for script in ('research.py', 'check_answer_key.py', 'render_page.py', 'render_dashboard.py'):
            with self.subTest(script=script):
                completed = subprocess.CompletedProcess([], 9, '', 'Synthetic child failure')
                with patch.object(runner.subprocess, 'run', return_value=completed), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, script + ' exited 9'):
                        runner.step('Test', script, [], ROOT)

    def test_skill_document_is_short_and_demo_is_small(self):
        self.assertLess(len((SKILL / 'SKILL.md').read_text().splitlines()), 150)
        self.assertLess(sum(len(data) for data in self.generated.values()), 2_000_000)


if __name__ == '__main__':
    unittest.main()
