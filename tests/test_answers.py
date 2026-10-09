import pytest
from fastapi.testclient import TestClient

import api
from answers import validate_answer
from gemini import GeminiError
from settings import UNKNOWN_ANSWER

PASSAGES = [{
    'id': 'privacy-001', 'document': 'Privacy Policy', 'section': 'Retention',
    'source_url': 'https://example.com/privacy', 'text': 'Logs are kept for approximately 30 days.',
}]


def test_abstention_has_no_misleading_citations():
    result = validate_answer({'answerable': False, 'answer': 'unsupported guess', 'source_ids': ['made-up']}, PASSAGES)
    assert result == {'answer': UNKNOWN_ANSWER, 'answerable': False, 'sources': []}


@pytest.mark.parametrize('source_ids', [['not-retrieved'], [], [12]])
def test_unsupported_or_missing_citation_ids_are_rejected(source_ids):
    with pytest.raises(GeminiError):
        validate_answer({'answerable': True, 'answer': '30 days.', 'source_ids': source_ids}, PASSAGES)


def test_source_metadata_comes_from_retrieval_and_duplicates_are_removed():
    result = validate_answer({'answerable': True, 'answer': 'Approximately 30 days.', 'source_ids': ['privacy-001', 'privacy-001']}, PASSAGES)
    assert len(result['sources']) == 1
    assert result['sources'][0]['url'] == PASSAGES[0]['source_url']
    assert result['sources'][0]['excerpt'] == PASSAGES[0]['text']


def test_api_validation_and_provider_failure(monkeypatch):
    client = TestClient(api.app)
    assert client.get('/health').status_code == 200
    assert client.post('/ask', json={'question': ''}).status_code == 422
    def unavailable(question):
        raise GeminiError('Gemini free-tier quota was reached. Wait before trying again.')
    monkeypatch.setattr(api, 'answer_question', unavailable)
    response = client.post('/ask', json={'question': 'Retention?'})
    assert response.status_code == 503
    assert 'quota' in response.json()['detail']


def test_api_returns_grounded_result(monkeypatch):
    expected = validate_answer({'answerable': True, 'answer': 'Approximately 30 days.', 'source_ids': ['privacy-001']}, PASSAGES)
    monkeypatch.setattr(api, 'answer_question', lambda question: expected)
    assert TestClient(api.app).post('/ask', json={'question': 'Retention?'}).json() == expected
