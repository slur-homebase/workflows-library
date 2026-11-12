#!/usr/bin/env python3
"""Render local sanctions-news report JSON as offline, self-contained HTML."""

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys


STYLE = """
:root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #172d34; background: #edf2f3; font-size: 17px; line-height: 1.6; }
* { box-sizing: border-box; min-width: 0; }
body { margin: 0; }
main { max-width: 804px; margin: auto; padding: 28px 22px 40px; }
h1 { font-size: clamp(1.65rem, 4vw, 2.3rem); line-height: 1.15; margin: 6px 0 12px; }
h2 { font-size: 1.25rem; margin: 26px 0 12px; }
h3 { font-size: 1rem; margin: 0 0 10px; }
p { margin: 8px 0; }
a { color: #125e72; }
small, .meta { font-size: .82rem; color: #405962; }
.kicker { font-size: .76rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }
.notice { border-left: 4px solid #315c69; padding-left: 12px; }
.timeline-entry { background: white; border: 2px solid #125e72; border-radius: 10px; padding: 20px; margin: 24px 0; }
.timeline-entry a { font-size: 1.2rem; font-weight: 700; }
.answer { background: #173e49; color: white; border-radius: 12px; padding: 24px; margin-top: 24px; }
.answer h2 { margin: 0 0 12px; font-size: 1rem; }
.answer-line { font-size: 1.4rem; line-height: 1.45; font-weight: 650; }
.headline { font-size: .85rem; margin: 16px 0 0; }
.overview, .sources, .cards, .readings, .comparison { display: grid; gap: 24px; }
.overview { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 20px 0 0; color: #172d34; }
.overview div { border: 1px solid #b8ccd1; border-radius: 8px; padding: 10px 12px; background: white; }
.overview strong { display: block; font-size: 1.75rem; }
.overview div { font-size: .85rem; }
.sources { grid-template-columns: 1fr; }
.source, .card { background: white; border: 1px solid #b8ccd1; border-radius: 10px; padding: 16px; }
.source { padding: 16px; font-size: .82rem; }
.source h3 { font-size: .9rem; }
.label { border-left: 4px solid; padding: 4px 7px; margin: 6px 0; }
.good { background: #e5f4ea; border-color: #267545; color: #174a2b; }
.warn { background: #fff2d8; border-color: #a3670a; color: #704500; }
.bad { background: #fce8e7; border-color: #ae3832; color: #7c2925; }
.neutral { background: #eaf0f7; border-color: #496e96; color: #294c72; }
.card.linked { border-left: 5px solid #267545; }
.card.dated { border-left: 5px solid #a3670a; }
.card.excluded { border-left: 5px solid #496e96; }
blockquote { margin: 12px 0; padding: 12px 16px; border-left: 3px solid #6d939c; background: #f1f6f7; }
.readings { grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 12px 0; }
.reading { border: 1px solid #aabfc6; border-radius: 7px; padding: 12px; text-align: center; background: #f5f8fa; }
.comparison { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.comparison div { background: #f1f6f7; padding: 12px; border-radius: 6px; }
.arrow { text-align: center; font-size: 1.25rem; margin: 8px; }
.who { background: white; border: 1px solid #b8ccd1; border-radius: 10px; padding: 20px; margin-top: 24px; }
.who h2 { margin-top: 0; }
.who ul, .source-dots { list-style: none; padding: 0; margin: 0; }
.who li { margin: 12px 0; }
.who li span.description { color: #405962; font-size: .85rem; }
.typed-name::after { content: attr(data-tag); display: inline-block; vertical-align: middle;
  font-size: .68rem; font-weight: 600; line-height: 1.7; padding: 1px 6px; margin-left: 5px;
  border-radius: 5px; background: #eaf0f7; color: #294c72; white-space: nowrap; }
.typed-name[data-kind="person"]::after { background: #eee9fa; color: #51317d; }
.typed-name[data-kind="company"]::after { background: #e2f1f6; color: #18566a; }
.typed-name[data-kind="authority"]::after { background: #fff2d8; color: #704500; }
.typed-name[data-kind="outlet"]::after { background: #e5f4ea; color: #174a2b; }
.typed-name[data-kind="place"]::after { background: #fce8e7; color: #7c2925; }
details { margin-top: 16px; }
summary { cursor: pointer; font-weight: 600; padding: 8px 0; color: #125e72; }
.answer .typed-name::after { color: #172d34; }
.answer summary { color: #d6edf4; font-size: .85rem; }
.source-dots li { margin: 10px 0; font-size: .85rem; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 8px; }
.dot.good { background: #267545; } .dot.warn { background: #a3670a; } .dot.bad { background: #ae3832; }
.verdict { font-weight: 600; }
footer { border-top: 1px solid #b8ccd1; margin-top: 28px; padding-top: 16px; font-size: .8rem; }
main, h1, h2, h3, p, div, blockquote, footer, a { overflow-wrap: anywhere; }
@media (max-width: 700px) {
  main { padding: 20px 14px 30px; }
  .overview { gap: 8px; }
  .overview div { padding: 10px 8px; font-size: .75rem; }
  .answer { padding: 20px 16px; }
  .answer-line { font-size: 1.25rem; }
  .reading { padding: 10px 6px; font-size: .85rem; }
}
@media print { :root { background: white; } .card, .source { break-inside: avoid; } }
"""


