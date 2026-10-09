"""Exercise UI rendering with explicit fixtures, not live model answers."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

import answers
from settings import UNKNOWN_ANSWER

APP_PATH = Path(__file__).resolve().parents[1] / 'app.py'


def test_answer_and_source_are_displayed(monkeypatch):
    monkeypatch.setattr(answers, 'answer_question', lambda question: {
        'answer': 'Approximately 30 days.', 'answerable': True,
        'sources': [{
            'document': 'Privacy Policy', 'section': 'How Long We Keep Information',
            'url': 'https://automattic.com/privacy/', 'excerpt': 'Logs are retained for approximately 30 days.',
        }],
    })
    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
    app.text_area[0].set_value('How long are logs kept?')
    app.button[0].click().run()
    assert not app.exception
    assert 'Approximately 30 days.' in [element.value for element in app.markdown]
    assert len(app.expander) == 1
    assert 'Privacy Policy' in app.markdown[-1].value


def test_unknown_answer_has_no_source_panel(monkeypatch):
    monkeypatch.setattr(answers, 'answer_question', lambda question: {
        'answer': UNKNOWN_ANSWER, 'answerable': False, 'sources': [],
    })
    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
    app.text_area[0].set_value('When will my refund arrive?')
    app.button[0].click().run()
    assert not app.exception
    assert UNKNOWN_ANSWER in [element.value for element in app.markdown]
    assert len(app.expander) == 0
