import sqlite3
from datetime import datetime


class Database:
    # 默认词汇本名称
    DEFAULT_NOTEBOOK = "默认词汇本"

    def __init__(self,db_path):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """确保表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ── 词汇本表 ──
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notebooks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at DATETIME
            )
        ''')

        # ── 单词表 ──
        cursor.execute('''
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
        ''')

        # ── 确保"默认词汇本"存在 ──
        cursor.execute("SELECT COUNT(*) FROM notebooks")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
                (self.DEFAULT_NOTEBOOK, now)
            )

        # ── 迁移：如果 words 表没有 notebook_id 列则添加 ──
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        if "notebook_id" not in columns:
            cursor.execute(
                "ALTER TABLE words ADD COLUMN notebook_id INTEGER DEFAULT 1"
            )

        conn.commit()
        conn.close()

        # ── 首次启动时导入内置词汇本到数据库 ──
        self._import_builtin_notebooks()

    def add_word(self, word, notebook_id=1):
        '''只添加到数据库，不查词典'''
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if self.get_one_word(word, notebook_id):
            conn.close()
            return "exists"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO words (word, notebook_id, created_at)
            VALUES (?, ?, ?)
        ''', (word, notebook_id, now))
        conn.commit()
        conn.close()
        return "success"

    def update_word_details(self, word, result):
        '''更新单词的音标、释义、例句'''
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE words 
            SET phonetic = ?, definition = ?, example = ?
            WHERE word = ?
        """, (result.get('phonetic', ''), result.get('definition', ''), result.get('example', ''), word))
        conn.commit()
        conn.close()

    def get_one_word(self, word, notebook_id=None):
        '''查询单词（可指定词汇本）'''
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("SELECT * FROM words WHERE word = ? AND notebook_id = ?", (word, notebook_id))
        else:
            cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_all_word(self, notebook_id=None):
        '''获取所有内容（可指定词汇本）'''
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("SELECT * FROM words WHERE notebook_id = ? ORDER BY created_at DESC", (notebook_id,))
        else:
            cursor.execute("SELECT * FROM words ORDER BY created_at DESC")
        result = cursor.fetchall()
        conn.close()
        return result
    
    def update_word(self,word,mastery,now):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE words
            SET mastery = ?, last_reviewed = ?
            WHERE word = ?
            """,(mastery, now, word))
        conn.commit()
        conn.close()
        
    def del_word(self, word, notebook_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("DELETE FROM words WHERE word = ? AND notebook_id = ?", (word, notebook_id))
        else:
            cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        conn.commit()
        conn.close()

    def del_all(self, notebook_id=None):
        """删除单词（可指定词汇本）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("DELETE FROM words WHERE notebook_id = ?", (notebook_id,))
        else:
            cursor.execute("DELETE FROM words")
        conn.commit()
        conn.close()

    # ── 学习 / 复习相关查询 ──────────────────────────────────────────

    def get_new_words(self, notebook_id=None):
        """获取未学习的单词 (mastery == 0)，按添加时间正序"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute(
                "SELECT * FROM words WHERE (mastery = 0 OR mastery IS NULL) AND notebook_id = ? ORDER BY created_at ASC",
                (notebook_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM words WHERE mastery = 0 OR mastery IS NULL ORDER BY created_at ASC"
            )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_review_words(self, notebook_id=None):
        """获取需要复习的单词 (0 < mastery < 5)，优先复习到期或久未复习的"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if notebook_id is not None:
            cursor.execute("""
                SELECT * FROM words
                WHERE mastery > 0 AND mastery < 5 AND notebook_id = ?
                AND (next_review IS NULL OR next_review <= ?)
                ORDER BY next_review ASC NULLS LAST, last_reviewed ASC
            """, (notebook_id, now))
        else:
            cursor.execute("""
                SELECT * FROM words
                WHERE mastery > 0 AND mastery < 5
                AND (next_review IS NULL OR next_review <= ?)
                ORDER BY next_review ASC NULLS LAST, last_reviewed ASC
            """, (now,))
        result = cursor.fetchall()
        conn.close()
        return result

    def get_all_learned_words(self):
        """获取所有已学习过的单词 (mastery > 0)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM words WHERE mastery > 0 ORDER BY last_reviewed ASC")
        result = cursor.fetchall()
        conn.close()
        return result

    def count_new_words(self, notebook_id=None):
        """统计未学习单词数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if notebook_id is not None:
            cursor.execute("SELECT COUNT(*) FROM words WHERE (mastery = 0 OR mastery IS NULL) AND notebook_id = ?", (notebook_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM words WHERE mastery = 0 OR mastery IS NULL")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def count_review_words(self, notebook_id=None):
        """统计待复习单词数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if notebook_id is not None:
            cursor.execute("""
                SELECT COUNT(*) FROM words
                WHERE mastery > 0 AND mastery < 5 AND notebook_id = ?
                AND (next_review IS NULL OR next_review <= ?)
            """, (notebook_id, now))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM words
                WHERE mastery > 0 AND mastery < 5
                AND (next_review IS NULL OR next_review <= ?)
            """, (now,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def mark_word_learned(self, word):
        """将单词标记为已学习 (mastery → 1)，立即可复习"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # next_review 设为当前时间，让单词立即可出现在复习队列
        cursor.execute("""
            UPDATE words SET mastery = 1, last_reviewed = ?, next_review = ?
            WHERE word = ? AND (mastery = 0 OR mastery IS NULL)
        """, (now, now, word))
        conn.commit()
        conn.close()

    def increase_mastery(self, word):
        """复习通过：mastery +1（上限 5），更新下次复习时间（间隔递增）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT mastery FROM words WHERE word = ?", (word,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        current = row[0] or 0
        new_mastery = min(current + 1, 5)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 间隔递增：1h → 1d → 3d → 7d → 14d
        intervals = {1: 1, 2: 24, 3: 72, 4: 168, 5: 336}  # hours
        hours = intervals.get(new_mastery, 336)
        from datetime import timedelta
        next_review = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE words SET mastery = ?, last_reviewed = ?, next_review = ?
            WHERE word = ?
        """, (new_mastery, now, next_review, word))
        conn.commit()
        conn.close()

    def reset_all_mastery(self):
        """重置所有单词的 mastery 为 0（清空复习本）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE words SET mastery = 0, last_reviewed = NULL, next_review = NULL")
        conn.commit()
        conn.close()

    # ── 词汇本管理 ────────────────────────────────────────────────────

    def get_all_notebooks(self):
        """获取所有词汇本，返回 [(id, name, created_at, word_count)]"""
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
        """按名称获取词汇本 ID，不存在则返回 None"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notebooks WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def create_notebook(self, name: str):
        """新建词汇本，返回 notebook_id；重名则返回 'exists'"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notebooks WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return "exists"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
            (name, now)
        )
        notebook_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return notebook_id

    def rename_notebook(self, notebook_id: int, new_name: str):
        """重命名词汇本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE notebooks SET name = ? WHERE id = ?", (new_name, notebook_id))
        conn.commit()
        conn.close()

    def delete_notebook(self, notebook_id: int):
        """删除词汇本及其所有单词（默认词汇本不可删除）"""
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
        """统计词汇本中的单词数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM words WHERE notebook_id = ?", (notebook_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _import_builtin_notebooks(self):
        """首次启动时把 words.py 中的内置词汇本导入数据库笔记本"""
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

            # 检查是否已导入（按名称查）
            cursor.execute("SELECT id FROM notebooks WHERE name = ?", (book_name,))
            row = cursor.fetchone()
            if row:
                # 词汇本已存在，跳过
                continue

            # 创建词汇本
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
                (book_name, now)
            )
            nb_id = cursor.lastrowid

            # 导入该词汇本的所有单词
            for w in book.get("words", []):
                english = w.get("english", "")
                if not english:
                    continue
                # 避免重复（同词汇本内）
                cursor.execute(
                    "SELECT id FROM words WHERE word = ? AND notebook_id = ?",
                    (english, nb_id)
                )
                if cursor.fetchone():
                    continue
                cursor.execute("""
                    INSERT INTO words (word, phonetic, definition, example, mastery, notebook_id, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                """, (
                    english,
                    w.get("pronunciation", ""),
                    w.get("chinese", ""),
                    w.get("example", ""),
                    nb_id,
                    now,
                ))

        conn.commit()
        conn.close()