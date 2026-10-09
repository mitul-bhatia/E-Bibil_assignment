"""Record real answers and retrieval checks. A human reviews factual correctness."""
import argparse
from datetime import datetime, timezone
import json
import time

from answers import answer_question
from gemini import GeminiError
from retrieval import SetupError, retrieve
from settings import DATA_DIR, gemini_model


def matches_expected_source(sources, question):
    return any(
        source['document'] == question['expected_document']
        and question['expected_section'] in source['section']
        for source in sources
    )


def evaluate(output_path, pause_seconds):
    questions = json.loads((DATA_DIR / 'eval_questions.json').read_text())
    results = []
    for index, question in enumerate(questions):
        print(f"Running {question['id']}...", flush=True)
        row = {
            **question, 'status': 'pending', 'actual_answer': None, 'sources': [],
            'retrieval_hit': None, 'answerability_match': None,
            'citation_match': None, 'human_verdict': 'pending', 'review_notes': '',
        }
        try:
            retrieved = retrieve(question['question'])
            response = answer_question(question['question'])
            row.update({
                'status': 'completed', 'actual_answer': response['answer'], 'sources': response['sources'],
                'retrieved_ids': [chunk['id'] for chunk in retrieved],
                'retrieval_hit': matches_expected_source(retrieved, question) if question['answerable'] else None,
                'answerability_match': response['answerable'] == question['answerable'],
                'citation_match': matches_expected_source(response['sources'], question)
                    if question['answerable'] else not response['sources'],
            })
        except (GeminiError, SetupError, OSError) as error:
            row.update({'status': 'blocked', 'review_notes': str(error)})
        results.append(row)
        report = {
            'run_at': datetime.now(timezone.utc).isoformat(), 'model': gemini_model(),
            'results': results,
            'note': 'Source and answerability checks are automated. Factual correctness requires human review against expected_answer.',
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        print(f"  {row['status']}", flush=True)
        if row['status'] == 'blocked' and 'prepare_chunks.py' in row['review_notes']:
            # Missing data affects every question: record every row without wasting calls or waiting.
            pause_seconds = 0
        if pause_seconds and index < len(questions) - 1:
            time.sleep(pause_seconds)
    print(f'Saved results to {output_path}. Review each answer before marking human_verdict pass/fail.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=lambda value: DATA_DIR.parent / value, default=DATA_DIR / 'eval_results.json')
    parser.add_argument('--pause', type=float, default=10, help='Seconds between questions, to reduce free-tier rate-limit errors.')
    arguments = parser.parse_args()
    if not 0 <= arguments.pause <= 60:
        parser.error('--pause must be between 0 and 60 seconds.')
    evaluate(arguments.output, arguments.pause)
