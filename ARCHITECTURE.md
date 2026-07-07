# Rohill RAG Pipeline — Final Architecture
## Dry Run on MacBook Air M4 / Production on Ubuntu Server

---

## 1. Infrastructure

### Docker Compose Services

| Service | Image | Port(s) | Profile | Memory |
|---|---|---|---|---|
| Qdrant | qdrant/qdrant:v1.9.7 | 6333, 6334 | core | 512M |
| PostgreSQL | postgres:16-alpine | 5432 | core | 256M |
| MinIO | minio/minio:latest | 9000, 9001 | core | 256M |
| LiteLLM | ghcr.io/berriai/litellm:main-stable | 4000 | core | 512M |
| Open WebUI | ghcr.io/open-webui/open-webui:main | 3000→8080 | core | 512M |
| Langfuse | langfuse/langfuse:2 | 3001→3000 | core | 512M |
| Embeddings | michaelf34/infinity:latest | 7997 | core | 4G |
| Tika | apache/tika:2.9.2-full | 9998 | ingest | 1G |
| Unstructured | unstructured-io/unstructured-api | 8000 | ingest | 2G |
| Prefect | prefecthq/prefect:3-latest | 4200 | ingest | 512M |
| Prometheus | prom/prometheus:latest | 9090 | monitor | 256M |
| Grafana | grafana/grafana:latest | 3002→3000 | monitor | 256M |

### Dry Run vs Production

| Component | Dry Run (Mac M4) | Production (Ubuntu) |
|---|---|---|
| LLM Serving | Ollama (native, Metal GPU) | vLLM (NVIDIA GPU) |
| Models | Llama 3.2 3B / Qwen2.5 7B / DeepSeek 8B | Llama 3.3 70B / Qwen2.5 72B / DeepSeek-V3 |
| Embedding | infinity-emb (Docker, CPU) | infinity-emb (Docker, GPU) |
| Everything else | Identical | Identical |

### Ollama Note
Ollama runs NATIVE on Mac (Metal GPU). NOT in Docker.
LiteLLM connects via: http://host.docker.internal:11434

---

## 2. Database Schema (PostgreSQL)

