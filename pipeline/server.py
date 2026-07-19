"""
server.py
─────────────────────────────────────────────────────────
FastAPI server که pipeline ما رو به صورت OpenAI-compatible
API expose میکنه — تا Open WebUI بتونه بهش وصل بشه.
─────────────────────────────────────────────────────────
"""

import time
import uuid
import json
import asyncio
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from main import ask
from query.query_rewriter import rewrite_query
from security.input_validator import validate_input
from security.guard import check_topic
from cache.exact_cache import get_cached_response, cache_response

LOG_FILE = Path(__file__).parent / "evaluation" / "test_results.csv"


def _log_result(question: str, answer: str, elapsed: float,
                query_type: str, cache_hit: bool):
    """هر سوال و جوابش رو با زمان توی CSV ذخیره میکنه"""
    file_exists = LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "question", "answer",
                             "elapsed_sec", "query_type", "cache_hit"])
        writer.writerow([
            time.strftime("%H:%M:%S"),
            question,
            answer[:200],
            round(elapsed, 1),
            query_type,
            cache_hit
        ])


app = FastAPI(title="Rohill RAG Pipeline API")

RADIO_KEYWORDS = [
    "repeater", "antenna", "duplexer", "dmr", "tetra", "alarm",
    "install", "power", "voltage", "led", "lcd", "channel",
    "rd98", "hr652", "hp7", "transmit", "receive", "frequency",
    "temperature", "grounding", "specification", "range", "error",
    "signal", "cable", "bracket", "screw", "pa module", "vswr",
    "fan", "battery", "ip rating", "outdoor", "indoor", "rack"
]


@app.on_event("startup")
async def startup_event():
    """مدل‌های سنگین رو موقع startup load میکنیم"""
    print("Pre-loading models at startup...")

    def preload():
        from retrieval.embedder import _get_sparse_model
        from retrieval.reranker import _get_reranker
        _get_sparse_model()
        _get_reranker()
        print("✓ Models pre-loaded and ready.")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, preload)


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "rohill-rag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "rohill"
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    if not messages:
        return JSONResponse({"error": "no messages"}, status_code=400)

    question = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        None
    )

    if not question:
        return JSONResponse({"error": "no user message"}, status_code=400)

    history = messages[:-1]

    # Input validation (بدون LLM — فوری)
    validation = validate_input(question)
    if not validation["valid"]:
        answer = f"Invalid input: {validation['reason']}"
        _log_result(question, answer, 0.0, "rejected_input", False)
        return _make_response(answer)

    # Topic guard — فقط اگه سوال به نظر بی‌ربط میاد
    question_lower = question.lower()
    is_likely_technical = any(kw in question_lower for kw in RADIO_KEYWORDS)

    if not is_likely_technical:
        topic = check_topic(question)
        if not topic["on_topic"]:
            answer = ("This question is outside the scope of the Rohill "
                      "technical documentation system.")
            _log_result(question, answer, 0.0, "rejected_topic", False)
            return _make_response(answer)

    def run_pipeline():
        import time as _time
        try:
            # کلید cache = سوالِ «حل‌شده»، نه متنِ خام. یک سوالِ ضمیردار
            # ("How do I install it?") در دو گفت‌وگوی مختلف دو معنی متفاوت
            # دارد؛ کلیدِ خام جوابِ محصولِ گفت‌وگوی قبلی را به گفت‌وگوی بعدی
            # نشت می‌داد. rewrite_query قطعی و بدون LLM است، پس این lookup
            # ارزان است و ask() داخل خودش به همان نتیجه می‌رسد.
            cache_question = rewrite_query(question, history)

            cached = get_cached_response(cache_question)
            if cached["hit"]:
                print(f"[CACHE HIT] {cache_question[:60]}")
                _log_result(question, cached["answer"], 0.0, "cached", True)
                return cached["answer"]

            # cache miss — pipeline رو اجرا کن
            t_start = _time.time()
            result = ask(question, conversation_history=history)
            answer = result["answer"]
            elapsed = _time.time() - t_start

            query_type = result.get("query_type", "unknown")
            product = result.get("detected_product", "none")
            print(f"[{elapsed:.1f}s] type={query_type} "
                  f"product={product} | Q: {question[:60]}")

            # لاگ کن
            _log_result(question, answer, elapsed, query_type, False)

            # cache کن
            chunk_ids = [
                c.payload.get("chunk_id", "")
                for c in result.get("chunks", [])
            ]
            cache_response(cache_question, answer, chunk_ids)

            return answer
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            _log_result(question, str(e), 0.0, "error", False)
            return f"Pipeline error: {str(e)}"

    async def generate():
        # اول یه chunk خالی بفرست
        keepalive = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "rohill-rag",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(keepalive)}\n\n"

        # pipeline رو توی thread pool اجرا کن
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            future = loop.run_in_executor(pool, run_pipeline)

            # هر ۵ ثانیه یه keepalive بفرست تا connection زنده بمونه
            while not future.done():
                await asyncio.sleep(5)
                if not future.done():
                    ping = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "rohill-rag",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": ""},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(ping)}\n\n"

            answer = await future

        # جواب اصلی
        chunk_data = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "rohill-rag",
            "choices": [{
                "index": 0,
                "delta": {"content": answer},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"

        done_data = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "rohill-rag",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(done_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def _make_response(content: str):
    async def generate():
        chunk_data = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "rohill-rag",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=False)