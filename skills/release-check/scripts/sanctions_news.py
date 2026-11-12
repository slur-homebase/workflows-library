"""Offline packaging checks only, not a human release or supervised-run gate."""

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


BANNED = ('Singapore', 'Jurong', 'Woodlands', 'Tuas', 'Pasir Panjang',
          'registration', 'date_of_birth', 'nationality', 'admitted', 'convicted')
MAX_DEMO_BYTES = 2_000_000


class LocalResources(HTMLParser):
    """Reject non-local links/resources and network-capable HTML declarations."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.errors = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'base' or (tag == 'meta' and (attrs.get('http-equiv') or '').lower() == 'refresh'):
            self.errors.append('redirect or base declaration')
        for name in ('href', 'src', 'action', 'data', 'poster', 'srcset'):
            if name not in attrs:
                continue
            value = unquote(attrs[name] or '').strip()
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith(('//', '\\')) or name == 'srcset':
                self.errors.append('non-local ' + name + ': ' + value)
            elif parsed.path:
                self.links.append(parsed.path)


def demo_errors(demo):
    """Scan every retained file, not just a trusted list of rendered pages."""
    errors = []
    files = sorted(p for p in demo.rglob('*') if p.is_file() and not p.is_symlink())
    if not files:
        return ['demo is missing or empty']
    if sum(p.stat().st_size for p in files) >= MAX_DEMO_BYTES:
        errors.append('demo must be under 2 MB')
    for path in sorted(demo.rglob('*')):
        if path.is_symlink():
            errors.append('demo contains symlink: ' + path.name)
    for path in files:
        name = path.relative_to(demo).as_posix()
        if path.suffix not in ('.html', '.json', '.md'):
            errors.append('unexpected demo file: ' + name)
            continue
        try:
            text = unescape(path.read_text(encoding='utf-8')).replace('\\/', '/')
            text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), text)
            for term in BANNED:
                if term.casefold() in text.casefold():
                    errors.append(name + ': banned term ' + term)
            if re.search(r'(?i)\b[a-z][a-z0-9+.-]*://|@import\b|url\s*\(', text):
                errors.append(name + ': external URL or CSS load')
            if path.suffix == '.html':
                parser = LocalResources()
                parser.feed(path.read_text(encoding='utf-8'))
                errors.extend(name + ': ' + error for error in parser.errors)
                for link in parser.links:
                    target = (path.parent / link).resolve()
                    if demo.resolve() not in target.parents or not target.is_file():
                        errors.append(name + ': missing or escaping local link ' + link)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(name + ': ' + str(exc))
    return errors


def check_package(subject):
    """Regenerate via run.py without ever overwriting the saved demo."""
    demo, sample = subject / 'demo', subject / 'sample'
    errors = demo_errors(demo)
    results = [('Demo safety and size', not errors, '; '.join(errors))]
    try:
        ids = [s['id'] for s in json.loads((sample / 'subjects.json').read_text(encoding='utf-8'))['subjects']]
        if (not ids or len(set(ids)) != len(ids)
                or any(not re.fullmatch(r'SUB-[0-9]{3}', sid) for sid in ids)):
            raise ValueError('invalid sample subject ids')
        expected = {'index.html', 'dashboard.html'} | {sid + ext for sid in ids for ext in ('.json', '.md', '.html')}
        saved = {p.relative_to(demo).as_posix(): p.read_bytes() for p in demo.rglob('*')
                 if p.is_file() and not p.is_symlink()}
        results.append(('Demo file set', set(saved) == expected, 'expected ' + str(len(expected)) + ' files'))
        with tempfile.TemporaryDirectory(prefix='sanctions-news-release-') as temporary:
            out = Path(temporary) / 'output'
            proc = subprocess.run([sys.executable, str(subject / 'scripts/run.py'),
                                   '--subjects', str(sample / 'subjects.json'),
                                   '--articles', str(sample / 'articles'), '--out', str(out)],
                                  capture_output=True, text=True, timeout=60)
            results.append(('Sample entry command', proc.returncode == 0,
                            (proc.stdout + proc.stderr).strip() if proc.returncode else 'offline run completed'))
            fresh = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
            differences = sorted(name for name in set(saved) | set(fresh) if saved.get(name) != fresh.get(name))
            identical = bool(saved) and proc.returncode == 0 and set(fresh) == expected and not differences
            results.append(('Byte-identical demo replay', identical,
                            ', '.join(differences) if differences else str(len(fresh)) + ' files compared'))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        results.append(('Sample replay', False, str(exc)))
    for label, passed, detail in results:
        print(label + ': ' + ('PASS' if passed else 'FAIL') + (' | ' + detail if detail else ''))
    passed = all(result[1] for result in results)
    print('Verdict: ' + ('PASS' if passed else 'BLOCKED') + ' (offline package only; human sign-off not given)')
    return 0 if passed else 1
