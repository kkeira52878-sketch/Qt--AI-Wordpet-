# -*- coding: utf-8 -*-
"""
闪卡 B1 合并流验收 — 4 个用例覆盖 database 三个新方法 + renderer 新 mode。
"""
import os
import sqlite3
import pytest

from database import Database
from word_card_renderer import render_word_card


# ── 辅助: 手工造旧版 DB (无新列) ──


def _make_old_db(path: str, word_definitions):
    """word_definitions: [(word, definition_or_None, mastery), ...]"""
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
    for word, defn, mastery in word_definitions:
        conn.execute(
            "INSERT INTO words (word, definition, notebook_id, mastery, created_at) "
            "VALUES (?, ?, 1, ?, '2024-01-01 00:00:00')",
            (word, defn, mastery),
        )
    conn.commit()
    conn.close()


# ── 用例 1: mark_forgotten 保持 mastery 不变, 只写 next_review/last_reviewed ──


def test_mark_forgotten_keeps_mastery(tmp_path):
    """用户点'忘记': mastery 不变, next_review = now, last_reviewed = now。"""
    db_path = str(tmp_path / "forgot.db")
    _make_old_db(db_path, [
        ("a", "def a", 2),  # mastery=2
        ("b", "def b", 4),  # mastery=4
    ])
    db = Database(db_path)

    # 记录调用前的 mastery 和 next_review
    conn = sqlite3.connect(db_path)
    before = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT word, mastery, next_review FROM words WHERE notebook_id=1"
    ).fetchall()}
    conn.close()

    db.mark_forgotten("a", 1)
    db.mark_forgotten("b", 1)

    conn = sqlite3.connect(db_path)
    after = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT word, mastery, next_review FROM words WHERE notebook_id=1"
    ).fetchall()}
    conn.close()

    # mastery 必须保持不变
    assert after["a"][0] == 2, f"a 的 mastery 应保持 2, 实际 {after['a'][0]}"
    assert after["b"][0] == 4, f"b 的 mastery 应保持 4, 实际 {after['b'][0]}"
    # next_review 应被更新 (从 NULL 变为非空)
    assert after["a"][1] is not None, "a 的 next_review 应被写入"
    assert after["b"][1] is not None, "b 的 next_review 应被写入"


# ── 用例 2: get_flashcard_words 排除 mastery=5 (毕业) ──


def test_get_flashcard_words_excludes_mastery_5(tmp_path):
    """mastery=5 的词不出现在闪卡队列。"""
    db_path = str(tmp_path / "excluded.db")
    _make_old_db(db_path, [
        ("new",      "d0", 0),
        ("learning", "d1", 2),
        ("review",   "d2", 4),
        ("graduated","d3", 5),  # 应被排除
    ])
    db = Database(db_path)
    words = db.get_flashcard_words(1)
    word_names = [w[1] for w in words]
    assert "graduated" not in word_names, "mastery=5 的词不应出现"
    assert set(word_names) == {"new", "learning", "review"}, \
        f"应只返 3 个, 实际 {word_names}"


# ── 用例 3: get_flashcard_words NULLS FIRST (mastery=0 排最前) ──


def test_get_flashcard_words_nulls_first(tmp_path):
    """mastery=0 的词 next_review IS NULL, 应排最前 (NULLS FIRST)。"""
    db_path = str(tmp_path / "order.db")
    _make_old_db(db_path, [
        ("past_word",  "d1", 2),  # next_review will be set to past
        ("null_word",  "d0", 0),  # next_review IS NULL (默认)
        ("future_word","d2", 3),  # next_review will be set to future
    ])
    # 手动设置 next_review 模拟不同到期时间
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE words SET next_review='2020-01-01 00:00:00' WHERE word='past_word'")
    conn.execute("UPDATE words SET next_review='2099-01-01 00:00:00' WHERE word='future_word'")
    # null_word 保持 next_review NULL (mastery=0 默认就是 NULL)
    conn.commit()
    conn.close()
    db = Database(db_path)
    words = db.get_flashcard_words(1)
    order = [w[1] for w in words]
    # mastery=0 (NULLS FIRST) 应排第一位, 然后过去的, 然后未来的
    assert order[0] == "null_word", f"mastery=0 (NULL next_review) 应排最前, 实际 {order}"
    assert order == ["null_word", "past_word", "future_word"], \
        f"应为 [null, past, future], 实际 {order}"


# ── 用例 4: renderer mode='flashcard' 隐藏英文 ──


def test_renderer_flashcard_mode_hides_english(tmp_path):
    """mode='flashcard' 渲染时不显示 english 字段文本 (renderer 本身不输出 english 标签)。"""
    wd = {
        "english":       "ephemeral",  # 应被隐藏
        "pronunciation": "/ɪˈfemərəl/",
        "meanings": [
            {"partOfSpeech": "adjective", "definitions": [
                {"definition": "短暂的, 转瞬即逝的", "example": "Fame in this industry is fleeting."}
            ]}
        ],
        "memory":        "memorize tip",  # 应被隐藏 (renderer 不显 memory)
        "mastery":       0,
        "lookup_status": "success",
        "count_meanings": 1,
    }
    result = render_word_card(wd, mode='flashcard')
    # english 文本不应在 HTML 里出现 (renderer 不会输出 english 标签)
    assert "ephemeral" not in result.html, \
        f"flashcard 模式应隐藏英文, 但 html 包含: {result.html[:200]}"
    # phonetic 也不应被输出 (虽然 word_data 里有, 但 renderer 在 flashcard 模式下不显)
    assert "ˈfemərəl" not in result.html, \
        f"flashcard 模式应隐藏音标, 但 html 包含: {result.html[:200]}"
    # memory 也不应被输出
    assert "memorize tip" not in result.html
    # 但 meanings 仍应渲染
    assert "短暂的" in result.html, "释义应正常渲染"
    # show_fold_button / show_retry_button 都应 False
    assert result.show_fold_button is False
    assert result.show_retry_button is False
