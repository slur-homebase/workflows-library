#!/usr/bin/env python3
"""Run the four existing offline scripts on invented local inputs."""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / 'scripts'
SAMPLE = SKILL / 'sample'
# The research baseline, not the packaging commit. Pin provenance so moving the
# output or committing the frozen demo cannot change its rendered bytes.
RESEARCH_COMMIT = 'bba5cde0e17e29c48f995be6b47f6f078b95a641'


def step(label, script, arguments, cwd):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, arguments)],
                          cwd=cwd, capture_output=True, text=True)
    if proc.returncode:
        print(label + ': FAIL', flush=True)
        detail = (proc.stderr or proc.stdout).strip()
        if detail:
            print(detail, file=sys.stderr)
        raise ValueError(script + ' exited ' + str(proc.returncode))
    summary = proc.stdout.strip().splitlines()
    print(label + ': PASS' + (' | ' + summary[-1] if summary else ''), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subjects', type=Path, help='invented subjects JSON; sources.json must be beside it')
    parser.add_argument('--articles', type=Path, help='invented article Markdown folder')
    parser.add_argument('--out', type=Path, help='new or empty output folder')
    parser.add_argument('--demo', action='store_true', help='regenerate the bundled sample into demo/')
    args = parser.parse_args(argv)
    if args.demo:
        if args.subjects or args.articles or args.out:
            parser.error('--demo uses the bundled sample and demo/; do not combine input/output flags')
        args.subjects, args.articles, args.out = SAMPLE / 'subjects.json', SAMPLE / 'articles', SKILL / 'demo'
    elif not all((args.subjects, args.articles, args.out)):
        parser.error('--subjects, --articles and --out are required without --demo')
    try:
        subjects, articles, out = args.subjects.resolve(), args.articles.resolve(), args.out.resolve()
        # Stage the inputs for the existing --fixtures interface without changing
        # any input bytes or teaching this wrapper the research rules.
        if not subjects.is_file() or not articles.is_dir():
            raise ValueError('Subjects file and articles folder must exist')
        for protected in (subjects.parent, articles, SKILL / 'evidence', SCRIPTS):
            if out == protected or protected in out.parents or out in protected.parents:
                raise ValueError('Output must not overlap inputs, scripts or frozen evidence')
        if not args.demo and out.exists() and any(out.iterdir()):
            raise ValueError('Output folder must be new or empty; use --demo to refresh the frozen demo')
        if not args.demo and (out == SKILL / 'demo' or SKILL / 'demo' in out.parents):
            raise ValueError('Use --demo to refresh the frozen demo')
        data = json.loads(subjects.read_text(encoding='utf-8'))
        ids = [subject['id'] for subject in data['subjects']]
        if (not ids or any(not isinstance(sid, str) or not re.fullmatch(r'SUB-[0-9]{3}', sid) for sid in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError('Require distinct SUB-NNN subject ids')
        key = subjects.with_name('answer-key.json')
        with tempfile.TemporaryDirectory(prefix='sanctions-news-run-') as temporary:
            work = Path(temporary)
            fixtures, reports = work / 'inputs', work / 'reports'
            fixtures.mkdir()
            shutil.copyfile(subjects, fixtures / 'subjects.json')
            shutil.copyfile(subjects.with_name('sources.json'), fixtures / 'sources.json')
            shutil.copytree(articles, fixtures / 'articles')
            if key.exists():
                shutil.copyfile(key, fixtures / 'answer-key.json')
            for sid in ids:
                step('Research ' + sid, 'research.py',
                     ['--subject', sid, '--fixtures', fixtures, '--out', reports], work)
            if key.exists():
                # The checker intentionally replays research independently. Its
                # reports stay separate from the pipeline's original reports.
                step('Answer key', 'check_answer_key.py',
                     ['--fixtures', fixtures, '--out', work / 'checked'], work)
            else:
                print('Answer key: SKIP | no answer-key.json beside subjects', flush=True)
            step('Findings pages', 'render_page.py',
                 ['--all', 'reports', '--commit-id', RESEARCH_COMMIT], work)
            step('Dashboard', 'render_dashboard.py',
                 ['--reports', 'reports', '--out', 'reports/dashboard.html'], work)
            generated = sorted(reports.iterdir())
            if args.demo and out.exists() and {p.name for p in out.iterdir()} != {p.name for p in generated}:
                raise ValueError('Demo has unexpected files; refusing to remove them')
            out.mkdir(parents=True, exist_ok=True)
            for path in generated:
                shutil.copyfile(path, out / path.name)
        print('Output: ' + str(out), flush=True)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Run failed: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