def text(value):
    return escape(str(value), quote=True)


def document(title, body):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
            'style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">'
            '<title>' + text(title) + '</title><style>' + STYLE + '</style></head>'
            '<body><main>' + body + '</main></body></html>\n')


def commit_id():
    """Read optional local provenance, never contact a remote."""
    try:
        proc = subprocess.run(['git', 'rev-parse', 'HEAD'],
                              cwd=Path(__file__).resolve().parents[3],
                              capture_output=True, text=True, timeout=2)
        value = proc.stdout.strip()
        if proc.returncode == 0 and re.fullmatch(r'[0-9a-f]{40,64}', value):
            return value
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def authority(quote):
    """Copy only the supplied sample's authority clause. Never infer a name."""
    for pattern in (r'^(The .+?) (?:designated|imposed|fined|announced)\b',
                    r', (the .+?) (?:is investigating|said|delisted|imposed)\b'):
        match = re.search(pattern, quote)
        if match:
            return match[1]
    return 'Not stated separately; see exact quote.'


def readings(check):
    values = check.get('readings', [])
    if not values:
        return ''
    if len(values) != 3 or check.get('chosen_reading') is not None:
        raise ValueError('Three unchosen identity readings required')
    meaning = '<p class="meta">Entity means company.</p>' if 'same entity' in values else ''
    return (meaning + '<div class="readings" aria-label="Three equally weighted identity readings">'
            + ''.join('<div class="reading">' + text(v) + '</div>' for v in values)
            + '</div><p><strong>Tool chooses none.</strong></p>')


TAGS = {'person': '👤 Person', 'company': '🏢 Company', 'authority': '🏛 Authority',
        'outlet': '📰 News outlet', 'place': '📍 Place'}


def display_date(value):
    """Use fixed English month names, independent of the machine locale."""
    parsed = date.fromisoformat(value)
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    return f'{parsed.day} {months[parsed.month - 1]} {parsed.year}'


def records(report):
    for group in ('findings', 'possible_matches', 'excluded_articles', 'non_events'):
        for record in report.get(group, []):
            yield record
            if 'resolution' in record:
                yield record['resolution']


def name_types(report):
    """Use copied structured fields and the explicit authority clause only.

    Report subject/source fields originate in subjects.json/sources.json.
    Never infer types from invented spelling. Conflicting types stay unknown.
    """
    names = {}

    def add(name, kind, description):
        if name and kind in TAGS:
            if name in names and names[name][0] != kind:
                names[name] = (None, 'type not established by the supplied fields')
            elif name not in names:
                names[name] = (kind, description)

    subject = report['subject']
    add(subject['name'], subject.get('type'), 'the person we checked' if subject.get('type') == 'person'
        else 'the company we checked')
    for field, kind, description in (('employer', 'company', 'employer of the person we checked'),):
        add(subject.get(field), kind, description)
    for record in records(report):
        written = authority(record['quote'])
        if written in record['quote']:
            name = re.sub(r'^[Tt]he ', '', written)
            action = ('reported the case outcome' if record.get('event') == 'delisting or case closed' else
                      'imposed the restriction' if record.get('event') == 'designation' else
                      'authority named in the report')
            add(name, 'authority', action)
            if record.get('event') == 'delisting or case closed' and names.get(name, (None,))[0] == 'authority':
                names[name] = ('authority', 'reported a delisting or case outcome')
        fields = record.get('identity_check', {}).get('stated_fields', {})
        for field, kind, description in (('employer', 'company', 'employer stated in an article'),):
            add(fields.get(field), kind, description)
    for source in report['sources']:
        add(source['source'], 'outlet', 'news source in the supplied sample')
    return names


