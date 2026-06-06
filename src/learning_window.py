# -*- coding: utf-8 -*-
"""
学习窗口 — Anki 风格闪卡: 默认隐藏英文, 显释义+音标, "记得/忘记"二选一。
B1 合并流: 调 db.get_flashcard_words() (mastery 0..4, 排除已毕业 mastery=5)。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
)
from PySide6.QtCore import Qt, QPoint, QTimer

from database import Database
from word_card_renderer import render_word_card, parse_meanings
from audio_player import play_audio_bytes, synthesize_audio_bytes

# 3b-2: 跨词本同步 — 顶部 import main 拿 notebook_bus (运行时反向引用, 不构成循环导入)
import main as _main


# ── 样式 ──
LEARNING_STYLE = """
    QWidget {
        background-color: #F5F3FF;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        color: #1A1A2E;
    }
    QLabel {
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        color: #1A1A2E;
    }
    QPushButton {
        color: white;
        border: none;
        border-radius: 8px;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        padding: 10px 16px;
    }
"""

CARD_STYLE = """
    QWidget {
        background-color: #FFFFFF;
        border-radius: 16px;
        border: 2px solid #DDD6FE;
    }
"""


def _db_row_to_dict(row) -> dict:
    """DB tuple → word_data dict (含 meanings/lookup_status/count_meanings)。
    列顺序: id(0), word(1), phonetic(2), definition(3), example(4),
            mastery(5), is_favorite(6), notebook_id(7),
            created_at(8), last_reviewed(9), next_review(10),
            notes(11), meanings_json(12), lookup_status(13), audio_cache(14)
    """
    meanings = parse_meanings(row[12] if len(row) > 12 else None)
    return {
        "english":       row[1] or "",
        "pronunciation": row[2] or "",
        "memory":        "",
        "mastery":       row[5] or 0,
        "meanings":      meanings,
        "lookup_status": row[13] if len(row) > 13 else "never",
        "count_meanings": len(meanings),
        "_raw":          row,
    }


class LearningWindow(QWidget):
    """学习窗口 — Anki 风格闪卡 (mode='flashcard'), 音频走 DB 缓存。"""

    def __init__(self):
        super().__init__()
        self.current_words = []
        self.current_index = 0
        self.current_book_name = None
        self._current_notebook_id = None
        self._drag_position = QPoint()
        self._db = Database("data/wordpet.db")
        self._setup_ui()
        # 3b-2: 订阅跨词本同步总线
        _main.notebook_bus.subscribe(self._on_notebook_changed_from_bus)

    def _setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("学习 - WordPet")
        self.setFixedSize(440, 520)
        self.setStyleSheet(LEARNING_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # 标题栏
        title_layout = QHBoxLayout()
        self.book_label = QLabel("📖 学习 — 词汇库选好词本后, 点'学习新单词'打开")
        self.book_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #4A3FB5;")
        title_layout.addWidget(self.book_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            "background: transparent; color: #6B6B8A; font-size: 22px; padding: 0;"
        )
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        # 3b-2: 跨词本切换提示条 (默认隐藏, bus 触发时显示)
        warning_layout = QHBoxLayout()
        warning_layout.setSpacing(6)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet(
            "color: #B45309; font-size: 12px; background: #FEF3C7;"
            "padding: 4px 8px; border-radius: 4px;"
        )
        self.warning_label.setVisible(False)
        warning_layout.addWidget(self.warning_label, 1)
        self._reload_btn = QPushButton("🔄 重新加载")
        self._reload_btn.setFixedHeight(24)
        self._reload_btn.setStyleSheet(
            "background-color: #3B82F6; color: white; font-size: 12px;"
            "border-radius: 4px; padding: 2px 8px;"
        )
        self._reload_btn.setVisible(False)
        self._reload_btn.clicked.connect(self._on_reload_clicked)
        warning_layout.addWidget(self._reload_btn)
        main_layout.addLayout(warning_layout)

        # 单词卡片
        card_widget = QWidget()
        card_widget.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)
        card_widget.setLayout(card_layout)

        # ── 英文 (默认隐藏, 闪卡核心) ──
        self.english_label = QLabel("")
        self.english_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.english_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #4A3FB5;")
        self.english_label.setVisible(False)  # 闪卡默认隐藏
        card_layout.addWidget(self.english_label)

        # ── 音标 (flashcard 模式也隐藏, 算"提示") ──
        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 15px; color: #059669;")
        self.phonetic_label.setVisible(False)  # 闪卡默认隐藏
        card_layout.addWidget(self.phonetic_label)

        self.play_btn = QPushButton("🔊 播放发音")
        self.play_btn.setFixedWidth(140)
        self.play_btn.setStyleSheet(
            "background-color: #7C3AED; color: white;"
            "border-radius: 8px; padding: 8px 16px;"
        )
        self.play_btn.clicked.connect(self._on_play_clicked)
        card_layout.addWidget(self.play_btn, alignment=Qt.AlignCenter)

        # 释义 QTextEdit (走 WordCardRenderer mode='flashcard')
        self.meanings_edit = QTextEdit()
        self.meanings_edit.setReadOnly(True)
        self.meanings_edit.setMaximumHeight(220)
        self.meanings_edit.setMinimumHeight(100)
        self.meanings_edit.setStyleSheet(
            "QTextEdit { background:#FFFFFF; border:2px solid #DDD6FE;"
            "border-radius:10px; padding:10px; font-size:13px; }"
        )
        card_layout.addWidget(self.meanings_edit)

        main_layout.addWidget(card_widget)

        # 进度
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #6B6B8A; font-size: 13px;")
        main_layout.addWidget(self.progress_label)

        # 底部双按钮: ✅ 记得 (绿) + ❌ 忘记 (红)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.remember_btn = QPushButton("✅ 记得")
        self.remember_btn.setStyleSheet(
            "background-color: #059669; color: white;"
            "border-radius: 8px; padding: 12px 16px; font-size: 14px;"
        )
        self.remember_btn.clicked.connect(self._on_remember)
        buttons_layout.addWidget(self.remember_btn)

        self.forget_btn = QPushButton("❌ 忘记")
        self.forget_btn.setStyleSheet(
            "background-color: #DC2626; color: white;"
            "border-radius: 8px; padding: 12px 16px; font-size: 14px;"
        )
        self.forget_btn.clicked.connect(self._on_forget)
        buttons_layout.addWidget(self.forget_btn)

        main_layout.addLayout(buttons_layout)

    # ── 加载 ──

    def load_from_database(self, notebook_id=None):
        """B1 合并流: 调 get_flashcard_words 取 mastery 0..4, 排除已毕业 mastery=5。"""
        rows = self._db.get_flashcard_words(notebook_id)
        self._current_notebook_id = notebook_id

        if notebook_id:
            notebooks = self._db.get_all_notebooks()
            name = next((nb[1] for nb in notebooks if nb[0] == notebook_id), "未学单词")
            self.current_book_name = f"{name}"
        else:
            self.current_book_name = "全部词汇库"

        self.book_label.setText(f"📖 {self.current_book_name}")

        if not rows:
            self.current_words = []
            self.show_current_word()
            return

        self.current_words = [_db_row_to_dict(r) for r in rows]
        self.current_index = 0
        self.show_current_word()

    def show_current_word(self):
        if not self.current_words:
            self.english_label.setText("📚 没有可学习的单词")
            self.english_label.setVisible(True)  # 空状态消息要显示
            self.phonetic_label.setVisible(False)
            self.meanings_edit.setHtml(
                '<p style="color:#9CA3AF; font-style:italic;">'
                '去词汇库添加单词后再来学习吧</p>'
            )
            self.play_btn.setVisible(False)
            self.remember_btn.setVisible(False)
            self.forget_btn.setVisible(False)
            self.progress_label.setText("0 / 0")
            return

        if self.current_index < len(self.current_words):
            word = self.current_words[self.current_index]
            # ── 闪卡核心: 英文默认隐藏 ──
            self.english_label.setText(word.get("english", ""))
            self.english_label.setVisible(False)
            self.phonetic_label.setVisible(False)

            # mode='flashcard' 隐藏 english/phonetic/memory, 只显 meanings
            result = render_word_card(word, mode='flashcard')
            self.meanings_edit.setHtml(result.html)

            self.play_btn.setVisible(True)
            self.remember_btn.setVisible(True)
            self.forget_btn.setVisible(True)
            self.progress_label.setText(
                f"{self.current_index + 1} / {len(self.current_words)}"
            )
        else:
            # 全部答完 (含 B1 合并流下"忘记"的词也被重排过)
            self.english_label.setText("🎉 本轮学习完成！")
            self.english_label.setVisible(True)
            self.phonetic_label.setVisible(False)
            self.meanings_edit.setHtml(
                '<p style="color:#059669; font-weight:bold;">'
                '恭喜你完成了本轮闪卡</p>'
            )
            self.play_btn.setVisible(False)
            self.remember_btn.setVisible(False)
            self.forget_btn.setVisible(False)
            self.progress_label.setText(
                f"{len(self.current_words)} / {len(self.current_words)}"
            )

    # ── 闪卡交互 ──

    def _on_remember(self):
        """✅ 记得: mastery +1 (走 increase_mastery, 跨本限定由调用方传 notebook_id) + 1s 临时显示英文 + 切下一张"""
        if not self.current_words or self.current_index >= len(self.current_words):
            return
        word = self.current_words[self.current_index]
        word_text = word.get("english", "")
        if word_text:
            # B1 合并流: learning 窗口不限定词汇本 (跟旧 increase_mastery 行为兼容)
            self._db.increase_mastery(word_text)
        self._reveal_english(1000)
        self.current_index += 1
        self.show_current_word()

    def _on_forget(self):
        """❌ 忘记: mastery 不变, DB 标 mark_forgotten + in-memory 队尾追加 + 1.5s 临时显示英文 + 切下一张"""
        if not self.current_words or self.current_index >= len(self.current_words):
            return
        word = self.current_words[self.current_index]
        word_text = word.get("english", "")
        nb_id = self._current_notebook_id or 1
        if word_text:
            # DB 持久化: 标 mark_forgotten (next_review=now)
            self._db.mark_forgotten(word_text, nb_id)
            # In-memory 立即追加: 本会话内重排, 让用户立即能再看到
            self.current_words.append(word)
        self._reveal_english(1500)
        self.current_index += 1
        self.show_current_word()

    def _on_play_clicked(self):
        """🔊 播放按钮: 1.5s 临时显示英文 (用户主动"看答案") + 播放音频"""
        if not self.current_words or self.current_index >= len(self.current_words):
            return
        self._reveal_english(1500)
        self._play_current_audio()

    # ── 临时显示英文 (避免定时器引用错词) ──

    def _reveal_english(self, duration_ms):
        """临时显示英文 duration_ms 毫秒, 然后自动隐藏。
        闭包捕获 current_word 的值 (而非 index), 切下一张时定时器不会隐藏错词。
        """
        if not self.current_words or self.current_index >= len(self.current_words):
            return
        current_word = self.current_words[self.current_index].get("english", "")
        if not current_word:
            return
        self.english_label.setText(current_word)
        self.english_label.setVisible(True)
        QTimer.singleShot(duration_ms, lambda w=current_word: self._hide_english_if_matches(w))

    def _hide_english_if_matches(self, word):
        """只有当前 english_label.text() == word 时才隐藏, 避免与新卡片竞争。"""
        if self.english_label.text() == word:
            self.english_label.setVisible(False)

    # ── 3b-2: 跨词本同步 (bus.subscribe 回调 + 重新加载) ──

    def _on_notebook_changed_from_bus(self, nb_id):
        """vocabulary 切词本时被调 (Q2 选 b + Q4 选 a):
        - 弹窗可见 → 在标题下显示"⚠️ 词本已切换"提示条 + "🔄 重新加载"按钮
        - 弹窗不可见 → 不动 (用户主动点才打开)
        - nb_id == _current_notebook_id (同词本) → 不显 (避免重复提示)
        - 不调 load_from_database, 不改 current_index, 不重置 english_label
          (Q4 决策: 当前卡片 serendipity 继续看完, reload 不打断)
        """
        if not self.isVisible():
            return
        if nb_id == self._current_notebook_id or self._current_notebook_id is None:
            return  # 同词本或未初始化, 不显提示

        # 取新词本名用于提示条文案
        try:
            notebooks = self._db.get_all_notebooks()
            new_name = next((nb[1] for nb in notebooks if nb[0] == nb_id), f"#{nb_id}")
        except Exception:
            new_name = f"#{nb_id}"

        self.warning_label.setText(f"⚠️ 词本已切换为 [{new_name}], 点 [🔄 重新加载] 刷新")
        self.warning_label.setVisible(True)
        self._reload_btn.setVisible(True)

    def _on_reload_clicked(self):
        """用户点"🔄 重新加载": 强制 reload 当前词本, 隐藏提示条"""
        self.warning_label.setVisible(False)
        self._reload_btn.setVisible(False)
        # 重置到新词本第 0 张卡
        self.current_index = 0
        self.load_from_database(self._current_notebook_id)

    # ── 音频 (走 audio_player + DB 缓存) ──

    def _play_current_audio(self):
        if self.current_words and self.current_index < len(self.current_words):
            self._play_audio(self.current_words[self.current_index].get("english", ""))

    def _play_audio(self, text: str):
        """先查 DB 缓存, 命中走 MCI; 未命中 gTTS 实时 + 缓存。"""
        if not text:
            return
        nb_id = self._current_notebook_id or 1
        cached = self._db.get_audio_cache(text, nb_id)
        if cached:
            play_audio_bytes(cached, self)
            return
        audio = synthesize_audio_bytes(text)
        if audio:
            self._db.save_audio_cache(text, nb_id, audio)
            play_audio_bytes(audio, self)

    # ── 外部调用入口 (3a 后 UI 改用 vocabulary_window 注入 notebook_id) ──

    def _select_source(self, notebook_id, dialog):
        """外部调用入口, 3a 后 UI 改用 vocabulary_window 注入 notebook_id。"""
        dialog.accept()
        self.load_from_database(notebook_id)

    # ── 拖拽 / 生命周期 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if not self._drag_position.isNull():
                self.move(event.globalPosition().toPoint() - self._drag_position)
                event.accept()

    def showEvent(self, event):
        super().showEvent(event)
