# -*- coding: utf-8 -*-
import os
import sqlite3
import json
from datetime import datetime


class Database:
    # 默认词汇本名称
    DEFAULT_NOTEBOOK = "默认词汇本"

    def __init__(self, db_path):
        self.db_path = db_path
        # 自动建父目录, 避免 sqlite3.OperationalError
        # (测试或全新拉下来的项目里 data/ 不存在, main.py 之前手动建, 但测试不走 main)
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._ensure_db()

    # ── 启动迁移 (幂等) ──────────────────────────────────────────

    def _ensure_db(self):
        """确保表与新列存在, 并对旧数据做一次性回填。
        整个流程幂等: 第二次启动列已存在 + 没有 (lookup_status='never' AND definition!='') 的行, 全部 UPDATE 影响 0 行。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ── notebooks 表 ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notebooks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at DATETIME
            )
        """)

        # ── words 表 (基础结构, 新列走 ALTER 追加) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                phonetic TEXT,
                definition TEXT,
                example TEXT,
                mastery INTEGER DEFAULT 0,
                is_favorite BOOLEAN DEFAULT FALSE,
                notebook_id INTEGER DEFAULT 1,
                created_at DATETIME,
                last_reviewed DATETIME,
                next_review DATETIME,
                FOREIGN KEY (notebook_id) REFERENCES notebooks(id)
            )
        """)

        # ── 默认词汇本 ──
        cursor.execute("SELECT COUNT(*) FROM notebooks")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
                (self.DEFAULT_NOTEBOOK, now),
            )

        # ── 列迁移: notes (旧) ──
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        if "notes" not in columns:
            cursor.execute("ALTER TABLE words ADD COLUMN notes TEXT DEFAULT ''")

        # ── 列迁移: meanings_json (新) ──
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        if "meanings_json" not in columns:
            cursor.execute(
                "ALTER TABLE words ADD COLUMN meanings_json TEXT DEFAULT '[]'"
            )

        # ── 列迁移: lookup_status (新, 默认 'never') ──
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        if "lookup_status" not in columns:
            cursor.execute(
                "ALTER TABLE words ADD COLUMN lookup_status TEXT DEFAULT 'never'"
            )

        # ── 列迁移: audio_cache (新, 可空 BLOB) ──
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        if "audio_cache" not in columns:
            cursor.execute(
                "ALTER TABLE words ADD COLUMN audio_cache BLOB"
            )

        # ── 旧数据回填: 把 definition 非空的行合成到 meanings_json + 标 'success' ──
        # WHERE 条件确保幂等: lookup_status='never' (尚未迁移) AND definition 非空
        cursor.execute("""
            SELECT id, definition, example
            FROM words
            WHERE (meanings_json IS NULL OR meanings_json = '' OR meanings_json = '[]')
              AND (definition IS NOT NULL AND definition != '')
              AND lookup_status = 'never'
        """)
        rows = cursor.fetchall()
        for row_id, old_def, old_ex in rows:
            synthesized = [{
                "partOfSpeech": "?",
                "definitions": [{
                    "definition": old_def or "",
                    "example": old_ex or "",
                }],
            }]
            cursor.execute(
                "UPDATE words SET meanings_json = ?, lookup_status = 'success' WHERE id = ?",
                (json.dumps(synthesized, ensure_ascii=False), row_id),
            )

        conn.commit()
        conn.close()

        # ── 首次启动时导入 words.py 内置词汇本 (会写入 definition/phonetic/example) ──
        self._import_builtin_notebooks()

        # ── 内置导入后再跑一次回填, 把刚导入的单词也标 'success' ──
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, definition, example
            FROM words
            WHERE (meanings_json IS NULL OR meanings_json = '' OR meanings_json = '[]')
              AND (definition IS NOT NULL AND definition != '')
              AND lookup_status = 'never'
        """)
        rows = cursor.fetchall()
        for row_id, old_def, old_ex in rows:
            synthesized = [{
                "partOfSpeech": "?",
                "definitions": [{
                    "definition": old_def or "",
                    "example": old_ex or "",
                }],
            }]
            cursor.execute(
                "UPDATE words SET meanings_json = ?, lookup_status = 'success' WHERE id = ?",
                (json.dumps(synthesized, ensure_ascii=False), row_id),
            )
        conn.commit()
        conn.close()

    # ── 单词 CRUD ────────────────────────────────────────────────

    def add_word(self, word, notebook_id=1):
        """添加单词, 默认 lookup_status='never' (由列 DEFAULT 决定)。"""
        if self.get_one_word(word, notebook_id):
            return "exists"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            INSERT INTO words (word, notebook_id, created_at)
            VALUES (?, ?, ?)
            """,
            (word, notebook_id, now),
        )
        conn.commit()
        conn.close()
        return "success"

    def update_word_details(self, word, result, notebook_id=None, *, audio_bytes=None):
        """更新单词: 写 meanings_json + phonetic + lookup_status='success' + (可选) audio_cache。
        不再写 definition / example (列保留作废)。
        notebook_id: 传入则限定词汇本 (修既有的跨本误更新 bug)。
        audio_bytes: 非空时写入 audio_cache; 传 None 或空 bytes 则保持 audio_cache 不变 (COALESCE 语义)。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        meanings = result.get("meanings", []) or []
        meanings_json = json.dumps(meanings, ensure_ascii=False)
        phonetic = result.get("phonetic", "") or ""

        if notebook_id is not None:
            cursor.execute(
                """
                UPDATE words
                SET phonetic = ?,
                    meanings_json = ?,
                    lookup_status = 'success',
                    audio_cache = COALESCE(?, audio_cache)
                WHERE word = ? AND notebook_id = ?
                """,
                (phonetic, meanings_json, audio_bytes, word, notebook_id),
            )
        else:
            cursor.execute(
                """
                UPDATE words
                SET phonetic = ?,
                    meanings_json = ?,
                    lookup_status = 'success',
                    audio_cache = COALESCE(?, audio_cache)
                WHERE word = ?
                """,
                (phonetic, meanings_json, audio_bytes, word),
            )
        conn.commit()
        conn.close()

    def mark_lookup_pending(self, word, notebook_id):
        """重置为 'never' (= 即将查词 / retry 触发)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE words SET lookup_status = 'never' WHERE word = ? AND notebook_id = ?",
            (word, notebook_id),
        )
        conn.commit()
        conn.close()

    def mark_lookup_failed(self, word, notebook_id=None):
        """标 'failed' (查词失败 / 词典未收录)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "UPDATE words SET lookup_status = 'failed' WHERE word = ? AND notebook_id = ?",
                (word, notebook_id),
            )
        else:
            cursor.execute(
                "UPDATE words SET lookup_status = 'failed' WHERE word = ?",
                (word,),
            )
        conn.commit()
        conn.close()

    def get_audio_cache(self, word, notebook_id):
        """读取 audio_cache 字段。None 表示未缓存。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT audio_cache FROM words WHERE word = ? AND notebook_id = ?",
            (word, notebook_id),
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
        return None

    def save_audio_cache(self, word, notebook_id, audio_bytes):
        """单独写 audio_cache (不更新释义/状态)。空 bytes 不写。"""
        if not audio_bytes:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE words SET audio_cache = ? WHERE word = ? AND notebook_id = ?",
            (audio_bytes, word, notebook_id),
        )
        conn.commit()
        conn.close()

    def get_one_word(self, word, notebook_id=None):
        """查询单词 (可指定词汇本)。返回完整 tuple (含新列 meanings_json/lookup_status/audio_cache)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT * FROM words WHERE word = ? AND notebook_id = ?",
                (word, notebook_id),
            )
        else:
            cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        result = cursor.fetchone()
        conn.close()
        return result

    def get_all_word(self, notebook_id=None):
        """获取所有内容 (可指定词汇本)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT * FROM words WHERE notebook_id = ? ORDER BY created_at DESC",
                (notebook_id,),
            )
        else:
            cursor.execute("SELECT * FROM words ORDER BY created_at DESC")
        result = cursor.fetchall()
        conn.close()
        return result

    def update_word(self, word, mastery, now):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE words
            SET mastery = ?, last_reviewed = ?
            WHERE word = ?
            """,
            (mastery, now, word),
        )
        conn.commit()
        conn.close()

    def del_word(self, word, notebook_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "DELETE FROM words WHERE word = ? AND notebook_id = ?",
                (word, notebook_id),
            )
        else:
            cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        conn.commit()
        conn.close()

    def del_all(self, notebook_id=None):
        """删除单词 (可指定词汇本)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("DELETE FROM words WHERE notebook_id = ?", (notebook_id,))
        else:
            cursor.execute("DELETE FROM words")
        conn.commit()
        conn.close()

    # ── 学习 / 复习查询 ──────────────────────────────────────────

    def get_new_words(self, notebook_id=None):
        """获取未学习的单词 (mastery == 0), 按添加时间正序。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT * FROM words WHERE (mastery = 0 OR mastery IS NULL) AND notebook_id = ? ORDER BY created_at ASC",
                (notebook_id,),
            )
        else:
            cursor.execute(
                "SELECT * FROM words WHERE mastery = 0 OR mastery IS NULL ORDER BY created_at ASC"
            )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_review_words(self, notebook_id=None):
        """获取需要复习的单词 (0 < mastery < 5), 优先复习到期或久未复习的。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if notebook_id is not None:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE mastery > 0 AND mastery < 5 AND notebook_id = ?
                AND (next_review IS NULL OR next_review <= ?)
                ORDER BY next_review ASC, last_reviewed ASC
                """,
                (notebook_id, now),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE mastery > 0 AND mastery < 5
                AND (next_review IS NULL OR next_review <= ?)
                ORDER BY next_review ASC, last_reviewed ASC
                """,
                (now,),
            )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_flashcard_words(self, notebook_id):
        """B1 合并流: 一次性取 mastery 0..4 的所有词, 按 next_review ASC NULLS FIRST 排。
        mastery=5 (毕业) 不出现。mastery=0 的新词 next_review IS NULL, 自然排最前。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE mastery < 5 AND notebook_id = ?
                ORDER BY next_review ASC NULLS FIRST, created_at ASC
                """,
                (notebook_id,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM words
                WHERE mastery < 5
                ORDER BY next_review ASC NULLS FIRST, created_at ASC
                """
            )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_all_learned_words(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM words WHERE mastery > 0 ORDER BY last_reviewed ASC"
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def count_new_words(self, notebook_id=None):
        """统计未学习单词数。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE (mastery = 0 OR mastery IS NULL) AND notebook_id = ?",
                (notebook_id,),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE mastery = 0 OR mastery IS NULL"
            )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def count_review_words(self, notebook_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if notebook_id is not None:
            cursor.execute(
                """
                SELECT COUNT(*) FROM words
                WHERE mastery > 0 AND mastery < 5 AND notebook_id = ?
                AND (next_review IS NULL OR next_review <= ?)
                """,
                (notebook_id, now),
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) FROM words
                WHERE mastery > 0 AND mastery < 5
                AND (next_review IS NULL OR next_review <= ?)
                """,
                (now,),
            )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def count_mastered_words(self, notebook_id=None):
        """统计 mastery=5 (已完全掌握) 的单词数。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM words WHERE mastery = 5 AND notebook_id = ?",
                (notebook_id,),
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM words WHERE mastery = 5")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def mark_word_learned(self, word):
        """将单词标记为已学习 (mastery → 1)。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            UPDATE words SET mastery = 1, last_reviewed = ?, next_review = ?
            WHERE word = ? AND (mastery = 0 OR mastery IS NULL)
            """,
            (now, now, word),
        )
        conn.commit()
        conn.close()

    def increase_mastery(self, word, notebook_id=None):
        """复习通过: mastery +1 (上限 5), 更新下次复习时间。
        notebook_id: 传入则限定词汇本 (修跨本误更新, B1 review 窗口必须传)。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT mastery FROM words WHERE word = ? AND notebook_id = ?",
                (word, notebook_id),
            )
        else:
            cursor.execute("SELECT mastery FROM words WHERE word = ?", (word,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        current = row[0] or 0
        new_mastery = min(current + 1, 5)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        intervals = {1: 1, 2: 24, 3: 72, 4: 168, 5: 336}
        hours = intervals.get(new_mastery, 336)
        from datetime import timedelta
        next_review = (datetime.now() + timedelta(hours=hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if notebook_id is not None:
            cursor.execute(
                """
                UPDATE words SET mastery = ?, last_reviewed = ?, next_review = ?
                WHERE word = ? AND notebook_id = ?
                """,
                (new_mastery, now, next_review, word, notebook_id),
            )
        else:
            cursor.execute(
                """
                UPDATE words SET mastery = ?, last_reviewed = ?, next_review = ?
                WHERE word = ?
                """,
                (new_mastery, now, next_review, word),
            )
        conn.commit()
        conn.close()

    def mark_forgotten(self, word, notebook_id):
        """用户点'忘记': mastery 不变, next_review = now, last_reviewed = now。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE words SET next_review = ?, last_reviewed = ? "
            "WHERE word = ? AND notebook_id = ?",
            (now, now, word, notebook_id),
        )
        conn.commit()
        conn.close()

    def reset_all_mastery(self):
        """重置所有单词的 mastery 为 0。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE words SET mastery = 0, last_reviewed = NULL, next_review = NULL"
        )
        conn.commit()
        conn.close()

    # ── 词汇本管理 ──────────────────────────────────────────────

    def get_all_notebooks(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.id, n.name, n.created_at,
                   (SELECT COUNT(*) FROM words WHERE notebook_id = n.id) AS word_count
            FROM notebooks n
            ORDER BY n.id ASC
        """)
        result = cursor.fetchall()
        conn.close()
        return result

    def get_notebook_id(self, name: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notebooks WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def create_notebook(self, name: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notebooks WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return "exists"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO notebooks (name, created_at) VALUES (?, ?)", (name, now)
        )
        notebook_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return notebook_id

    def rename_notebook(self, notebook_id: int, new_name: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notebooks SET name = ? WHERE id = ?", (new_name, notebook_id)
        )
        conn.commit()
        conn.close()

    def delete_notebook(self, notebook_id: int):
        """删除词汇本及其所有单词 (默认词汇本不可删除)。"""
        if notebook_id == 1:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM words WHERE notebook_id = ?", (notebook_id,))
        cursor.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        conn.commit()
        conn.close()
        return True

    def count_words_in_notebook(self, notebook_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM words WHERE notebook_id = ?", (notebook_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _import_builtin_notebooks(self):
        """首次启动时把 words.py 中的内置词汇本导入数据库笔记本。
        注意: 此时新列 meanings_json/lookup_status/audio_cache 已存在, 列默认值为 '[]'/'never'/NULL。
        导入完成后, _ensure_db 末尾的回填会再次扫描, 把这些单词也合成到 meanings_json + 标 'success'。
        """
        try:
            from words import ALL_VOCABULARY_BOOKS
        except ImportError:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for book in ALL_VOCABULARY_BOOKS:
            book_name = book.get("name", "")
            if not book_name:
                continue

            cursor.execute("SELECT id FROM notebooks WHERE name = ?", (book_name,))
            row = cursor.fetchone()
            if row:
                continue  # 已导入, 跳过 (幂等)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
                (book_name, now),
            )
            nb_id = cursor.lastrowid

            for w in book.get("words", []):
                english = w.get("english", "")
                if not english:
                    continue
                cursor.execute(
                    "SELECT id FROM words WHERE word = ? AND notebook_id = ?",
                    (english, nb_id),
                )
                if cursor.fetchone():
                    continue
                cursor.execute(
                    """
                    INSERT INTO words (word, phonetic, definition, example, mastery, notebook_id, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        english,
                        w.get("pronunciation", ""),
                        w.get("chinese", ""),
                        w.get("example", ""),
                        nb_id,
                        now,
                    ),
                )

        conn.commit()
        conn.close()

    def update_word_notes(self, word, notes, notebook_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                """
                UPDATE words
                SET notes=?
                WHERE word=? AND notebook_id=?
                """,
                (notes, word, notebook_id),
            )
        else:
            cursor.execute(
                """
                UPDATE words
                SET notes=?
                WHERE word=?
                """,
                (notes, word),
            )
        conn.commit()
        conn.close()