def named(value, names):
    """Keep copied quote/summary textContent verbatim with CSS-generated tags.

    Each span also carries an accessible name including the icon and type.
    """
    value = str(value)
    known = [name for name, (kind, _) in names.items() if kind in TAGS]
    if not known:
        return text(value)
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(n) for n in sorted(known, key=lambda n: (-len(n), n))) + r')(?!\w)'
    chunks, end = [], 0
    for match in re.finditer(pattern, value):
        name = match[0]
        kind = names[name][0]
        chunks.append(text(value[end:match.start()]))
        chunks.append('<span class="typed-name" data-kind="' + kind + '" data-tag="' + TAGS[kind]
                      + '" aria-label="' + text(name + ', ' + TAGS[kind]) + '">' + text(name) + '</span>')
        end = match.end()
    return ''.join(chunks) + text(value[end:])


def evidence(record, names):
    return ('<p class="meta">' + text(record['source_id']) + ' · ' + named(record['source'], names)
            + ' · ' + text(record['article_id']) + ' · <time>' + text(record['date'])
            + '</time></p><p>Authority as written: <strong>' + named(authority(record['quote']), names)
            + '</strong></p><blockquote>' + named(record['quote'], names) + '</blockquote>')


def details(label, body):
    return '<details><summary>' + text(label) + '</summary>' + body + '</details>'


def event_heading(event):
    meanings = {'designation': 'named under a restriction',
                'penalty or settlement': 'a fine or agreed case outcome',
                'open investigation': 'an inquiry with no reported outcome',
                'historical investigation': 'an earlier inquiry, not a current-state claim',
                'delisting or case closed': 'removed from a restrictions list or case ended'}
    meaning = meanings.get(event)
    return '<h3>' + text(event) + (' (' + text(meaning) + ')' if meaning else '') + '</h3>'


def verdict(check, subject):
    if check.get('conflicting_fields'):
        fields = ', '.join(check['conflicting_fields'])
        return 'Different ' + ('person' if subject['type'] == 'person' else 'company') + ': ' + fields + ' do not match.'
    if set(check.get('matched_fields', [])) == {'name', 'role', 'employer', 'age'}:
        return 'Same person: name, role, employer and age all match.'
    if check.get('decision') == 'possible':
        return 'Same name, but not enough information to confirm who this is. Human review required.'
    fields = ', '.join(check.get('matched_fields', []))
    return fields.capitalize() + ' match. Identity still needs human review.'


def finding_card(record, subject, names, kind='finding'):
    when = display_date(record['date'])
    if kind == 'linked':
        happened = 'An inquiry was reported on ' + when + '; case closed on ' + display_date(record['resolution']['date']) + '.'
    elif kind == 'dated':
        happened = 'An inquiry was reported on ' + when + '. No later report was found; its status is unknown.'
    elif kind == 'possible':
        happened = 'A sanctions story dated ' + when + ' names someone who may not be the subject checked.'
    elif record.get('state') == 'reported delisting':
        happened = 'A delisting was reported on ' + when + '; no earlier case is confirmed linked.'
    else:
        happened = {'designation': 'Restricted by an authority on ' + when + '.',
                    'penalty or settlement': 'A fine or settlement was reported on ' + when + '.',
                    'delisting or case closed': 'Removal from a restrictions list or a case closure was reported on ' + when + '.',
                    'open investigation': 'An inquiry was reported on ' + when + '; the allegations are not proven.'
                    }.get(record['event'], 'A sanctions story was reported on ' + when + '.')
    body = '<h3>' + text(happened) + '</h3><p class="verdict">' + text(verdict(record['identity_check'], subject)) + '</p>'
    label = 'reported delisting' if record.get('state') == 'reported delisting' else record['event']
    proof = event_heading(label) + '<p>' + text(record['assessment']) + '</p>'
    if kind == 'linked':
        proof += '<p>case closed on ' + text(record['resolution']['date']) + '</p>'
    if kind == 'dated':
        proof += '<p>dated finding, no follow-up found in supplied sources, status unknown</p>'
    proof += evidence(record, names)
    proof += '<p>Identity: ' + text(record['identity_check']['identity']) + '.</p>'
    proof += readings(record['identity_check'])
    proof += ''.join('<p>' + named(line, names) + '</p>' for line in record.get('article_context', []))
    if kind == 'linked':
        proof += '<div class="arrow" aria-label="followed by">↓</div><h3>Later authority decision</h3>'
        proof += evidence(record['resolution'], names)
    return '<article class="card ' + kind + '">' + body + details('Show the evidence', proof) + '</article>'


