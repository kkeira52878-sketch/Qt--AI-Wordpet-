# -*- coding: utf-8 -*-
"""
复习窗口 - 基于词汇库数据库的间隔复习
从数据库加载 mastery > 0 且未完全掌握的单词
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QPoint, QTimer
import tempfile
import os
import platform
import ctypes

from database import Database


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
    """将数据库行转为 dict（与学习窗口格式一致）"""
    return {
        "english":      row[1] or "",
        "pronunciation": row[2] or "",
        "chinese":      row[3] or "",
        "example":      row[4] or "",
        "memory":       "",
        "mastery":      row[5] or 0,
        "_raw":         row,
    }


class ReviewWindow(QWidget):
    """复习窗口 - 从数据库加载需要复习的单词"""

    def __init__(self):
        super().__init__()
        self.current_index = 0
        self.review_words = []
        self._current_notebook_id = None
        self._drag_position = QPoint()
        self._db = Database("data/wordpet.db")
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("复习 - WordPet")
        self.setFixedSize(440, 460)
        self.setStyleSheet(REVIEW_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # ===== 标题栏 =====
        title_layout = QHBoxLayout()
        self.title_label = QLabel("🔄 复习本")
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

        # ===== 单词卡片 =====
        card_widget = QWidget()
        card_widget.setStyleSheet(REVIEW_CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)
        card_widget.setLayout(card_layout)

        self.word_label = QLabel("")
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #059669;")
        card_layout.addWidget(self.word_label)

        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 15px; color: #0891B2;")
        card_layout.addWidget(self.phonetic_label)

        self.play_btn = QPushButton("🔊 播放发音")
        self.play_btn.setFixedWidth(140)
        self.play_btn.setStyleSheet(
            "background-color: #7C3AED; color: white;"
            "border-radius: 8px; padding: 8px 16px;"
        )
        self.play_btn.clicked.connect(self._play_current_audio)
        card_layout.addWidget(self.play_btn, alignment=Qt.AlignCenter)

        self.definition_label = QLabel("")
        self.definition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.definition_label.setWordWrap(True)
        self.definition_label.setStyleSheet("font-size: 20px; color: #1A1A2E; font-weight: bold;")
        card_layout.addWidget(self.definition_label)

        self.example_label = QLabel("")
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("font-size: 13px; color: #4B5563; font-style: italic;")
        card_layout.addWidget(self.example_label)

        self.mastery_label = QLabel("")
        self.mastery_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mastery_label.setStyleSheet(
            "font-size: 13px; color: #059669; "
            "background-color: #DCFCE7; "
            "padding: 8px 12px; border-radius: 8px;"
        )
        card_layout.addWidget(self.mastery_label)

        main_layout.addWidget(card_widget)

        # ===== 进度 =====
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #6B6B8A; font-size: 13px;")
        main_layout.addWidget(self.progress_label)

        # ===== 底部按钮 =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        pass_btn = QPushButton("✅ 记住了")
        pass_btn.setStyleSheet(
            "background-color: #059669; color: white;"
            "border-radius: 8px; padding: 10px 16px;"
        )
        pass_btn.clicked.connect(self._on_pass)
        buttons_layout.addWidget(pass_btn)

        clear_btn = QPushButton("🗑️ 重置进度")
        clear_btn.setStyleSheet(
            "background-color: #DC2626; color: white;"
            "border-radius: 8px; padding: 10px 16px;"
        )
        clear_btn.clicked.connect(self._on_clear)
        buttons_layout.addWidget(clear_btn)

        main_layout.addLayout(buttons_layout)

    # ── 辅助：按需显示/隐藏标签 ────────────────────────────────────

    @staticmethod
    def _set_label_visible(label: QLabel, text: str, prefix: str = ""):
        """有内容则显示，无内容则隐藏"""
        if text:
            label.setText(f"{prefix}{text}" if prefix else text)
            label.show()
        else:
            label.setText("")
            label.hide()

    # ── 数据 ──────────────────────────────────────────────────────────

    def load_from_database(self, notebook_id=None):
        """从数据库加载需要复习的单词，可指定词汇本"""
        self._current_notebook_id = notebook_id
        rows = self._db.get_review_words(notebook_id)
        self.review_words = [_db_row_to_dict(r) for r in rows]
        self.current_index = 0
        review_count = len(self.review_words)

        if notebook_id:
            notebooks = self._db.get_all_notebooks()
            name = next((nb[1] for nb in notebooks if nb[0] == notebook_id), "")
            self.title_label.setText(f"🔄 复习 - {name}  ({review_count} 个待复习)")
        else:
            self.title_label.setText(f"🔄 复习本  ({review_count} 个待复习)")

        self.show_current_word()

    def show_current_word(self):
        if not self.review_words:
            self.word_label.setText("📚 暂无待复习单词")
            self._set_label_visible(self.phonetic_label, "")
            self._set_label_visible(self.definition_label, "去学习窗口 Pass 单词后，它们会出现在这里")
            self._set_label_visible(self.example_label, "")
            self._set_label_visible(self.mastery_label, "")
            self.play_btn.hide()
            self.progress_label.setText("0 / 0")
            return

        if self.current_index < len(self.review_words):
            word = self.review_words[self.current_index]
            self.word_label.setText(word.get("english", ""))
            self._set_label_visible(self.phonetic_label, word.get("pronunciation", ""))
            self._set_label_visible(self.definition_label, word.get("chinese", ""))
            self._set_label_visible(self.example_label, word.get("example", ""))
            mastery = word.get("mastery", 0)
            self._set_label_visible(self.mastery_label, f"{'★' * mastery}{'☆' * (5 - mastery)}", "⭐ 掌握度: ")
            self.play_btn.show()
            self.progress_label.setText(f"{self.current_index + 1} / {len(self.review_words)}")

            english = word.get("english", "")
            if english:
                self._play_audio(english)
        else:
            self.word_label.setText("🎉 复习完成！")
            self._set_label_visible(self.phonetic_label, "")
            self._set_label_visible(self.definition_label, "恭喜你完成了本轮复习")
            self._set_label_visible(self.example_label, "")
            self._set_label_visible(self.mastery_label, "")
            self.play_btn.hide()
            self.progress_label.setText(f"{len(self.review_words)} / {len(self.review_words)}")

    # ── 音频（静默播放）──────────────────────────────────────────────

    def _play_current_audio(self):
        if not self.review_words or self.current_index >= len(self.review_words):
            return
        word = self.review_words[self.current_index]
        english = word.get("english", "")
        if english:
            self._play_audio(english)

    def _play_audio(self, text: str):
        """静默播放 TTS 音频（Windows MCI API，不弹播放器）"""
        if not text:
            return
        try:
            from gtts import gTTS
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(temp_path)
            _mci_play(temp_path, self)
        except Exception as e:
            print(f"[Audio] 播放失败: {e}")

    # ── 交互 ──────────────────────────────────────────────────────────

    def _on_pass(self):
        """复习通过：数据库 mastery +1，然后下一个"""
        if self.review_words and self.current_index < len(self.review_words):
            word = self.review_words[self.current_index]
            word_text = word.get("english", "")
            if word_text:
                self._db.increase_mastery(word_text)
            self.current_index += 1
            self.show_current_word()

    def _on_clear(self):
        """重置所有单词的掌握度（相当于清空复习本）"""
        msg = QMessageBox(self)
        msg.setWindowTitle("确认重置")
        msg.setText("这将重置所有单词的掌握度（mastery 归零），\n相当于从头开始学习。\n\n确定要重置吗？")
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet("""
            QMessageBox { background-color: #F0FDF4; }
            QLabel { color: #1A1A2E; font-size: 14px; }
            QPushButton {
                background-color: #4A3FB5; color: #FFFFFF;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        yes_btn = msg.addButton("确定重置", QMessageBox.YesRole)
        no_btn  = msg.addButton("取消", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self._db.reset_all_mastery()
            self.load_from_database()

    # ── 拖拽 ──────────────────────────────────────────────────────────

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
        """每次显示时从数据库刷新复习列表"""
        super().showEvent(event)
        self.load_from_database()


def _safe_unlink(path):
    try:
        os.unlink(path)
    except Exception:
        pass


# ── Windows MCI 静默播放 ────────────────────────────────────────────
_mci_counter = 0

def _mci_play(filepath: str, parent=None):
    """用 Windows MCI API 静默播放 MP3，不弹出任何播放器窗口"""
    global _mci_counter
    _mci_counter += 1
    alias = f"wp_audio_{_mci_counter}"

    if platform.system() != "Windows":
        os.startfile(filepath)
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
        return

    try:
        winmm = ctypes.windll.winmm
        open_cmd = f'open "{filepath}" alias {alias}'
        winmm.mciSendStringW(open_cmd, None, 0, None)
        play_cmd = f'play {alias}'
        winmm.mciSendStringW(play_cmd, None, 0, None)

        def _cleanup():
            try:
                winmm.mciSendStringW(f'close {alias}', None, 0, None)
            except Exception:
                pass
            _safe_unlink(filepath)

        if parent:
            QTimer.singleShot(8000, _cleanup)
        else:
            import threading
            threading.Timer(8.0, _cleanup).start()
    except Exception as e:
        print(f"[MCI] 播放失败: {e}")
        try:
            os.startfile(filepath)
        except Exception:
            pass
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