```sql
-- Core document storage
CREATE TABLE documents (
    doc_id          VARCHAR(255) PRIMARY KEY,
    filename        VARCHAR(500),
    product         VARCHAR(100),
    doc_type        VARCHAR(50),    -- manual/spec/release_note/guideline/draft_spec
    version         VARCHAR(20),
    is_latest       BOOLEAN DEFAULT TRUE,
    is_preliminary  BOOLEAN DEFAULT FALSE,
    access_level    VARCHAR(20) DEFAULT 'public',  -- public/restricted/confidential
    status          VARCHAR(20) DEFAULT 'active',  -- active/archived
    minio_key       VARCHAR(500),
    language        VARCHAR(10),
    upload_date     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunks (
    chunk_id        VARCHAR(255) PRIMARY KEY,
    doc_id          VARCHAR(255) REFERENCES documents(doc_id),
    chunk_index     INTEGER,
    page_number     INTEGER,
    page_hash       VARCHAR(32),
    content_type    VARCHAR(30),    -- semantic/procedural/table/figure
    section         VARCHAR(200),
    step_range_start INTEGER,
    step_range_end   INTEGER,
    total_steps      INTEGER,
    quality_score   FLOAT DEFAULT 1.0,
    blacklisted     BOOLEAN DEFAULT FALSE,
    flag_count      INTEGER DEFAULT 0,
    needs_review    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Document versioning
CREATE TABLE document_pages (
    id          SERIAL PRIMARY KEY,
    doc_id      VARCHAR(255),
    page_number INTEGER,
    page_hash   VARCHAR(32),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_updates (
    id              SERIAL PRIMARY KEY,
    old_doc_id      VARCHAR(255),
    new_doc_id      VARCHAR(255),
    product         VARCHAR(100),
    old_version     VARCHAR(20),
    new_version     VARCHAR(20),
    pages_changed   INTEGER,
    pages_added     INTEGER,
    pages_removed   INTEGER,
    updated_by      VARCHAR(255),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Feedback system
CREATE TABLE feedback (
    id                  SERIAL PRIMARY KEY,
    session_id          VARCHAR(255),
    message_id          VARCHAR(255),
    user_id             VARCHAR(255),
    question            TEXT,
    llm_answer          TEXT,
    top_chunk_id        VARCHAR(255),
    retrieved_chunk_ids VARCHAR(255)[],
    rating              INTEGER,        -- 1 or -1
    correction          TEXT,
    feedback_type       VARCHAR(50),    -- THUMBS_DOWN_SIMPLE/WRONG_ANSWER/HALLUCINATION/OUTDATED_INFO
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE corrections (
    id              SERIAL PRIMARY KEY,
    chunk_id        VARCHAR(255),
    wrong_answer    TEXT,
    correct_answer  TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Cache
CREATE TABLE query_cache (
    cache_key            VARCHAR(64) PRIMARY KEY,
    query                TEXT,
    response             TEXT,
    retrieved_chunk_ids  VARCHAR(255)[],
    hit_count            INTEGER DEFAULT 1,
    created_at           TIMESTAMP DEFAULT NOW(),
    last_hit_at          TIMESTAMP,
    expires_at           TIMESTAMP,
    is_valid             BOOLEAN DEFAULT TRUE,
    invalidated_at       TIMESTAMP,
    invalidation_reason  VARCHAR(100)
);

CREATE INDEX idx_cache_valid_expires ON query_cache (is_valid, expires_at);
CREATE INDEX idx_cache_chunks ON query_cache USING GIN (retrieved_chunk_ids);

-- Security
CREATE TABLE security_events (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(255),
    query       TEXT,
    event_type  VARCHAR(50),
    threat_type VARCHAR(50),
    confidence  FLOAT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Query logging (for cache and analytics)
CREATE TABLE query_logs (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(255),
    user_id     VARCHAR(255),
    user_role   VARCHAR(50),
    product     VARCHAR(100),
    query       TEXT,
    query_type  VARCHAR(30),
    cache_hit   BOOLEAN,
    latency_ms  INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 3. Qdrant Collections

### rohill_documents (main)
Stores both dense and sparse vectors for hybrid search.

**Dense vector**: 1024-dim from BGE-M3
**Sparse vector**: BM25 from Qdrant/bm25 via fastembed

**Payload (metadata)**:
```json
{
  "doc_id":           "doc_001",
  "chunk_id":         "chunk_041",
  "chunk_index":      41,
  "page_number":      23,
  "doc_type":         "manual",
  "content_type":     "procedural",
  "product":          "TRB-1900",
  "product_family":   "TRB-series",
  "version":          "3.0",
  "is_latest":        true,
  "is_preliminary":   false,
  "access_level":     "public",
  "language":         "en",
  "upload_date":      "2025-03-15",
  "supersedes":       "TRB-1800",
  "hw_revision":      "B",
  "region":           "EU",
  "error_category":   null,
  "section":          "antenna_installation",
  "step_range_start": 8,
  "step_range_end":   12,
  "total_steps":      40,
  "table_title":      null,
  "row_count":        null,
  "has_units":        false,
  "figure_caption":   null,
  "figure_number":    null,
  "quality_score":    1.0,
  "blacklisted":      false,
  "text":             "Step 8: Mount the antenna bracket..."
}
```

### query_cache_vectors
Semantic cache. Dense vectors only. 1024-dim BGE-M3.
Payload: `{"cache_key": "sha256_hash"}`

---

## 4. Pipeline Code Structure

```
pipeline/
│
├── main.py                    # FastAPI app, entry point
│
├── security/
│   ├── input_validator.py     # Pattern-based injection detection
│   ├── guard.py               # LLM-based threat classifier
│   ├── document_scanner.py    # Pre-indexing doc security scan
│   └── output_validator.py    # Post-generation response check
│
├── cache/
│   ├── exact_cache.py         # SHA256 hash lookup
│   ├── semantic_cache.py      # Vector similarity cache (threshold=0.97)
│   └── cache_invalidator.py   # Invalidate on doc update / chunk blacklist
│
├── query/
│   ├── query_analyzer.py      # Detect type: standard/procedural/
│   │                          #   specification/calculation/comparison/inference
│   │                          # Extract entities: product, version, hw_revision
│   │                          # Validate entities exist in documents
│   ├── query_rewriter.py      # Resolve pronouns using conversation history
│   └── query_expander.py      # Add English equivalents for non-English terms
│
├── language/
│   └── language_detector.py   # Detect query language (langdetect)
│
├── retrieval/
│   ├── embedder.py            # BGE-M3 via infinity-emb API (port 7997)
│   ├── retriever.py           # Hybrid search: dense + sparse + RRF
│   │                          # Parallel retrieval for multi-doc queries
│   │                          # Procedural retrieval (ordered by step)
│   │                          # Comparison retrieval (per-product)
│   │                          # Access level filter
│   │                          # Blacklist filter
│   │                          # Quality score weighting
│   ├── context_expander.py    # Expand low-confidence chunks with neighbors
│   └── reranker.py            # BGE Reranker v2-m3 via infinity-emb
│
├── generation/
│   ├── quality_assessor.py    # no_results / low_confidence / uncertain / confident
│   ├── answer_classifier.py   # EXPLICIT_NO / IMPLICIT_NO / EXPLICIT_YES / PARTIAL / NOT_FOUND
│   ├── inference_classifier.py # DIRECT_INFERENCE / TECHNICAL_INFERENCE / SPECULATION
│   ├── detector.py            # CLARIFICATION vs ANSWER
│   └── generator.py           # Build prompt + call LiteLLM
│
├── comparison/
│   ├── comparison_builder.py  # Build structured comparison prompt
│   └── comparison_validator.py # Detect missing data per product
│
├── tools/
│   ├── calculator.py          # Python code execution sandbox
│   └── validator.py           # Code safety check (forbidden patterns)
│
├── conversation/
│   └── conversation.py        # Conversation state management
│
├── prompts/
│   └── prompts.py             # All system prompts:
│                              #   BASE, PROCEDURAL, CALCULATION,
│                              #   COMPARISON, CLARIFICATION,
│                              #   INFERENCE_DIRECT, INFERENCE_TECHNICAL,
│                              #   LANGUAGE_INSTRUCTIONS, DRAFT_DISCLAIMER,
│                              #   SANDBOXED_WRAPPER
│
├── feedback/
│   ├── feedback_handler.py    # Receive webhook from Open WebUI
│   └── feedback_actor.py      # Act: flag / blacklist / alert / reindex
│
├── document_manager/
│   ├── diff_detector.py       # Page hash comparison for change detection
│   └── version_manager.py     # Blue-green swap + cleanup
│
├── access_control/
│   └── rbac.py                # JWT decode + role → allowed access levels
│
└── workflows/
    ├── ingest.py              # Initial document indexing flow
    ├── document_update.py     # Update existing document (blue-green)
    └── review.py              # Human review trigger for flagged chunks
