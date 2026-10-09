import { readFile, writeFile, rename } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { chunkDocument } from '../lib/chunk.js';
import { embed, EMBEDDING_MODEL, DIMENSIONS } from '../lib/gemini.js';

const manifest = JSON.parse(await readFile('data/sources.json', 'utf8'));
let cache = {};
try { cache = JSON.parse(await readFile('data/embedding-cache.json', 'utf8')); } catch {}
const chunks = [];
try {
  for (const source of manifest.documents) {
    const text = await readFile(source.file, 'utf8');
    if (createHash('sha256').update(text).digest('hex') !== source.sha256) {
      throw new Error(`${source.file} changed. Update its source manifest first.`);
    }
    for (const chunk of chunkDocument(text, source)) {
      const input = `title: ${chunk.document} | text: ${chunk.section}\n${chunk.text}`;
      const hash = createHash('sha256').update(EMBEDDING_MODEL + DIMENSIONS + input).digest('hex');
      if (!cache[hash]) {
        cache[hash] = await embed(input, true);
        await writeFile('data/embedding-cache.json', JSON.stringify(cache));
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      chunks.push({ ...chunk, vector: cache[hash] });
      console.log(`Prepared ${chunk.id}`);
    }
  }
  const index = { model: EMBEDDING_MODEL, dimensions: DIMENSIONS, preparedAt: new Date().toISOString(),
    documentHashes: manifest.documents.map(({ file, sha256 }) => ({ file, sha256 })), chunks };
  await writeFile('data/index.json.tmp', JSON.stringify(index));
  await rename('data/index.json.tmp', 'data/index.json');
  console.log(`Saved ${chunks.length} real embeddings to data/index.json.`);
} catch (error) {
  console.error(`Preparation stopped: ${error.message}\nExisting index was kept. Fix the issue and rerun; completed embeddings are cached.`);
  process.exitCode = 1;
}
