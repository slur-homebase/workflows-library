"""Rule-based comparison for the supplied sample grammar, not general news extraction."""

from typing import Any


def extract_fields(subject, article, split_sentences, read_identity, age_at):
    """Keep values and their complete, verbatim supporting sentences together."""
    import re

    fields = ('name', 'profile', 'age', 'position') if subject['type'] == 'person' else (
        'name', 'profile', 'key_people')
    found: dict[str, dict[str, Any]] = {field: {'value': None, 'source_sentence': None} for field in fields}
    stated = {}
    for sentence in split_sentences(article['body']):
        identity = read_identity(subject, sentence)
        if identity is not None:
            if found['name']['value'] is None:
                found['name'] = {'value': subject['name'], 'source_sentence': sentence}
            for key, value in identity.items():
                stated.setdefault(key, (value, sentence))
    if subject['type'] == 'company':
        if 'profile' in stated:
            value, sentence = stated['profile']
            found['profile'] = {'value': value, 'source_sentence': sentence}
        # This pronoun grammar applies only to a single-company sample article.
        people = re.search(r'Its director is ([A-Z][A-Za-z -]+)\.', article['body'])
        if people:
            sentence = next(s for s in split_sentences(article['body']) if people[0] in s)
            found['key_people'] = {'value': people[1], 'source_sentence': sentence}
    else:
        if 'age' in stated:
            value, sentence = stated['age']
            found['age'] = {'value': value, 'source_sentence': sentence}
        if 'role' in stated:
            role, sentence = stated['role']
            employer = stated.get('employer')
            value = role + (' at ' + employer[0] if employer and employer[1] == sentence else '')
            found['position'] = {'value': value, 'source_sentence': sentence}
        profile = re.search(r'(?:His work focuses on |His work focused on |He works as a )([^.!?]+)[.!?]',
                            article['body'])
        if profile:
            sentence = next(s for s in split_sentences(article['body']) if profile[0] in s)
            found['profile'] = {'value': profile[1], 'source_sentence': sentence}
    expected = {'name': subject['name'], 'profile': subject.get('profile')}
    if subject['type'] == 'person':
        expected['age'] = age_at(subject, article['date'])
        expected['position'] = subject.get('role', '') + (
            ' at ' + subject['employer'] if subject.get('employer') else '')
    else:
        expected['key_people'] = ', '.join(subject.get('key_people', [])) or None
    for field, cell in found.items():
        value = cell['value']
        cell['subject_value'] = expected[field]
        cell['status'] = 'Not stated'
        cell['comparison_note'] = ''
        if value is not None:
            # Compare only stated components. Do not manufacture a missing employer.
            target = expected[field]
            if field == 'position' and 'employer' not in stated:
                target = subject.get('role')
                cell['comparison_note'] = 'Role only. Employer not stated in this article.'
            if target is None:
                # The media supplied a value but the subject record did not.
                cell['status'] = 'Not stated'
                cell['comparison_note'] = 'Our subject has no value for comparison.'
                cell['reported_only'] = dict(value=value, source_sentence=cell['source_sentence'])
                cell['value'] = cell['source_sentence'] = None
            else:
                cell['status'] = 'Same' if value.casefold() == target.casefold() else 'Different'
            if cell['value'] is not None:
                if not cell['source_sentence'] or cell['source_sentence'] not in article['body']:
                    raise ValueError('Ungrounded source sentence')
                if cell['value'] not in cell['source_sentence']:
                    raise ValueError('Ungrounded media value')
    return found


def comparisons(subject, articles, report, split_sentences, read_identity, age_at,
                story_context=None):
    """Use report verdicts unchanged; comparisons never feed the verdict matcher."""
    verdicts = {}
    for group in ('findings', 'possible_matches', 'excluded_articles', 'non_events'):
        for record in report[group]:
            if group == 'findings':
                verdict = record['assessment']
            elif group == 'excluded_articles':
                verdict = record['reason']
            elif group == 'possible_matches':
                verdict = 'Possible match, not enough evidence. Human review required.'
            else:
                verdict = 'Not a sanctions event.'
            verdicts.setdefault(record['article_id'], verdict)
            if 'resolution' in record:
                verdicts[record['resolution']['article_id']] = record['assessment']
    sources = {s['source_id']: s for s in report['sources']}
    result = []
    for article in articles:
        source = sources[article['source_id']]
        if source['execution'] != 'completed':
            continue
        # Body name match only. Metadata and headlines cannot force a result.
        import re
        if not re.search(r'(?<!\w)' + re.escape(subject['name']) + r'(?!\w)', article['body']):
            continue
        result.append({'article_id': article['id'], 'headline': article['headline'],
                       'outlet': source['source'], 'date': article['date'],
                       'source_status': {f: source[f] for f in ('execution', 'result', 'freshness', 'as_of')},
                       'body': article['body'],
                       **(story_context(article) if story_context is not None else {}),
                       'verdict': verdicts.get(article['id'], 'No confirmed finding. Human review required.'),
                       'fields': extract_fields(subject, article, split_sentences, read_identity, age_at)})
    return result
