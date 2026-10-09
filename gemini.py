"""One small Gemini client shared by preprocessing and answers."""
import json
import os

from google import genai
from google.genai import errors, types
import httpx


class GeminiError(RuntimeError):
    """A readable failure message that never includes credentials."""


def generate_json(model, instructions, prompt, schema):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'replace_with_your_key':
        raise GeminiError('Set GEMINI_API_KEY in your local environment or Streamlit Secrets.')

    config = types.GenerateContentConfig(
        system_instruction=instructions,
        response_mime_type='application/json',
        response_json_schema=schema,
        temperature=0,
    )
    try:
        with genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120000)) as client:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
        if not response.text:
            raise GeminiError('Gemini returned no answer. Please try again.')
        return json.loads(response.text)
    except errors.APIError as error:
        messages = {
            400: 'Gemini rejected the request. Check your model setting and API key.',
            401: 'Gemini could not authenticate. Check your API key.',
            403: 'Gemini access was denied. Check the key permissions and region.',
            404: 'The configured Gemini model is unavailable. Update GEMINI_MODEL.',
            429: 'Gemini free-tier quota was reached. Wait before trying again.',
        }
        raise GeminiError(messages.get(error.code, 'Gemini is unavailable. Please try again later.')) from None
    except httpx.HTTPError:
        raise GeminiError('Could not connect to Gemini. Check your network connection.') from None
    except json.JSONDecodeError:
        raise GeminiError('Gemini returned invalid JSON. Please try again.') from None
