"""
config.py
─────────────────────────────────────────────────────────
تنظیمات مرکزی پروژه — همه ماژول‌ها از اینجا import می‌کنن.
─────────────────────────────────────────────────────────
"""

import os
from dotenv import load_dotenv

load_dotenv()

# LiteLLM
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_API_KEY  = os.getenv("LITELLM_API_KEY", "sk-dry-run-key")

# Models
MODEL_LLAMA     = os.getenv("MODEL_LLAMA", "llama3.2-3b")
MODEL_QWEN      = os.getenv("MODEL_QWEN", "qwen2.5-7b")
MODEL_DEEPSEEK  = os.getenv("MODEL_DEEPSEEK", "deepseek-r1-8b")
MODEL_EMBEDDING = os.getenv("MODEL_EMBEDDING", "bge-m3")

# مدل پیش‌فرض برای generation (بعداً برای benchmark سه‌تا رو عوض می‌کنیم)
DEFAULT_MODEL = MODEL_LLAMA

# Timeouts

LLM_TIMEOUT = 120

# Qdrant
QDRANT_COLLECTION = "rohill_documents"
VECTOR_SIZE = 1024

# Reranker (sentence-transformers, نه از طریق Ollama)
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# Chunking
MAX_SECTION_WORDS = 350
SUB_CHUNK_WORDS = 200
SUB_CHUNK_OVERLAP = 30

# مسیرها
from pathlib import Path
PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
DOCUMENTS_DIR = PROJECT_DIR / "data" / "documents"