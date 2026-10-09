# Client Knowledge Assistant

A small RAG app that answers questions using three public Automattic documents and shows the document, section and supporting passage. Gemini is used for one-time semantic chunking and for answers. Streamlit is the deployed UI; FastAPI exposes the same logic locally.

**Current status:** the code and offline checks are complete, but this checkout is **not submission-ready yet**. The development environment blocks both the Gemini API and Hugging Face downloads. No Gemini-generated chunks or live answers have been fabricated. Run the preparation and evaluation commands below from a network that can reach both services before deploying or submitting.

## Run locally

Use Python **3.12**, a Gemini API key on a free-tier project, and internet access to Google and Hugging Face. The CPU-only PyTorch dependency keeps the deployment smaller than a CUDA installation. The first model download and dependency installation can take several minutes.

```bash
git clone https://github.com/mitul-bhatia/E-Bibil_assignment.git
cd E-Bibil_assignment
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Keep the key out of Git. A key shared publicly or in a chat should be rotated before deployment. The model names are environment settings; defaults use `gemini-3.8-flash`. Google currently lists a free tier for this model, but model access and quotas depend on your project: [pricing](https://ai.google.dev/gemini-api/docs/pricing).

Prepare the dataset **once**:

```bash
python prepare_chunks.py
```

This writes `data/chunks.json`. It may make one corrective request per document if the first boundary proposal is invalid. Validated proposals are cached in the ignored `data/chunking-proposals/` directory so restarting preparation does not repeat successful requests. If preparation fails, it stops without substituting non-Gemini chunks or replacing an existing dataset. Delete that cache if you intentionally want Gemini to make new boundary choices.

```bash
streamlit run app.py
```

Open the displayed local URL. Example: **How long does a deleted WordPress.com post stay in Trash?**

For the optional local API, open another terminal with the same environment:

```bash
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/docs` and try `POST /ask` with:

```json
{"question": "Approximately how long are website visitor web server logs kept?"}
```

`GET /health` checks whether the API process is alive; it does not test Google access or dataset readiness.

## Architecture and code map

```text
Original Markdown → Gemini boundary choices → validated saved chunks

Streamlit ─┐
           ├→ local embeddings → cosine retrieval → Gemini → answer and sources
