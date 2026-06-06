# -*- coding: utf-8 -*-
"""
数据库迁移验收 — 3 个 fixture 覆盖 0 / 全有定义 / 混合 三种旧 DB 形态 + 1 个幂等性验证。
所有 fixture 数据走 notebook_id=1, 与 _import_builtin_notebooks 自动导入的 notebook_id=2/3 隔离,
保证 expected_total 断言不被 words.py 干扰。
"""
import os
import sqlite3
import pytest

from database import Database


# ── 辅助: 手工造"旧版本"数据库 (无新列) ──


def _make_old_db(path: str, word_definitions):
    """手工造一个'旧版本'数据库, words 表没有 meanings_json/lookup_status/audio_cache。
    word_definitions: [(word, definition_or_None), ...] — definition=None 模拟用户从未查过。
    所有 fixture 数据固定写入 notebook_id=1, 与 _import_builtin_notebooks 的 notebook_id=2/3 隔离。
    """
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE notebooks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at DATETIME
        )
    """)
    conn.execute("""
        CREATE TABLE words(
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
            next_review DATETIME
        )
    """)
    for word, defn in word_definitions:
        conn.execute(
            "INSERT INTO words (word, definition, notebook_id) VALUES (?, ?, 1)",
            (word, defn),
        )
    conn.commit()
    conn.close()


# ── 辅助: 4 个验收点 (a)(b)(c)(d) 的断言 ──


def _assert_migrated(path: str, expected_total: int) -> None:
    """验证 (a) 3 列自动添加 (b) definition 非空 → success + meanings_json 回填
                (c) definition=NULL → never (d) 单词总数不变 (notebook_id=1 隔离)。
    """
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute('PRAGMA table_info(words)').fetchall()]
    assert 'meanings_json' in cols, "列 meanings_json 应自动创建"
    assert 'lookup_status' in cols, "列 lookup_status 应自动创建"
    assert 'audio_cache' in cols, "列 audio_cache 应自动创建"

    # (d) 单词总数不变 (notebook_id=1 隔离, 不被 words.py 导入干扰)
    total = conn.execute(
        'SELECT COUNT(*) FROM words WHERE notebook_id = 1'
    ).fetchone()[0]
    assert total == expected_total, f"notebook_id=1 单词数应不变 ({expected_total}), 实际 {total}"

    # (b)(c) definition 非空 → success + meanings_json 非空; definition=NULL → never
    rows = conn.execute(
        'SELECT word, definition, lookup_status, meanings_json '
        'FROM words WHERE notebook_id = 1'
    ).fetchall()
    for word, defn, status, mjson in rows:
        if defn:
            assert status == 'success', f"'{word}' 有 definition 应标 success, 实际 {status}"
            assert mjson and mjson != '[]', f"'{word}' 有 definition 应回填 meanings_json, 实际 {mjson!r}"
            assert defn in mjson, f"'{word}' 旧 definition 应出现在新 meanings_json 中"
        else:
            assert status == 'never', f"'{word}' definition=NULL 应保持 never, 实际 {status}"
    conn.close()


# ── Fixture 1: 0 词空表 (新建 DB, 不应该崩) ──


def test_migration_empty_db(tmp_path):
    """空 DB 启动: 3 列自动加, notebook_id=1 仍为 0 词, notebook_id=2/3 由 words.py 自动导入."""
    db_path = str(tmp_path / "empty.db")
    Database(db_path)  # 触发迁移
    _assert_migrated(db_path, expected_total=0)


# ── Fixture 2: 50 词全有 definition (典型旧版数据) ──


def test_migration_50_words_all_defined(tmp_path):
    db_path = str(tmp_path / "legacy_full.db")
    words = [(f"word_{i}", f"definition of word {i}") for i in range(50)]
    _make_old_db(db_path, words)
    Database(db_path)
    _assert_migrated(db_path, expected_total=50)


# ── Fixture 3: 50 词混合 (30 有 definition, 20 NULL — 模拟用户查词失败的旧词) ──


def test_migration_50_words_mixed(tmp_path):
    db_path = str(tmp_path / "legacy_mixed.db")
    words = (
        [(f"defined_{i}", f"definition {i}") for i in range(30)]
        + [(f"undefined_{i}", None) for i in range(20)]
    )
    _make_old_db(db_path, words)
    Database(db_path)
    _assert_migrated(db_path, expected_total=50)


# ── Fixture 4: 幂等性 — 第二次启动后整库数据应完全一致 ──


def test_migration_is_idempotent(tmp_path):
    """第二次启动不应改变任何数据 (notebook_id=1 隔离, 整 notebook 数据 dump 应当一致)."""
    db_path = str(tmp_path / "idempotent.db")
    words = [(f"w_{i}", f"def {i}") for i in range(10)]
    _make_old_db(db_path, words)

    Database(db_path)  # 第一次
    conn1 = sqlite3.connect(db_path)
    dump1 = "\n".join(
        str(r) for r in conn1.execute(
            'SELECT word, definition, meanings_json, lookup_status '
            'FROM words WHERE notebook_id = 1 ORDER BY id'
        ).fetchall()
    )
    conn1.close()

    Database(db_path)  # 第二次
    conn2 = sqlite3.connect(db_path)
    dump2 = "\n".join(
        str(r) for r in conn2.execute(
            'SELECT word, definition, meanings_json, lookup_status '
            'FROM words WHERE notebook_id = 1 ORDER BY id'
        ).fetchall()
    )
    conn2.close()

    assert dump1 == dump2, "第二次启动后 notebook_id=1 数据应与第一次完全一致 (幂等迁移)"


# ── 短修 3a: count_mastered_words 方法验证 ──


def test_count_mastered_words(tmp_path):
    """count_mastered_words: 仅统计 mastery=5, notebook_id 可选且不存在的本返回 0。"""
    db_path = str(tmp_path / "mastered.db")
    _make_old_db(db_path, [("a", "def a"), ("b", None)])
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE words SET mastery=5 WHERE word='a'")
    conn.commit()
    conn.close()
    db = Database(db_path)
    assert db.count_mastered_words(1) == 1, "notebook_id=1 应有 1 个 mastery=5"
    assert db.count_mastered_words() == 1, "notebook_id=None 应跨本统计 (1 个)"
    assert db.count_mastered_words(999) == 0, "不存在的 notebook_id 应返回 0"
