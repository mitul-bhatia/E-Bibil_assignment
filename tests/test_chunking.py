"""Offline safety checks; this tokenizer fixture is NOT an embedding-model evaluation."""
import re

import pytest

from documents import find_sections, make_passages, validate_boundaries
import prepare_chunks
from prepare_chunks import add_overlap


class WordTokenizer:
    """A tiny test double so source-integrity tests need no model downloads."""

    def encode(self, text, add_special_tokens=False):
        return list(range(len(re.findall(r'\S+', text))))

    def __call__(self, text, **kwargs):
        return {'offset_mapping': [(match.start(), match.end()) for match in re.finditer(r'\S+', text)]}


def document(text):
    return {'text': text, 'title': 'Test policy', 'filename': 'test.md', 'source_url': 'https://example.com/policy'}


def test_both_heading_styles_and_preamble_are_preserved():
    text = 'Preamble\n\nPolicy\n======\n\n## Payment\nPay first.\n\n### Exceptions\nRefunds apply.\n'
    sections = find_sections(text)
    assert [section['section'] for section in sections] == [
        'Introduction', 'Policy', 'Policy → Payment', 'Policy → Payment → Exceptions',
    ]
    assert ''.join(text[section['start']:section['end']] for section in sections) == text


def test_long_unicode_paragraph_and_whitespace_have_exact_coverage():
    text = 'Policy\n------\n\n' + ('Customer’s data—preserve it. ' * 200) + '\n\n'
    original = document(text)
    passages = make_passages(original, WordTokenizer())
    assert ''.join(text[p['start']:p['end']] for p in passages) == text
    assert len(passages) > 3


@pytest.mark.parametrize('boundaries', [[0], [1, 0, 2], [True, 2], [-1, 2], [3]])
def test_missing_reordered_or_invalid_passages_are_rejected(boundaries):
    passages = [
        {'id': i, 'start': i * 2, 'end': i * 2 + 2, 'section': 'Same'} for i in range(3)
    ]
    with pytest.raises(ValueError):
        validate_boundaries(boundaries, passages, document('a b c '), WordTokenizer())


def test_section_crossing_and_oversized_chunks_are_rejected():
    passages = [
        {'id': 0, 'start': 0, 'end': 2, 'section': 'A'},
        {'id': 1, 'start': 2, 'end': 4, 'section': 'B'},
    ]
    with pytest.raises(ValueError, match='section'):
        validate_boundaries([1], passages, document('a b '), WordTokenizer())
    original = document('word ' * 300)
    with pytest.raises(ValueError, match='tokens'):
        validate_boundaries([0], [{'id': 0, 'start': 0, 'end': len(original['text']), 'section': 'A'}], original, WordTokenizer())


def test_overlap_uses_original_text_and_stops_at_section_boundary():
    text = ' '.join(f'w{i}' for i in range(120))
    split = text.index('w60 ')
    second_split = text.index('w100 ')
    groups = [
        {'start': 0, 'end': split, 'section': 'A'},
        {'start': split, 'end': second_split, 'section': 'A'},
        {'start': second_split, 'end': len(text), 'section': 'B'},
    ]
    chunks = add_overlap(document(text), groups, WordTokenizer())
    assert chunks[1]['overlap_tokens'] == 30
    assert chunks[1]['start'] < chunks[1]['core_start']
    assert chunks[2]['overlap_tokens'] == 0
    assert ''.join(text[chunk['core_start']:chunk['end']] for chunk in chunks) == text
    assert all(chunk['text'] == text[chunk['start']:chunk['end']] for chunk in chunks)


def test_gemini_receives_the_complete_document_not_individual_sections(monkeypatch):
    import json
    original = document('# A\n\nFirst rule.\n\n# B\n\nSecond rule.\n')
    tokenizer = WordTokenizer()
    passages = make_passages(original, tokenizer)
    boundaries = [
        index for index, passage in enumerate(passages)
        if index == len(passages) - 1 or passage['section'] != passages[index + 1]['section']
    ]
    prompts = []
    def fake_gemini(model, instructions, prompt, schema):
        prompts.append(json.loads(prompt))
        return {'boundaries': boundaries}
    monkeypatch.setattr(prepare_chunks, 'generate_json', fake_gemini)
    groups, _, attempts = prepare_chunks.choose_groups(original, passages, tokenizer, 'test-model')
    assert attempts == 1 and len(prompts) == 1
    assert ''.join(p['text'] for p in prompts[0]['complete_document']) == original['text']
    assert ''.join(original['text'][g['start']:g['end']] for g in groups) == original['text']


def test_invalid_gemini_boundaries_do_not_silently_create_fallback_chunks(monkeypatch):
    original = document('# A\n\nFirst rule.\n\n# B\n\nSecond rule.\n')
    tokenizer = WordTokenizer()
    passages = make_passages(original, tokenizer)
    monkeypatch.setattr(prepare_chunks, 'generate_json', lambda *args: {'boundaries': [len(passages) - 1]})
    with pytest.raises(ValueError, match='invalid boundaries twice'):
        prepare_chunks.choose_groups(original, passages, tokenizer, 'test-model')