```

---

## 5. Complete Query Flow

```
[1] User sends query via Open WebUI
    ↓
[2] Pipeline receives request
    Extract: user_id, user_role, session_id, query
    ↓
[3] SECURITY LAYER
    ├── input_validator.py  → pattern check
    ├── guard.py            → LLM threat classifier
    └── If blocked: return polite refusal, log to security_events
    ↓
[4] ACCESS CONTROL
    rbac.py: role → allowed_access_levels
    ↓
[5] LANGUAGE DETECTION
    language_detector.py → query_language
    ↓
[6] EMBEDDING
    embedder.py → query_vector (BGE-M3, port 7997)
    ↓
[7] CACHE CHECK
    ├── exact_cache.py → SHA256 lookup
    ├── semantic_cache.py → vector similarity (threshold=0.97)
    └── If hit: return cached response (10-25ms)
    ↓
[8] QUERY ANALYSIS
    ├── query_rewriter.py   → resolve pronouns from history
    ├── query_analyzer.py   → type + entities + validation
    └── query_expander.py   → add English technical terms
    ↓
[9] RETRIEVAL (strategy based on query_type)
    ├── standard:     hybrid search, top-5
    ├── procedural:   find section → ordered by step_range_start
    ├── specification: table-first retrieval
    ├── comparison:   parallel retrieval per product
    ├── calculation:  hybrid search, top-5
    └── All: apply access_level + blacklist filters
    ↓
[10] CONTEXT EXPANSION
     context_expander.py → add neighbor chunks if score < 0.70
     ↓
[11] RERANKING
     reranker.py → BGE Reranker v2-m3 → top-5 final
     ↓
[12] QUALITY ASSESSMENT
     quality_assessor.py → no_results / low_confidence / confident
     ↓
[13] ANSWER CLASSIFICATION (if confident)
     answer_classifier.py → EXPLICIT_NO / IMPLICIT_NO / PARTIAL / etc.
     ↓
[14] INFERENCE CLASSIFICATION (if not found directly)
     inference_classifier.py → DIRECT / TECHNICAL / SPECULATION
     ↓
[15] PROMPT BUILDING
     prompts.py → select system prompt based on:
       query_type + answer_type + inference_type +
       query_language + is_preliminary
     ↓
[16] GENERATION
     LiteLLM (port 4000) → Ollama / vLLM
     ↓
[17] OUTPUT VALIDATION
     output_validator.py → check for leaks, credential exposure
     ↓
[18] RESPONSE TYPE DETECTION
     detector.py → CLARIFICATION or ANSWER
     ↓
[19] SAVE TO CACHE (if ANSWER)
     exact_cache + semantic_cache
     ↓
[20] LOG TO LANGFUSE
     trace: question, chunks, answer, latency, model,
            answer_source (direct/inference/cached),
            query_type, inference_type
     ↓
