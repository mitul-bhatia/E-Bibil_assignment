import { readFile } from 'node:fs/promises';
import { embed, generateAnswer, EMBEDDING_MODEL, DIMENSIONS } from './gemini.js';

export const UNKNOWN = "I don't know based on the provided documents.";
export const TOP_K = 4;

export async function loadIndex() {
  let index;
  try { index = JSON.parse(await readFile(`${process.cwd()}/data/index.json`, 'utf8')); }
  catch { throw new Error('The document index could not be read. Run npm run prepare:index.'); }
  if (!index.chunks.length) throw new Error('The document index is not prepared yet. Run npm run prepare:index.');
  if (index.model !== EMBEDDING_MODEL || index.dimensions !== DIMENSIONS) {
    throw new Error('The embedding settings changed. Prepare the document index again.');
  }
  return index;
}

export function search(chunks, queryVector, topK = TOP_K) {
  // Both document and question vectors are normalized: dot product = cosine similarity.
  return chunks.map(({ vector, ...passage }) => ({
    ...passage, score: vector.reduce((sum, value, i) => sum + value * queryVector[i], 0),
  })).sort((a, b) => b.score - a.score).slice(0, topK);
}

export function resolveAnswer(result, passages) {
  if (typeof result?.answerable !== 'boolean') throw new Error('Google returned an invalid answer. Please try again.');
  if (!result.answerable) return { answer: UNKNOWN, answerable: false, sources: [] };
  const available = new Map(passages.map(passage => [passage.id, passage]));
  if (typeof result.answer !== 'string' || !result.answer.trim() ||
      !Array.isArray(result.source_ids) || !result.source_ids.length ||
      result.source_ids.some(id => !available.has(id))) {
    throw new Error('The answer has invalid supporting sources. Please try again.');
  }
  return {
    answer: result.answer.trim(), answerable: true,
    sources: [...new Set(result.source_ids)].map(id => available.get(id)),
  };
}

export async function ask(question) {
  if (typeof question !== 'string' || !question.trim() || question.length > 1000) {
    throw new Error('Enter a question between 1 and 1,000 characters.');
  }
  const started = Date.now();
  const index = await loadIndex();
  const queryVector = await embed(question.trim());
  const passages = search(index.chunks, queryVector);
  const result = await generateAnswer(question.trim(), passages.map(({ score, url, filename, ...evidence }) => evidence));
  return { ...resolveAnswer(result, passages), retrieved: passages, elapsedMs: Date.now() - started };
}
