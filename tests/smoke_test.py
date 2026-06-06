# -*- coding: utf-8 -*-
"""Smoke test: imports + DB migration + state machine."""
import os
import sys
import json
import sqlite3
import tempfile
import shutil

# Add src/ to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

# Smoke 1: all modules import
import audio_player
import word_card_renderer
import dict_api
import database
import clipboard_monitor
import pet_window
import vocabulary_window
import learning_window
import review_window
import notification_window
import main
import words
print("OK: all 12 modules import cleanly")

# Smoke 2: DB migration on a fake old DB
tmp_dir = tempfile.mkdtemp()
db_path = os.path.join(tmp_dir, "test.db")

# Create an old DB WITHOUT the new columns
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("""CREATE TABLE notebooks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at DATETIME)""")
c.execute("""CREATE TABLE words(
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
    notes TEXT DEFAULT '')""")
c.execute("INSERT INTO notebooks(name, created_at) VALUES('test_nb', '2024-01-01 00:00:00')")
c.execute("INSERT INTO words(word, definition, example, notebook_id, created_at) VALUES('hello', '你好', 'Hello world', 1, '2024-01-01 00:00:00')")
c.execute("INSERT INTO words(word, notebook_id, created_at) VALUES('blankword', 1, '2024-01-01 00:00:00')")
conn.commit()
conn.close()

from database import Database
db = Database(db_path)

# Verify new columns
conn = sqlite3.connect(db_path)
c = conn.cursor()
cols = [col[1] for col in c.execute("PRAGMA table_info(words)").fetchall()]
print("OK: words columns after migration:", cols)
assert "meanings_json" in cols
assert "lookup_status" in cols
assert "audio_cache" in cols

# hello: should be 'success' + meanings_json synthesized
row = c.execute("SELECT meanings_json, lookup_status FROM words WHERE word=?", ("hello",)).fetchone()
print(f"OK: hello -> lookup_status={row[1]}, meanings_json={row[0][:60]}...")
assert row[1] == "success"
parsed = json.loads(row[0])
assert parsed[0]["definitions"][0]["definition"] == "你好"
assert parsed[0]["partOfSpeech"] == "?"

# blankword: should stay 'never' (no definition to synthesize)
row = c.execute("SELECT lookup_status FROM words WHERE word=?", ("blankword",)).fetchone()
print(f"OK: blankword -> lookup_status={row[0]}")
assert row[0] == "never"

# update_word_details new signature
db.update_word_details(
    "hello",
    {
        "phonetic": "/həˈloʊ/",
        "meanings": [{"partOfSpeech": "interjection",
                      "definitions": [{"definition": "你好", "example": "Hello!"}]}],
    },
    notebook_id=1,
    audio_bytes=b"\x00\x01\x02",
)
row = c.execute("SELECT meanings_json, lookup_status, audio_cache FROM words WHERE word=?", ("hello",)).fetchone()
print(f"OK: hello updated -> status={row[1]}, audio_len={len(row[2] or b'')}")
assert row[1] == "success"
assert row[2] == b"\x00\x01\x02"
assert len(json.loads(row[0])) == 1

# mark_lookup_failed / mark_lookup_pending
db.mark_lookup_failed("hello", 1)
row = c.execute("SELECT lookup_status FROM words WHERE word=?", ("hello",)).fetchone()
assert row[0] == "failed"
db.mark_lookup_pending("hello", 1)
row = c.execute("SELECT lookup_status FROM words WHERE word=?", ("hello",)).fetchone()
assert row[0] == "never"
print("OK: mark_lookup_pending/failed transitions")

# get_audio_cache / save_audio_cache
db.save_audio_cache("hello", 1, b"new audio")
got = db.get_audio_cache("hello", 1)
assert got == b"new audio"
print("OK: audio_cache read/write")

# save_audio_cache with empty bytes should be no-op
db.save_audio_cache("hello", 1, b"")
got = db.get_audio_cache("hello", 1)
assert got == b"new audio", "empty bytes should not overwrite"
print("OK: save_audio_cache(b'') is no-op")

# Second launch idempotency
db2 = Database(db_path)
cols2 = [col[1] for col in sqlite3.connect(db_path).execute("PRAGMA table_info(words)").fetchall()]
assert cols2 == cols
# Migration should not have changed anything for already-migrated rows
row = c.execute("SELECT meanings_json, lookup_status, audio_cache FROM words WHERE word=?", ("hello",)).fetchone()
assert row[1] == "never"  # mark_lookup_pending set this
assert row[2] == b"new audio"  # audio cache preserved
print("OK: second launch is idempotent")

# Cleanup
conn.close()
del db, db2
shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL SMOKE TESTS PASSED")
