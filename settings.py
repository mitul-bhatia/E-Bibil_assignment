"""Paths and the few settings used by the whole app."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')

DOCUMENTS_DIR = ROOT / 'documents'
DATA_DIR = ROOT / 'data'
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
TARGET_TOKENS = 200
OVERLAP_TOKENS = 30
MAX_EMBEDDING_TOKENS = 254  # MiniLM's 256-token limit, minus two special tokens.
TOP_K = 4
UNKNOWN_ANSWER = "I don't know based on the provided documents."


def gemini_model():
    return os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')


def chunking_model():
    return os.getenv('CHUNKING_MODEL', gemini_model())
