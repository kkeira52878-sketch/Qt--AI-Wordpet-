# -*- coding: utf-8 -*-
"""
复习窗口 — Anki 风格闪卡 (mode='flashcard'), 跟 learning 窗口同 UI。
B1 合并流: 调 db.get_flashcard_words()。
3a 加的"空状态 4 行统计"保留不动。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QTextEdit,
)
from PySide6.QtCore import Qt, QPoint, QTimer

from database import Database
from word_card_renderer import render_word_card, parse_meanings
from audio_player import play_audio_bytes, synthesize_audio_bytes

# 3b-2: 跨词本同步 — 顶部 import main 拿 notebook_bus (Q5=a 跟 learning 对称)
import main as _main


REVIEW_STYLE = """
    QWidget {
        background-color: #F0FDF4;
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

REVIEW_CARD_STYLE = """
    QWidget {
        background-color: #FFFFFF;
        border-radius: 16px;
        border: 2px solid #BBF7D0;
    }
"""


def _db_row_to_dict(row) -> dict:
    """DB tuple → word_data dict。"""
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


class ReviewWindow(QWidget):
    """复习窗口 — Anki 风格闪卡, 3a 4 行统计保留, 音频走 DB 缓存。"""

    def __init__(self):
        super().__init__()
        self.current_index = 0
        self.review_words = []
        self._current_notebook_id = None
        self._drag_position = QPoint()
        self._db = Database("data/wordpet.db")
        self._setup_ui()
        # 3b-2: 订阅跨词本同步总线 (Q5=a 跟 learning 对称)
        _main.notebook_bus.subscribe(self._on_notebook_changed_from_bus)

    def _setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("复习 - WordPet")
        self.setFixedSize(440, 500)
        self.setStyleSheet(REVIEW_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # 标题栏
        title_layout = QHBoxLayout()
        self.title_label = QLabel("🔄 复习 — 词汇库选好词本后, 点'复习'打开")
        self.title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #059669;"
        )
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            "background: transparent; color: #6B6B8A; font-size: 22px; padding: 0;"
        )
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        # 3b-2: 跨词本切换提示条 (默认隐藏, bus 触发时显示) — 跟 learning 对称
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
        card_widget.setStyleSheet(REVIEW_CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)
        card_widget.setLayout(card_layout)

        # ── 英文 (闪卡默认隐藏) ──
        self.english_label = QLabel("")
        self.english_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.english_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #059669;")
        self.english_label.setVisible(False)
        card_layout.addWidget(self.english_label)

        # ── 音标 (闪卡默认隐藏) ──
        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 15px; color: #0891B2;")
        self.phonetic_label.setVisible(False)
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
            "QTextEdit { background:#FFFFFF; border:2px solid #BBF7D0;"
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
        self._current_notebook_id = notebook_id
        rows = self._db.get_flashcard_words(notebook_id)
        self.review_words = [_db_row_to_dict(r) for r in rows]
        self.current_index = 0
        review_count = len(self.review_words)
        # 3a 保留: 标题动态展示词本名 + 数量
        if notebook_id:
            notebooks = self._db.get_all_notebooks()
            name = next((nb[1] for nb in notebooks if nb[0] == notebook_id), "")
            self.title_label.setText(f"🔄 复习 — {name}  ({review_count} 张待复习)")
        else:
            self.title_label.setText(f"🔄 复习 — 全部词本  ({review_count} 张待复习)")
        self.show_current_word()

    def show_current_word(self):
        if not self.review_words:
            # ── 3a 保留: 空状态 4 行统计 ──
            self.english_label.setText("📚 暂无待复习单词")
            self.english_label.setVisible(True)
            self.phonetic_label.setVisible(False)
            self.play_btn.setVisible(False)
            self.remember_btn.setVisible(False)
            self.forget_btn.setVisible(False)
            self.progress_label.setText("0 / 0")

            nb_id = self._current_notebook_id
            if nb_id:
                notebooks = self._db.get_all_notebooks()
                name = next((nb[1] for nb in notebooks if nb[0] == nb_id), "未知词本")
            else:
                name = "全部词本"
            n_total = len(self._db.get_all_word(nb_id))
            x_mastered = self._db.count_mastered_words(nb_id)
            z_new = self._db.count_new_words(nb_id)
            y_pending = max(0, n_total - x_mastered - z_new)

            stats_html = (
                '<div style="font-family:Microsoft YaHei,sans-serif;'
                'color:#1A1A2E; font-size:14px; line-height:1.8; padding:4px;">'
                f'<p style="margin:4px 0;">📚 词本 <b>{name}</b> 共 <b>{n_total}</b> 个单词</p>'
                f'<p style="margin:4px 0; color:#059669;">✅ 已掌握 <b>{x_mastered}</b> 个 (mastery=5)</p>'
                f'<p style="margin:4px 0; color:#7C3AED;">📖 待复习 <b>{y_pending}</b> 个 (0&lt;mastery&lt;5)</p>'
                f'<p style="margin:4px 0; color:#6B6B8A;">📒 未学 <b>{z_new}</b> 个 (mastery=0)</p>'
                '</div>'
            )
            self.meanings_edit.setHtml(stats_html)
            return

        if self.current_index < len(self.review_words):
            word = self.review_words[self.current_index]
            # ── 闪卡核心: 英文默认隐藏 ──
            self.english_label.setText(word.get("english", ""))
            self.english_label.setVisible(False)
            self.phonetic_label.setVisible(False)

            result = render_word_card(word, mode='flashcard')
            self.meanings_edit.setHtml(result.html)

            self.play_btn.setVisible(True)
            self.remember_btn.setVisible(True)
            self.forget_btn.setVisible(True)
            self.progress_label.setText(
                f"{self.current_index + 1} / {len(self.review_words)}"
            )
        else:
            self.english_label.setText("🎉 复习完成！")
            self.english_label.setVisible(True)
            self.phonetic_label.setVisible(False)
            self.meanings_edit.setHtml(
                '<p style="color:#059669; font-weight:bold;">'
                '恭喜你完成了本轮复习</p>'
            )
            self.play_btn.setVisible(False)
            self.remember_btn.setVisible(False)
            self.forget_btn.setVisible(False)
            self.progress_label.setText(
                f"{len(self.review_words)} / {len(self.review_words)}"
            )

    # ── 闪卡交互 ──

    def _on_remember(self):
        """✅ 记得: 必须传 notebook_id (review 跨本误更新修复) + 1s 临时显示英文 + 切下一张"""
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        word = self.review_words[self.current_index]
        word_text = word.get("english", "")
        nb_id = self._current_notebook_id or 1
        if word_text:
            # ★ review 窗口必须传 notebook_id, 不能像 learning 那样省略
            self._db.increase_mastery(word_text, notebook_id=nb_id)
        self._reveal_english(1000)
        self.current_index += 1
        self.show_current_word()

    def _on_forget(self):
        """❌ 忘记: mastery 不变, DB 标 mark_forgotten + in-memory 队尾追加 + 1.5s 临时显示英文"""
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        word = self.review_words[self.current_index]
        word_text = word.get("english", "")
        nb_id = self._current_notebook_id or 1
        if word_text:
            self._db.mark_forgotten(word_text, nb_id)
            # In-memory 立即追加: 本会话内重排
            self.review_words.append(word)
        self._reveal_english(1500)
        self.current_index += 1
        self.show_current_word()

    def _on_play_clicked(self):
        """🔊 播放: 1.5s 临时显示英文 + 播放音频"""
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        self._reveal_english(1500)
        self._play_current_audio()

    # ── 临时显示英文 (避免定时器引用错词) ──

    def _reveal_english(self, duration_ms):
        """临时显示英文 duration_ms 毫秒, 然后自动隐藏。
        闭包捕获 current_word 的值 (而非 index), 切下一张时定时器不会隐藏错词。
        """
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        current_word = self.review_words[self.current_index].get("english", "")
        if not current_word:
            return
        self.english_label.setText(current_word)
        self.english_label.setVisible(True)
        QTimer.singleShot(duration_ms, lambda w=current_word: self._hide_english_if_matches(w))

    def _hide_english_if_matches(self, word):
        """只有当前 english_label.text() == word 时才隐藏。"""
        if self.english_label.text() == word:
            self.english_label.setVisible(False)

    # ── 3b-2: 跨词本同步 (Q5=a, 跟 learning 对称) ──

    def _on_notebook_changed_from_bus(self, nb_id):
        """vocabulary 切词本时被调 (Q2 选 b + Q4 选 a) — 跟 learning 逻辑完全对称。"""
        if not self.isVisible():
            return
        if nb_id == self._current_notebook_id or self._current_notebook_id is None:
            return  # 同词本或未初始化, 不显提示

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
        self.current_index = 0
        self.load_from_database(self._current_notebook_id)

    # ── 音频 (走 audio_player + DB 缓存) ──

    def _play_current_audio(self):
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        self._play_audio(self.review_words[self.current_index].get("english", ""))

    def _play_audio(self, text: str):
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

    # ── 拖拽 ──

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
        self.load_from_database()