FastAPI ───┘
```

| File | Responsibility |
| --- | --- |
| `settings.py` | Paths, model names and chunk/retrieval settings |
| `documents.py` | Original text, Markdown headings, numbered source passages and validation |
| `prepare_chunks.py` | Give each complete document to Gemini and save source-preserving chunks |
| `retrieval.py` | Load chunks, embed them once and retrieve the four nearest chunks |
| `gemini.py` | Shared JSON API call and readable provider errors |
| `answers.py` | Grounded prompt and citation ID validation |
| `app.py` | Question box, answer, source links and expandable evidence |
| `api.py` | Thin local FastAPI wrapper |
| `evaluate.py` | Run the ten questions and record real results |

There is no vector database, agent framework, web search or conversation history. The chunking helper is a single-purpose LLM step, not a multi-agent system.

## Documents

I selected Automattic because its official public repository provides reusable Markdown documents, saving PDF extraction work and providing clear section citations. The organisation operates WordPress.com and other products; answers must preserve each policy's product scope.

The three original files are unchanged, from [Automattic/legalmattic revision `99aa482`](https://github.com/Automattic/legalmattic/tree/99aa482bf6b602645bcb50c47a68db48a76dbce0), downloaded October 9, 2026:

| Local file | Coverage |
| --- | --- |
| `documents/terms-of-service.md` | Account rules, payments, renewal, general refund conditions and termination |
| `documents/privacy-policy.md` | Data collection, retention, privacy rights and security |
| `documents/cookie-policy.md` | Cookie purposes and visitor controls |

`data/sources.json` records exact source URLs, repository revision and SHA-256 hashes. These documents are by **Automattic**, under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); their full licence is in `documents/LICENSE.txt`. Only the three Markdown documents are indexed. Links inside them, the licence and the source manifest are not additional knowledge sources.

## Chunking and retrieval choices

Gemini receives **each complete document**, with numbered source passages and section labels. It chooses the final semantic boundaries across that document. Paragraphs are numbered without alteration; oversized paragraphs are divided into smaller units, preferring sentence boundaries. This numbering makes Gemini's choices checkable rather than asking it to reproduce thousands of words accurately.

Gemini returns a list of ending passage IDs. Python assembles the original source slices and validates ordered, complete coverage, section boundaries and token size. Short sections can remain together. The target is **200 MiniLM tokens including title and section**, with up to **30 tokens of overlap** between consecutive chunks in the same section. Overlap is reduced if it would exceed MiniLM's 256-token input limit; two positions are reserved for special tokens. Core ranges reconstruct the entire original document, and every displayed excerpt must exactly match its source range.

The prepared file records the model, date, document hashes, boundary choices, attempt counts and per-chunk token counts. Saving it makes runtime reproducible even though a new LLM preparation run may choose different boundaries. There is no silent deterministic fallback: this version requires validated Gemini choices, as requested.

`all-MiniLM-L6-v2` produces local, normalized embeddings. Cosine similarity ranks chunks by meaning; the four highest-ranked passages become the answer context. Title and section are included in embedding text to preserve context. This is small enough for an in-memory array. A similarity score is **not** treated as proof that a question is answerable; the answer model must check whether the retrieved text supplies the requested facts.

The answer prompt forbids prior knowledge and following linked pages, preserves exceptions and product scope, and requests an explicit abstention when evidence is insufficient. Citation IDs must belong to the retrieved passages. Source titles, URLs and excerpts come from our saved metadata, not model-created URLs. These checks reject invalid references; they do not prove that every model claim is supported, so the evaluation also checks the cited text.

## Evaluation and actual results

The fixed set is `data/eval_questions.json`, with eight answerable questions and two unanswerable questions. Expected answers and expected sections were checked against the original files.

```bash
python evaluate.py
```

This saves actual answers, retrieved IDs, sources, retrieval hits, citation matches and answerability matches in `data/eval_results.json`. It pauses between questions to reduce quota errors; adjust with `--pause 20` if your project's limit is lower. Review each actual answer against `expected_answer`, then set `human_verdict` to `pass` or `fail` and explain misses in `review_notes`. Automated citation matches alone are not a factual-correctness score.

**Recorded development run:** 0/10 live answers completed. All ten are blocked because a genuine Gemini dataset could not be prepared here. No accuracy percentage is reported.

| ID | Question summary | Expected answer | Actual result |
| --- | --- | --- | --- |
| Q1 | Minimum age, including Europe | 13; 16 in Europe; guardian supervision below age of majority | Blocked — live run pending |
| Q2 | Cancellation deadline before renewal | One month for annual subscriptions; 24 hours for shorter periods | Blocked — live run pending |
| Q3 | Renewal after a promotional discount | Full price after the promotion ends | Blocked — live run pending |
| Q4 | Refund for a payment to an independent site owner | Contact that website owner | Blocked — live run pending |
| Q5 | Refund guarantee for every paid service | No; applicable policies and legal requirements are exceptions | Blocked — live run pending |
| Q6 | Visitor web server log retention | Approximately 30 days | Blocked — live run pending |
| Q7 | Deleted post: Trash and backups | 30 days in Trash; backups/caches may retain it until purged | Blocked — live run pending |
| Q8 | Disabling cookies | Possible through browser controls; some features may stop working correctly | Blocked — live run pending |
| Q9 | Exact arrival date of my pending refund | I don't know based on the provided documents | Blocked — live run pending |
| Q10 | Exact current Business plan price in INR | I don't know based on the provided documents | Blocked — live run pending |

For offline engineering checks:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

**Verified here: 20 offline tests passed; dependency checks passed.** These test source preservation, complete-document Gemini prompts, invalid boundaries, overlap, citation validation, API errors and UI rendering. Their tokenizer and answer fixtures are explicitly test doubles; they do **not** establish real retrieval quality or Gemini answer accuracy.

## Deploy on Streamlit Community Cloud

First run preparation and evaluation locally, inspect the results, and commit `data/chunks.json` plus the reviewed evaluation results to the public repository. `.env` and `.streamlit/secrets.toml` are ignored and must not be committed.

1. At [share.streamlit.io](https://share.streamlit.io/), create an app from the public repository, branch `main`, entrypoint `app.py`.
2. Select Python **3.12** in Advanced settings.
3. Add these top-level settings in **Secrets**, replacing only the key with your rotated key:

   ```toml
   GEMINI_API_KEY = "your-key"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```

4. Deploy. The embedding model downloads on the first start; later questions reuse the in-memory index. No document chunking runs on the hosted app.
5. Verify one answerable question and one unanswerable question at the deployed URL. If deployment fails, capture a 2–3 minute local demonstration instead, after the real evaluation runs.

Streamlit calls the shared Python RAG functions directly on Community Cloud. FastAPI remains a local demonstration interface. Hosting a separate public API is outside this prototype's scope. See Streamlit's [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) instructions.

## Limits and next steps

- Complete genuine preprocessing, evaluation and the hosted demo; these remain blocked in the current development environment.
- Semantic chunking does not guarantee optimal retrieval, and local MiniLM can miss paraphrases or evidence spread across more than four chunks. Inspect misses before changing retrieval settings.
- The policies are a fixed snapshot, not a live source of current prices or account-specific information. Updating documents requires updating their manifest and regenerating chunks.
- Gemini can still make unsupported claims despite the prompt and valid citation IDs. Add claim-level verification only if the evaluation shows it is necessary.
- Free-tier limits, cold starts and external model downloads affect availability. Errors are shown separately from document-based abstention. This public demo has no authentication or per-user quota controls.

## AI tools and time spent

OpenAI Codex assisted with document research, implementation, tests and this README. Gemini is the implemented tool for one-time boundary selection and runtime answers; **no successful Gemini request has been made from this development environment**, so it is not described as having already produced the dataset.

Work began around **16:16 IST on October 9, 2026**, including document research and design discussion. At **17:04 IST**, elapsed time was approximately **48 minutes**: 31 minutes for research/discussion and 17 minutes for implementation/validation. These are elapsed development-session estimates, not a claim about the applicant’s independent time. The four-hour budget includes research, preprocessing, evaluation and deployment; record any remaining work and stop by **20:16 IST** if using this start time. The submission deadline should be confirmed from the original email rather than inferred from the PDF's date.
