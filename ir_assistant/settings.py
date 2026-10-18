import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# Load only the conventional project .env, never arbitrary credential files.
load_dotenv(ROOT / ".env")
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("LANGSMITH_TRACING", "false")
DATA = ROOT / "data"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
CHUNK_SIZE = 400
OVERLAP = 60
CANDIDATE_K = 20
FINAL_K = 5
CONTEXT_TOKENS = 2200
