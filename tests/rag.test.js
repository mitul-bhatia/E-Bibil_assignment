import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { chunkDocument } from '../lib/chunk.js';
import { search, resolveAnswer, UNKNOWN } from '../lib/rag.js';
import { POST } from '../app/api/ask/route.js';

test('real document chunks preserve exact source passages and recognizable sections', () => {
  const manifest = JSON.parse(readFileSync('data/sources.json', 'utf8'));
  for (const source of manifest.documents) {
    const text = readFileSync(source.file, 'utf8');
    const chunks = chunkDocument(text, source);
    assert.ok(chunks.length > 0);
    assert.equal(new Set(chunks.map(chunk => chunk.id)).size, chunks.length);
    for (const chunk of chunks) {
      assert.ok(text.includes(chunk.text));
      assert.ok(chunk.text.length <= 1800);
      assert.equal(chunk.url, source.source_url);
    }
  }
});

test('long sections have overlap, no gaps, and never cross headings', () => {
  const section = 'First rule. '.repeat(30);
  const text = `Policy\n======\n\n## Retention\n${section}\n\n## Cookies\nCookie controls.\n`;
  const chunks = chunkDocument(text, { file: 'policy.md', title: 'Policy', source_url: 'https://example.com' }, 90, 20);
  const retention = chunks.filter(chunk => chunk.section === 'Policy → Retention');
  let covered = '';
  for (const chunk of retention) {
    if (!covered) covered = chunk.text;
    else {
      assert.equal(covered.slice(-20), chunk.text.slice(0, 20));
      covered += chunk.text.slice(20);
    }
    assert.ok(!chunk.text.includes('## Cookies'));
  }
  assert.equal(covered, `## Retention\n${section}\n\n`);
});

test('normalized cosine retrieval ranks exact matches first and strips stored vectors', () => {
  const results = search([{ id: 'opposite', vector: [-1, 0] }, { id: 'match', vector: [1, 0] }, { id: 'other', vector: [0, 1] }], [1, 0], 2);
  assert.deepEqual(results.map(result => result.id), ['match', 'other']);
  assert.equal(results[0].score, 1);
  assert.ok(!('vector' in results[0]));
});

test('citations are restricted to retrieved evidence and unknown answers have no sources', () => {
  const passage = { id: 'privacy-1', document: 'Privacy', section: 'Retention', text: '30 days', url: 'https://example.com' };
  assert.throws(() => resolveAnswer({ answerable: true, answer: '30 days', source_ids: ['invented'] }, [passage]));
  assert.throws(() => resolveAnswer({ answerable: true, answer: '30 days', source_ids: [] }, [passage]));
  assert.deepEqual(resolveAnswer({ answerable: false, answer: 'Guess', source_ids: ['invented'] }, [passage]), { answer: UNKNOWN, answerable: false, sources: [] });
  assert.deepEqual(resolveAnswer({ answerable: true, answer: '30 days', source_ids: ['privacy-1', 'privacy-1'] }, [passage]).sources, [passage]);
});

test('API rejects malformed, empty and oversized questions before calling Google', async () => {
  for (const body of ['invalid json', JSON.stringify({ question: ' ' }), JSON.stringify({ question: 'a'.repeat(1001) }), 'null']) {
    const response = await POST(new Request('http://localhost/api/ask', { method: 'POST', body }));
    assert.equal(response.status, 400);
  }
});