def section(title, cards):
    if not cards:
        return ''
    return '<section><h2>' + text(title) + '</h2><div class="cards">' + ''.join(cards) + '</div></section>'


def source_strip(sources, names, gaps):
    blocks = []
    tones = {'completed': 'good', 'current': 'good', 'stale': 'warn',
             'failed': 'bad', 'not attempted': 'bad', 'unavailable': 'bad',
             'possible hit': 'warn', 'no hit': 'neutral'}
    for source in sources:
        body = '<h3>' + text(source['source_id']) + '<br>' + named(source['source'], names) + '</h3>'
        for field in ('execution', 'result', 'freshness'):
            value = source[field]
            body += ('<div class="label ' + tones.get(value, 'neutral') + '" data-label="' + field
                     + '"><strong>' + field + ': ' + text(value) + '</strong><br>as_of: '
                     + text(source['field_as_of'][field]) + '</div>')
        body += '<p>as_of: ' + text(source['as_of']) + '<br>' + text(source['date_basis']) + '</p>'
        body += '<p>Articles checked: ' + text(', '.join(source['article_ids_checked']) or 'none') + '</p>'
        blocks.append('<article class="source">' + body + '</article>')
    completed = sum(s['execution'] == 'completed' and s['result'] != 'unavailable' for s in sources)
    failed = sum(s['execution'] == 'failed' for s in sources)
    not_run = sum(s['execution'] == 'not attempted' for s in sources)
    old = [s for s in sources if s['freshness'] == 'stale']
    incomplete = sum(s['execution'] == 'completed' and s['result'] == 'unavailable' for s in sources)
    line = f'Checked {completed} of {len(sources)} news sources. {failed} failed. {not_run} was not run.'
    if old:
        dates = ', '.join(display_date(s['as_of']) for s in old)
        line += f' {len(old)} is old (last updated {dates}).'
    if incomplete:
        line += f' {incomplete} ran but could not be fully read.'
    dots = []
    for source in sources:
        state = ('failed' if source['execution'] == 'failed' else
                 'not run' if source['execution'] == 'not attempted' else
                 'incomplete' if source['result'] == 'unavailable' else
                 'old' if source['freshness'] == 'stale' else 'checked')
        tone = 'bad' if state in {'failed', 'not run', 'incomplete'} else 'warn' if state == 'old' else 'good'
        dots.append('<li><span class="dot ' + tone + '" aria-hidden="true"></span>'
                    + named(source['source'], names) + ' · ' + state + '</li>')
    proof = ('<p class="meta">Execution = did the check run? '
            'Result = what did it report? Freshness = how old is the supplied snapshot? '
            'No hit means no finding in supplied articles, not complete coverage. '
            'as_of = the snapshot or planned-check date.</p>'
            '<div class="sources">' + ''.join(blocks) + '</div>' + gaps)
    return ('<section><h2>Sources</h2><p>' + text(line) + '</p><ul class="source-dots">'
            + ''.join(dots) + '</ul>' + details('Source details', proof) + '</section>')


def case_closed(record):
    # A reported delisting alone must not close any earlier finding.
    return 'resolution' in record


def answer_counts(report):
    closed = sum(case_closed(f) for f in report['findings'])
    return len(report['findings']) - closed, len(report['excluded_articles']) + closed, len(report['not_covered'])


def answer_sentence(report):
    hits, _, gaps = answer_counts(report)
    closed = sum(case_closed(f) for f in report['findings'])
    ruled = len(report['excluded_articles'])
    possible = len(report.get('possible_matches', []))
    parts = [f'{hits} sanctions news finding' + ('' if hits == 1 else 's')]
    if hits == 0 and closed:
        parts = []
    if closed:
        parts.append(f'{closed} earlier case' + (' is' if closed == 1 else 's are') + ' closed')
    if any(f['identity_check'].get('readings') for f in report['findings']):
        parts.append('identity still needs human review')
    if ruled:
        noun = 'person' if report['subject']['type'] == 'person' else 'company'
        parts.append(f'{ruled} same-name ' + noun + (' ruled out' if ruled == 1 else ' matches ruled out'))
    if possible:
        parts.append(f'{possible} possible identity match' + ('' if possible == 1 else 'es')
                     + (' needs' if possible == 1 else ' need') + ' human review')
    parts.append(f'{gaps} source' + ('' if gaps == 1 else 's') + ' could not be fully checked')
    return '; '.join(parts) + '.'


