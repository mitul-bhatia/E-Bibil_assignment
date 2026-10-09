# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
User requested a simple React interface and one repository deployed to Vercel. Next.js supplies React and one server-side API endpoint; no separate Python service.

## Users
An assessment reviewer who wants to try example questions, inspect the evidence, and understand the implementation.

## Product Purpose
A small assistant that answers questions using three public Automattic documents, cites the document and section, and admits when the documents lack an answer.

## Capabilities and Constraints
Generate embeddings once, save the vectors with original passages, and use top-k cosine similarity at runtime. Keep the source files, provenance, evaluation questions, and honest results. Keep credentials server-side. No accounts or document uploads are requested. Each chat turn is an independent question; disclose this next to the composer.

## Brand Commitments
User selected a dark chat interface. Keep the language plain and the implementation easy to explain.

## Evidence on Hand
Three original Markdown documents in documents/, their source manifest in data/sources.json, and ten evaluation questions in data/eval_questions.json. There are no indexed PDFs; citations must identify the actual Markdown sources.

## Product Principles
Working answers and evidence first. Show real evaluation results. Keep the code and dependencies small. Sample questions should be directly usable from the deployed app.
