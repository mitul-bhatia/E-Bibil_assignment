"""Local embeddings and a small in-memory cosine search. No vector database."""
from functools import lru_cache
import json

import numpy as np

from documents import embedding_text, load_documents, token_count
from settings import DATA_DIR, EMBEDDING_MODEL, MAX_EMBEDDING_TOKENS, TOP_K


class SetupError(RuntimeError):
    """The saved dataset or embedding model needs preparation."""


def load_chunks():
    path = DATA_DIR / 'chunks.json'
    if not path.exists():
        raise SetupError('Run python prepare_chunks.py once, then restart the app.')
    prepared = json.loads(path.read_text())
    if prepared.get('method') != 'gemini_semantic_boundaries':
        raise SetupError('The app requires validated Gemini-generated chunks.')
    documents = {document['filename']: document for document in load_documents()}
    if {report['filename'] for report in prepared['documents']} != set(documents):
        raise SetupError('The dataset does not include all three source documents.')
    for report in prepared['documents']:
        if report['sha256'] != documents[report['filename']]['sha256']:
            raise SetupError('The documents changed. Prepare the chunks again.')
    chunks = prepared['chunks']
    if not chunks or len({chunk['id'] for chunk in chunks}) != len(chunks):
        raise SetupError('The chunk dataset is empty or has duplicate IDs.')
    for filename, document in documents.items():
        document_chunks = [chunk for chunk in chunks if chunk['filename'] == filename]
        next_start = 0
        for chunk in document_chunks:
            if chunk['core_start'] != next_start or not 0 <= chunk['start'] <= chunk['core_start'] < chunk['end'] <= len(document['text']):
                raise SetupError('Source ranges are missing, reordered or invalid.')
            if chunk['document'] != document['title'] or chunk['source_url'] != document['source_url']:
                raise SetupError('Saved citation metadata does not match the source manifest.')
            next_start = chunk['end']
        cores = ''.join(document['text'][chunk['core_start']:chunk['end']] for chunk in document_chunks)
        if cores != document['text']:
            raise SetupError('Chunks do not cover the original documents. Prepare them again.')
        for chunk in document_chunks:
            if chunk['text'] != document['text'][chunk['start']:chunk['end']]:
                raise SetupError('A saved chunk does not match the original source text.')
    return chunks


@lru_cache(maxsize=1)
def get_index():
    chunks = load_chunks()
    from sentence_transformers import SentenceTransformer
    try:
        model = SentenceTransformer(EMBEDDING_MODEL, device='cpu')
    except OSError:
        raise SetupError('Could not download the embedding model. Check your internet connection.') from None
    texts = [embedding_text(chunk['document'], chunk['section'], chunk['text']) for chunk in chunks]
    if any(token_count(text, model.tokenizer) > MAX_EMBEDDING_TOKENS for text in texts):
        raise SetupError('A chunk exceeds the embedding model limit. Prepare the chunks again.')
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return model, chunks, vectors


def retrieve(question, top_k=TOP_K):
    model, chunks, vectors = get_index()
    question_vector = model.encode(question, normalize_embeddings=True, show_progress_bar=False)
    scores = vectors @ question_vector  # Unit-vector dot product equals cosine similarity.
    indices = np.argsort(-scores, kind='stable')[:top_k]
    return [{**chunks[index], 'score': float(scores[index])} for index in indices]
