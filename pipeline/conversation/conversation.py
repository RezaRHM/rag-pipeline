"""
conversation/conversation.py
─────────────────────────────────────────────────────────
مدیریت state مکالمه — نگه‌داری تاریخچه سوال‌ها و جواب‌ها
برای هر session.

بدون این ماژول، هر سوال مستقله و rewriter نمیتونه
ضمایر رو درست resolve کنه.
─────────────────────────────────────────────────────────
"""

import uuid
from datetime import datetime
from db.connection import get_postgres


def create_session(user_id: str = None) -> str:
    """یه session جدید میسازه و session_id برمیگردونه"""
    session_id = str(uuid.uuid4())
    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO query_logs (session_id, user_id, query, created_at)
        VALUES (%s, %s, %s, %s)
    """, (session_id, user_id or "anonymous", "__session_created__", datetime.now()))
    pg.commit()
    pg.close()
    return session_id


class ConversationManager:
    """
    مدیریت state یه مکالمه — تاریخچه رو در حافظه نگه میداره
    و برای log کردن به PostgreSQL مینویسه.
    """

    def __init__(self, session_id: str = None, user_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or "anonymous"
        self.history = []  # لیست {"role": "user"/"assistant", "content": "..."}

    def add_turn(self, question: str, answer: str,
                 query_type: str = None, product: str = None,
                 latency_ms: int = None):
        """یه دور مکالمه (سوال + جواب) رو ثبت میکنه"""
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})

        # لاگ توی PostgreSQL
        pg = get_postgres()
        cur = pg.cursor()
        cur.execute("""
            INSERT INTO query_logs
                (session_id, user_id, product, query, query_type,
                 cache_hit, latency_ms, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            self.session_id, self.user_id, product, question,
            query_type, False, latency_ms, datetime.now()
        ))
        pg.commit()
        pg.close()

    def get_history(self) -> list:
        """تاریخچه مکالمه رو برمیگردونه"""
        return self.history.copy()

    def reset(self):
        """تاریخچه رو پاک میکنه (شروع مکالمه جدید)"""
        self.history = []