def render_page(report, report_path, commit=None):
    subject = report['subject']
    names = name_types(report)
    regular, linked, dated = [], [], []
    for finding in report['findings']:
        if 'resolution' in finding:
            linked.append(finding_card(finding, subject, names, 'linked'))
        elif finding['state'] == 'historical status unknown':
            dated.append(finding_card(finding, subject, names, 'dated'))
        else:
            regular.append(finding_card(finding, subject, names))
    gaps = report['not_covered']
    summary = '<p class="headline">' + named(report['summary'], names) + '</p>'
    # The no-findings report contains raw source ids. Preserve it verbatim,
    # immediately below the answer, but keep its jargon one tap away.
    if re.search(r'SRC-|ART-|as_of|execution', report['summary'], re.IGNORECASE):
        summary = details('Original report summary', summary)
        if 'This is not a clearance.' in report['summary']:
            summary += '<p class="headline">This is not a clearance.</p>'
    body = ('<header><div class="kicker">Sanctions news · supplied sample only</div><h1>'
            + named(subject['name'], names) + '</h1><p class="meta">Checked on <time>'
            + display_date(report['as_of']) + '</time></p></header>'
            '<p class="notice">Invented sample data. No live news search or sanctions-list check.</p>'
            '<p><a href="dashboard.html#' + text(subject['id']) + '">Open this subject in the news timeline</a></p>'
            '<section class="answer"><h2>The answer</h2><p class="answer-line">'
            + text(answer_sentence(report)) + '</p>' + summary)
    body += '<div class="overview" aria-label="At a glance">'
    for count, label in zip(answer_counts(report), ('Confirmed hits', 'Ruled out or closed', 'Not checked')):
        body += '<div><strong>' + str(count) + '</strong>' + label + '</div>'
    body += '</div><p class="headline">Hits count reported news events, not identity decisions.</p></section>'
    body += '<p class="meta">News reports are not proof of conduct or a current restrictions-list match. '
    body += 'Not checked includes missing checks and old coverage. Human review required; the tool makes no decision.</p>'
    body += '<section class="who"><h2>Who’s who</h2><ul>'
    primary, secondary = [], []
    for name, (kind, description) in names.items():
        row = '<li>' + named(name, names) + '<span class="description"> · ' + text(description) + '</span></li>'
        (primary if name == subject['name'] or kind == 'authority' else secondary).append(row)
    body += ''.join(primary) + '</ul>'
    if secondary:
        body += details('More names · ' + str(len(secondary)), '<ul>' + ''.join(secondary) + '</ul>')
    body += ('<p class="meta">Company, person, authority and outlet names are placeholders. '
             'The sample is local in style only; no real place names are used.</p></section>')
    body += section('What happened', regular)
    body += section('Earlier case, now closed', linked)
    body += section('Older report, status unknown', dated)
    possible = []
    for record in report.get('possible_matches', []):
        possible.append(finding_card(record, subject, names, 'possible'))
    body += section('Possible matches (not enough evidence)', possible)
    excluded = []
    for record in report['excluded_articles']:
        check = record['identity_check']
        fields = check.get('conflicting_fields', [])
        comparison = '<div class="comparison">'
        for label, values in (('Subject', subject), ('Article', check['stated_fields'])):
            comparison += '<div><h3>' + label + '</h3>'
            for field in fields:
                value = values.get(field, 'not stated')
                if field == 'age' and label == 'Subject':
                    item = next((a for a in report.get('comparisons', []) if a['article_id'] == record['article_id']), None)
                    if item:
                        value = item['fields']['age']['subject_value']
                comparison += '<p><strong>' + text(field) + ':</strong> ' + named(value, names) + '</p>'
            comparison += '</div>'
        comparison += '</div>'
        excluded.append('<article class="card excluded"><h3>A story dated ' + display_date(record['date'])
                        + ' refers to a different ' + ('person' if subject['type'] == 'person' else 'company') + '.</h3>'
                        + '<p class="verdict">' + text(verdict(check, subject)) + '</p>'
                        + details('Show the evidence', comparison + evidence(record, names)
                                  + '<p>' + text(record['reason']) + '</p>') + '</article>')
    body += section('Same name, different ' + ('person' if subject['type'] == 'person' else 'company'), excluded)
    non_events = ['<article class="card"><h3>Ordinary news mention on ' + display_date(r['date'])
                  + '.</h3>' + details('Show the evidence', evidence(r, names)) + '</article>'
                  for r in report.get('non_events', [])]
    if non_events:
        body += details('Other mentions (not sanctions events) · ' + str(len(non_events)),
                        '<div class="cards">' + ''.join(non_events) + '</div>')
    by_source = {s['source_id']: s for s in report['sources']}
    gap_cards = []
    for gap in gaps:
        source = by_source[gap['source_id']]
        limit = ('Coverage stops at ' + gap['as_of'] + '. Nothing checked after this date.'
                 if gap['execution'] == 'completed' else
                 'No date coverage established. ' + gap['as_of'] + ' is a planned date only, nothing read.')
        gap_cards.append('<article class="card"><h3>' + text(gap['source_id']) + ' · ' + named(source['source'], names)
                         + '</h3><p>' + text(gap['execution']) + ' · ' + text(gap['freshness'])
                         + ' · as_of: ' + text(gap['as_of']) + '</p><p><strong>' + text(limit)
                         + '</strong></p><p>' + text(gap['reason']) + '</p></article>')
    body += source_strip(report['sources'], names, section('What was not covered', gap_cards))
    provenance = report.get('commit_id') or commit or 'not recorded'
    proof = ('<p>Skill version: ' + text(report['skill_version']) + ' · Commit id: ' + text(provenance)
             + ' (saved code version)</p><p>Generated from ' + text(report_path) + '</p><p>Run date: '
             + text(report['as_of']) + '</p>')
    body += '<footer>' + details('About this sample', proof + '<p>Invented sample data. No live news search or sanctions-list check.</p>'
                                '<p>Company, person, authority and outlet names are placeholders. '
                                'The sample is local in style only; no real place names are used.</p>'
                                '<p>Human review required. The tool chooses no disposition.</p>') + '</footer>'
    return document(subject['name'] + ' · findings', body)


