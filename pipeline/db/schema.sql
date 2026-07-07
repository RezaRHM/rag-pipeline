-- ─────────────────────────────────────────────────────────
--  Rohill RAG Pipeline — Complete Database Schema
--  منبع: ARCHITECTURE.md بخش ۲
-- ─────────────────────────────────────────────────────────

-- Core document storage
CREATE TABLE IF NOT EXISTS documents (
    doc_id          VARCHAR(255) PRIMARY KEY,
    filename        VARCHAR(500),
    product         VARCHAR(100),
    doc_type        VARCHAR(50),
    version         VARCHAR(20),
    is_latest       BOOLEAN DEFAULT TRUE,
    is_preliminary  BOOLEAN DEFAULT FALSE,
    access_level    VARCHAR(20) DEFAULT 'public',
    status          VARCHAR(20) DEFAULT 'active',
    minio_key       VARCHAR(500),
    language        VARCHAR(10),
    upload_date     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id          VARCHAR(255) PRIMARY KEY,
    doc_id            VARCHAR(255) REFERENCES documents(doc_id),
    chunk_index       INTEGER,
    page_number       INTEGER,
    page_hash         VARCHAR(32),
    content_type      VARCHAR(30),
    section           VARCHAR(200),
    step_range_start  INTEGER,
    step_range_end    INTEGER,
    total_steps       INTEGER,
    quality_score     FLOAT DEFAULT 1.0,
    blacklisted       BOOLEAN DEFAULT FALSE,
    flag_count        INTEGER DEFAULT 0,
    needs_review      BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Document versioning
CREATE TABLE IF NOT EXISTS document_pages (
    id          SERIAL PRIMARY KEY,
    doc_id      VARCHAR(255),
    page_number INTEGER,
    page_hash   VARCHAR(32),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_updates (
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
CREATE TABLE IF NOT EXISTS feedback (
    id                  SERIAL PRIMARY KEY,
    session_id          VARCHAR(255),
    message_id          VARCHAR(255),
    user_id             VARCHAR(255),
    question            TEXT,
    llm_answer          TEXT,
    top_chunk_id        VARCHAR(255),
    retrieved_chunk_ids VARCHAR(255)[],
    rating              INTEGER,
    correction          TEXT,
    feedback_type       VARCHAR(50),
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS corrections (
    id              SERIAL PRIMARY KEY,
    chunk_id        VARCHAR(255),
    wrong_answer    TEXT,
    correct_answer  TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Cache
CREATE TABLE IF NOT EXISTS query_cache (
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

CREATE INDEX IF NOT EXISTS idx_cache_valid_expires ON query_cache (is_valid, expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_chunks ON query_cache USING GIN (retrieved_chunk_ids);

-- Security
CREATE TABLE IF NOT EXISTS security_events (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(255),
    query       TEXT,
    event_type  VARCHAR(50),
    threat_type VARCHAR(50),
    confidence  FLOAT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Query logging
CREATE TABLE IF NOT EXISTS query_logs (
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
