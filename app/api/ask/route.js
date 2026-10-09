import { ask } from '../../../lib/rag.js';

export const runtime = 'nodejs';
export const maxDuration = 150;

export async function POST(request) {
  let body;
  try { body = await request.json(); }
  catch { return Response.json({ error: 'Send a valid JSON question.' }, { status: 400 }); }
  if (typeof body?.question !== 'string' || !body.question.trim() || body.question.length > 1000) {
    return Response.json({ error: 'Enter a question between 1 and 1,000 characters.' }, { status: 400 });
  }
  try { return Response.json(await ask(body.question), { headers: { 'Cache-Control': 'no-store' } }); }
  catch (error) { return Response.json({ error: error.message }, { status: 503 }); }
}