def render_index(items):
    cards = []
    for path, report in items:
        names = name_types(report)
        cards.append('<article class="card"><h2><a href="' + text(path.with_suffix('.html').name)
                     + '">' + named(report['subject']['name'], names)
                     + ' →</a></h2><p>' + text(answer_sentence(report)) + '</p>'
                     + details('Report summary', '<p>' + named(report['summary'], names) + '</p>') + '</article>')
    return document('Sanctions news · subject runs', '<header><h1>Sanctions news · subject runs</h1>'
                    '<p>Invented sample data. No live news search or sanctions-list check.</p>'
                    '<p>Company, person, authority and outlet names are placeholders. '
                    'The sample is local in style only; no real place names are used.</p>'
                    '<p><strong>Human review required. The tool chooses no disposition.</strong></p></header>'
                    '<section class="timeline-entry" aria-label="Start here">'
                    '<a href="dashboard.html">Open the dashboard and news timeline</a>'
                    '<p>Choose a subject, then click a dated timeline mark to read the source sentence.</p></section>'
                    '<div class="cards">' + ''.join(cards) + '</div>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--report', type=Path)
    group.add_argument('--all', dest='folder', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--commit-id', help='pin saved research provenance for a portable frozen demo')
    args = parser.parse_args(argv)
    if bool(args.report) != bool(args.out):
        parser.error('--report requires --out; --all writes beside each report')
    if args.commit_id is not None and not re.fullmatch(r'[0-9a-f]{40,64}', args.commit_id):
        parser.error('--commit-id must be a full hexadecimal commit id')
    try:
        paths = sorted(args.folder.glob('*.json')) if args.folder else [args.report]
        if not paths:
            raise ValueError('No report JSON files found')
        commit = args.commit_id or commit_id()
        items, outputs = [], []
        for path in paths:
            report = json.loads(path.read_text(encoding='utf-8'))
            out = path.with_suffix('.html') if args.folder else args.out
            if out.resolve() == path.resolve():
                raise ValueError('HTML output must not overwrite report JSON')
            outputs.append((out, render_page(report, path, commit)))
            items.append((path, report))
        if args.folder:
            outputs.append((args.folder / 'index.html', render_index(items)))
        # Render all inputs before writing, so invalid input cannot leave a
        # misleading partly refreshed set of pages.
        for out, html in outputs:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding='utf-8')
            print(str(out))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Page render failed: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
