import { readFile, writeFile } from 'node:fs/promises';
import { ask } from '../lib/rag.js';

const questions = JSON.parse(await readFile('data/eval_questions.json', 'utf8'));
const report = { runAt: new Date().toISOString(), model: process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite',
  note: 'Answerability and section checks are automated. Review each actual answer against expected_answer; these checks are not an accuracy score.', results: [] };
for (const question of questions) {
  const row = { ...question, status: 'blocked', actual_answer: null, sources: [], review_verdict: 'pending' };
  try {
    const answer = await ask(question.question);
    Object.assign(row, { status: 'completed', actual_answer: answer.answer, sources: answer.sources,
      retrieved_ids: answer.retrieved.map(passage => passage.id),
      answerability_match: answer.answerable === question.answerable,
      citation_match: question.answerable ? answer.sources.some(source => source.document === question.expected_document && source.section.includes(question.expected_section)) : answer.sources.length === 0,
      elapsed_ms: answer.elapsedMs });
  } catch (error) { row.review_notes = error.message; }
  report.results.push(row);
  await writeFile('data/eval_results.json', JSON.stringify(report, null, 2) + '\n');
  console.log(`${row.id}: ${row.status}`);
  // Space failed calls too: immediately repeating quota failures makes the limit worse.
  if (question !== questions.at(-1)) await new Promise(resolve => setTimeout(resolve, 15000));
}
console.log('Saved actual results. Review factual correctness before setting review_verdict.');