[21] RETURN to Open WebUI
```

---

## 6. Complete Ingestion Flow

```
[1] New document uploaded to MinIO (raw-documents bucket)
    ↓
[2] Prefect workflow triggered (ingest.py)
    ↓
[3] SECURITY SCAN
    document_scanner.py → check for injection patterns
    If suspicious: quarantine + alert admin
    ↓
[4] METADATA AUTO-EXTRACTION
    LiteLLM call: extract product, version, doc_type,
                  supersedes, hw_revision from first 500 words
    ↓
[5] PARSER SELECTION
    .pdf             → Docling
    .doc/.docx/.txt  → Tika
    everything else  → Unstructured
    ↓
[6] PAGE HASHING
    MD5 hash per page → stored in document_pages table
    Used for diff detection on future updates
    ↓
[7] CHUNKING (content-type aware)
    table content:      → keep whole table as one chunk
    procedural content: → chunk by step ranges
    everything else:    → semantic chunking (BGE-M3 similarity)
    ↓
[8] METADATA ASSIGNMENT
    Per chunk: content_type, section, step_range,
               table_title, figure_caption, etc.
    ↓
[9] EMBEDDING
    Dense:  BGE-M3 via infinity-emb → 1024-dim vector
    Sparse: BM25 via fastembed → sparse vector
    ↓
[10] INDEXING
     Qdrant upsert: both vectors + full metadata payload
     PostgreSQL insert: document + chunks records
     ↓
[11] NOTIFY ENGINEERS
     Users who queried this product in last 7 days
```

---

## 7. Monitoring & Observability

### Langfuse (LLM Tracing)
Every LLM call logged with:
- question, chunks used, answer
- latency (retrieval / reranking / generation)
- token count (input / output)
- model used
- answer_source: direct / inference / cached
- query_type, inference_type
- user_feedback (when received)

### Prometheus Metrics
- qdrant_requests_total
- litellm_request_duration_seconds (p50, p95, p99)
- cache_hit_rate (exact + semantic)
- embedding_latency_seconds
- reranker_latency_seconds
- security_events_total (by type)
- chunk_quality_score_histogram

### Grafana Dashboards
1. **Pipeline Health**: latency breakdown, error rates, throughput
2. **Model Comparison**: per-model latency, RAGAS scores over time
3. **Cache Performance**: hit rates, invalidation frequency
4. **Document Health**: chunk quality scores, flagged chunks
5. **Security**: events by type, high-risk users

---

## 8. RAGAS Evaluation

### Test Set
50 Q&A pairs created from indexed documents.
Each pair: question + ground_truth answer.
Validated by Bert Strijker (SME).

### Metrics
| Metric | What it measures | Target |
|---|---|---|
| Faithfulness | No hallucination | > 0.85 |
| Answer Relevancy | Answers the question | > 0.80 |
| Context Precision | Retrieved chunks are relevant | > 0.75 |
| Context Recall | All needed info retrieved | > 0.80 |

### Benchmarking
Run RAGAS for each of the 3 models:
- Llama 3.2 3B (dry run) / Llama 3.3 70B (production)
- Qwen2.5 7B (dry run) / Qwen2.5 72B (production)
- DeepSeek-R1 8B (dry run) / DeepSeek-V3 (production)

---

## 9. Security Architecture

### Five Layers
1. **Input validation** — pattern matching (INJECTION_PATTERNS)
2. **LLM Guard** — small model classifies threat type + confidence
3. **Prompt sandboxing** — XML delimiters isolate user input
4. **Document scanning** — pre-indexing injection detection
5. **Output validation** — post-generation leak detection

### Access Control
User roles (from Open WebUI JWT):
- technician → access: public
- engineer → access: public, restricted
- senior_engineer → access: public, restricted, confidential

---

## 10. Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| RAG framework | None (custom Python) | Full control, no abstraction overhead |
| Vector DB | Qdrant | Production-grade, supports hybrid search natively |
| Embedding | BGE-M3 | Multilingual, best open-weight embedding model |
| Reranker | BGE Reranker v2-m3 | Pairs with BGE-M3, strong cross-encoder |
| Search strategy | Hybrid (dense + sparse + RRF) | Best of semantic + keyword |
| Chunking | Semantic + table-aware + procedural | Content-type appropriate |
| LLM gateway | LiteLLM | Abstracts vLLM/Ollama, enables A/B testing |
| Tracing | Langfuse (self-hosted) | Air-gapped compatible, LLM-specific |
| Scheduling | Prefect | Production-grade, visual workflow UI |
| Evaluation | RAGAS | Standard RAG evaluation framework |

