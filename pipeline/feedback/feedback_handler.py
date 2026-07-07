"""
feedback/feedback_handler.py
─────────────────────────────────────────────────────────
وقتی Engineer feedback میده (ستاره، تصحیح، گزارش خطا)،
این ماژول اون رو توی PostgreSQL ذخیره میکنه.
─────────────────────────────────────────────────────────
"""

from datetime import datetime
from db.connection import get_postgres


def save_feedback(session_id: str,
                  user_id: str,
                  question: str,
                  answer: str,
                  rating: int,
                  chunk_ids: list,
                  correction: str = None,
                  feedback_type: str = "rating") -> int:
    """
    feedback رو ذخیره میکنه.

    rating: ۱ (بد) تا ۵ (عالی)
    feedback_type: rating / correction / wrong_product / outdated
    """
    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        INSERT INTO feedback
            (session_id, user_id, question, llm_answer,
             retrieved_chunk_ids, rating, correction,
             feedback_type, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        session_id, user_id, question, answer,
        chunk_ids, rating, correction,
        feedback_type, datetime.now()
    ))

    feedback_id = cur.fetchone()["id"]
    pg.commit()
    pg.close()
    return feedback_id