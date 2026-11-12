"""Sanctions-news packaging adapter: real replay plus fail-closed scan cases."""

import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills/release-check/scripts/release_check.py'
SPEC = importlib.util.spec_from_file_location('news_package', SCRIPT.with_name('sanctions_news.py'))
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
SKILL = ROOT / 'skills/sanctions-news'


class DemoSafetyTest(unittest.TestCase):
    def scan(self, text, filename='index.html'):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / filename).write_text(text, encoding='utf-8')
            return checker.demo_errors(folder)

    def test_real_demo_is_safe(self):
        self.assertEqual(checker.demo_errors(SKILL / 'demo'), [])

    def test_all_banned_terms_are_case_insensitive_in_every_file_type(self):
        for term in checker.BANNED:
            for extension in ('html', 'json', 'md'):
                with self.subTest(term=term, extension=extension):
                    self.assertTrue(self.scan(term.upper(), 'sample.' + extension))

    def test_external_urls_css_and_protocol_relative_loads_fail(self):
        for text in ('https://example.invalid', 'http://example.invalid', 'wss://example.invalid',
                     '<script src="//example.invalid/x"></script>', '<a href="//example.invalid">x</a>',
                     '<img src="&#104;ttps://example.invalid/x">', '<img src="https%3A%2F%2Fexample.invalid/x">',
                     '<link href="https://example.invalid/x">', '<style>@import "x.css";</style>',
                     '<style>div{background:url(x.png)}</style>', '<base href="elsewhere/">',
                     '<meta http-equiv="refresh" content="0;url=elsewhere.html">',
                     r'{"url":"https:\/\/example.invalid"}'):
            with self.subTest(text=text):
                self.assertTrue(self.scan(text))

    def test_encoded_banned_terms_fail(self):
        self.assertTrue(self.scan('Singa&#112;ore'))
        self.assertTrue(self.scan(r'\u0053ingapore', 'sample.json'))

    def test_local_existing_links_pass_missing_and_escape_fail(self):
        self.assertEqual(self.scan('<a href="index.html">local</a><a href="#here">here</a>'), [])
        for link in ('missing.html', '../outside.html', '/absolute.html'):
            self.assertTrue(self.scan('<a href="' + link + '">bad</a>'))

    def test_empty_unknown_binary_and_size_limit_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertTrue(checker.demo_errors(Path(temporary)))
        self.assertTrue(self.scan('invented text', 'unknown.txt'))
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'index.html').write_bytes(b'\xff')
            self.assertTrue(checker.demo_errors(folder))
        with patch.object(checker, 'MAX_DEMO_BYTES', 10):
            self.assertIn('demo must be under 2 MB', self.scan('1234567890'))

    def test_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'index.html').write_text('invented')
            (folder / 'linked.html').symlink_to(folder / 'index.html')
            self.assertTrue(any('symlink' in error for error in checker.demo_errors(folder)))


class PackageReplayTest(unittest.TestCase):
    def cli(self, *extra):
        return subprocess.run([sys.executable, str(SCRIPT), str(SKILL), *extra],
                              capture_output=True, text=True, timeout=30)

    def test_real_entry_replay_is_byte_identical_and_not_a_release(self):
        proc = self.cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('Byte-identical demo replay: PASS | 17 files compared', proc.stdout)
        self.assertIn('offline package only; human sign-off not given', proc.stdout)
        self.assertNotIn('Verdict: RELEASE', proc.stdout)

    def test_reject_model_and_record_release_flags(self):
        for flag in ('--with-model', '--record-release'):
            proc = self.cli(flag)
            self.assertEqual(proc.returncode, 2)
            self.assertIn('no model or release-recording flags', proc.stderr)

    def check_changed_copy(self, mutate):
        with tempfile.TemporaryDirectory() as temporary:
            skill = Path(temporary) / 'sanctions-news'
            for name in ('scripts', 'sample', 'demo'):
                shutil.copytree(SKILL / name, skill / name, ignore=shutil.ignore_patterns('__pycache__'))
            mutate(skill)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = checker.check_package(skill)
            return code, output.getvalue()

    def test_safe_but_changed_demo_fails_byte_check(self):
        def mutate(skill):
            path = skill / 'demo/SUB-001.md'
            path.write_text(path.read_text() + '\nInvented extra text.\n')
        code, output = self.check_changed_copy(mutate)
        self.assertEqual(code, 1)
        self.assertIn('Byte-identical demo replay: FAIL | SUB-001.md', output)

    def test_extra_and_missing_demo_files_fail(self):
        for mutate in (lambda skill: (skill / 'demo/extra.md').write_text('Invented'),
                       lambda skill: (skill / 'demo/index.html').unlink()):
            code, output = self.check_changed_copy(mutate)
            self.assertEqual(code, 1)
            self.assertIn('Demo file set: FAIL', output)

    def test_changed_sample_and_child_failure_fail_closed(self):
        def mutate(skill):
            (skill / 'sample/articles/ART-001.md').write_text('Invalid invented input')
        code, output = self.check_changed_copy(mutate)
        self.assertEqual(code, 1)
        self.assertIn('Sample entry command: FAIL', output)
        self.assertIn('Byte-identical demo replay: FAIL', output)

    def test_replay_timeout_fails_without_mutating_demo(self):
        before = {p.name: p.read_bytes() for p in (SKILL / 'demo').iterdir()}
        with patch.object(checker.subprocess, 'run', side_effect=subprocess.TimeoutExpired('run.py', 60)), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.check_package(SKILL), 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (SKILL / 'demo').iterdir()})


if __name__ == '__main__':
    unittest.main()
