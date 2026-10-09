"""Optional local FastAPI interface to the same functions as Streamlit."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from answers import answer_question
from gemini import GeminiError
from retrieval import SetupError

app = FastAPI(title='Client Knowledge Assistant')


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.get('/health')
def health():
    return {'status': 'ok'}  # Process health, not a claim that Gemini is available.


@app.post('/ask')
def ask(body: Question):
    try:
        return answer_question(body.question)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except (GeminiError, SetupError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
