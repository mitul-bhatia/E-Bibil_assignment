"""Find sections and source-preserving passages in the original Markdown."""
from functools import lru_cache
import hashlib
import json
import re

from settings import DATA_DIR, DOCUMENTS_DIR, EMBEDDING_MODEL, MAX_EMBEDDING_TOKENS


@lru_cache(maxsize=1)
def get_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


def token_count(text, tokenizer):
    return len(tokenizer.encode(text, add_special_tokens=False))


def embedding_text(title, section, text):
    return f'{title}\n{section}\n{text}'


def load_documents():
    manifest = json.loads((DATA_DIR / 'sources.json').read_text())
    documents = []
    for source in manifest['documents']:
        path = DOCUMENTS_DIR / source['file'].split('/')[-1]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError(f'{path.name} changed. Update the source manifest before preprocessing.')
        documents.append({**source, 'filename': path.name, 'text': raw.decode('utf-8')})
    return documents


def find_sections(text):
    """Recognize both # headings and headings followed by === or --- lines."""
    lines = text.splitlines(keepends=True)
    headings = []
    offset = 0
    hierarchy = []
    for index, line in enumerate(lines):
        atx = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line.rstrip())
        underline = None
        if index + 1 < len(lines) and line.strip():
            underline = re.fullmatch(r' {0,3}(=+|-+)\s*', lines[index + 1].rstrip())
        if atx or underline:
            level = len(atx[1]) if atx else (1 if underline[1][0] == '=' else 2)
            title = atx[2] if atx else line.strip()
            title = re.sub(r'[*`]', '', title).replace('\\.', '.')
            hierarchy = [(depth, name) for depth, name in hierarchy if depth < level]
            hierarchy.append((level, title))
            headings.append((offset, ' → '.join(name for _, name in hierarchy)))
        offset += len(line)
    if not headings or headings[0][0] != 0:
        headings.insert(0, (0, 'Introduction'))
    return [
        {'start': start, 'end': headings[i + 1][0] if i + 1 < len(headings) else len(text), 'section': title}
        for i, (start, title) in enumerate(headings)
    ]


def split_large_passage(text, start, end, tokenizer, limit=110):
    """Split only oversized paragraphs, preferring sentence endings over token cuts."""
    offsets = tokenizer(text[start:end], add_special_tokens=False, return_offsets_mapping=True)['offset_mapping']
    cursor = start
    while cursor < end:
        remaining = [(start + a, start + b) for a, b in offsets if start + b > cursor]
        if len(remaining) <= limit:
            yield cursor, end
            break
        hard_end = remaining[limit][0]
        candidates = list(re.finditer(r'[.!?](?:["”\')])?\s+', text[cursor:hard_end]))
        cut = cursor + candidates[-1].end() if candidates else hard_end
        if cut <= cursor:
            raise ValueError('Could not split a source passage safely.')
        yield cursor, cut
        cursor = cut


def make_passages(document, tokenizer):
    """Every character is covered exactly once. Gemini decides how to group these units."""
    passages = []
    text = document['text']
    for section in find_sections(text):
        start, end = section['start'], section['end']
        cuts = [start] + [start + match.end() for match in re.finditer(r'\n\s*\n', text[start:end])] + [end]
        cuts = sorted(set(cuts))
        for left, right in zip(cuts, cuts[1:]):
            for passage_start, passage_end in split_large_passage(text, left, right, tokenizer):
                passages.append({
                    'id': len(passages), 'start': passage_start, 'end': passage_end,
                    'section': section['section'],
                })
    if ''.join(text[p['start']:p['end']] for p in passages) != text:
        raise ValueError('Source coverage check failed.')
    return passages


def validate_boundaries(boundaries, passages, document, tokenizer):
    """Reject dropped/reordered passages, mixed sections and oversized embedding inputs."""
    if not boundaries or boundaries[-1] != len(passages) - 1:
        raise ValueError('Boundaries must include the last passage.')
    first = 0
    groups = []
    for last in boundaries:
        if type(last) is not int or last < first or last >= len(passages):
            raise ValueError('Boundary IDs must be valid, strictly increasing integers.')
        group = passages[first:last + 1]
        if len({p['section'] for p in group}) != 1:
            raise ValueError(f'Chunk ending at passage {last} crosses a section boundary.')
        text = document['text'][group[0]['start']:group[-1]['end']]
        size = token_count(embedding_text(document['title'], group[0]['section'], text), tokenizer)
        if size > MAX_EMBEDDING_TOKENS:
            raise ValueError(f'Chunk ending at passage {last} has {size} tokens; maximum is {MAX_EMBEDDING_TOKENS}.')
        groups.append({'start': group[0]['start'], 'end': group[-1]['end'], 'section': group[0]['section']})
        first = last + 1
    if ''.join(document['text'][g['start']:g['end']] for g in groups) != document['text']:
        raise ValueError('Chunk groups do not reconstruct the original document.')
    return groups
