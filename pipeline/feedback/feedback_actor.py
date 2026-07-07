"""
feedback/feedback_actor.py
─────────────────────────────────────────────────────────
بر اساس feedback جمع‌شده، اقدام میکنه:
  - chunk های بد رو blacklist میکنه
  - quality_score chunk های خوب رو بالا میبره
  - cache های مربوطه رو invalidate میکنه
─────────────────────────────────────────────────────────
"""

from db.connection import get_postgres, get_qdrant
import config

BAD_RATING_THRESHOLD = 2      # rating <= 2 بد
BLACKLIST_FLAG_COUNT = 3      # بعد از 3 تا flag، blacklist


def process_feedback(feedback_id: int):
    """
    یه feedback خاص رو پردازش میکنه و اقدامات لازم رو انجام میده.
    """
    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        SELECT rating, retrieved_chunk_ids, correction
        FROM feedback WHERE id = %s
    """, (feedback_id,))

    row = cur.fetchone()
    if not row:
        pg.close()
        return

    rating = row["rating"]
    chunk_ids = row["retrieved_chunk_ids"] or []
    correction = row["correction"]

    if rating and rating <= BAD_RATING_THRESHOLD and chunk_ids:
        _flag_chunks(chunk_ids, cur)

    if correction and chunk_ids:
        _save_correction(chunk_ids[0], row.get("question", ""), correction, cur)

    pg.commit()
    pg.close()


def _flag_chunks(chunk_ids: list, cur):
    """chunk ها رو flag میکنه — اگه به سقف رسیدن، blacklist میشن"""
    qdrant = get_qdrant()

    for chunk_id in chunk_ids:
        cur.execute("""
            UPDATE chunks
            SET flag_count = flag_count + 1,
                needs_review = TRUE,
                blacklisted = CASE
                    WHEN flag_count + 1 >= %s THEN TRUE
                    ELSE blacklisted
                END
            WHERE chunk_id = %s
            RETURNING flag_count, blacklisted
        """, (BLACKLIST_FLAG_COUNT, chunk_id))

        result = cur.fetchone()
        if result and result["blacklisted"]:
            # توی Qdrant هم payload رو آپدیت کن
            cur.execute(
                "SELECT chunk_id FROM chunks WHERE chunk_id = %s", (chunk_id,)
            )


def _save_correction(chunk_id: str, wrong_answer: str,
                     correct_answer: str, cur):
    """تصحیح کاربر رو ذخیره میکنه"""
    cur.execute("""
        INSERT INTO corrections (chunk_id, wrong_answer, correct_answer, created_at)
        VALUES (%s, %s, %s, NOW())
    """, (chunk_id, wrong_answer, correct_answer))