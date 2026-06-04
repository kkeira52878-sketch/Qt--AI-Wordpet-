# -*- coding: utf-8 -*-
"""
学习窗口 - 基于数据库词汇本的单词学习
所有词汇本统一由数据库管理，无硬编码数据源
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QComboBox
)
from PySide6.QtCore import Qt, QPoint, QTimer
import tempfile
import os
import platform
import random
import ctypes

from database import Database


# ── 亮色主题样式 ──────────────────────────────────────────────────────
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

BOOK_SELECTOR_STYLE = """
    QDialog {
        background-color: #F5F3FF;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }
    QLabel {
        font-size: 15px;
        font-weight: bold;
        color: #1A1A2E;
        padding: 4px;
    }
    QPushButton {
        background-color: #4A3FB5;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }
    QPushButton:hover { background-color: #3730A3; }
    QComboBox {
        border: 2px solid #C7D2FE;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        background-color: #FFFFFF;
        color: #1A1A2E;
        min-height: 28px;
    }
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #C7D2FE;
        background-color: #FFFFFF;
        color: #1A1A2E;
        selection-background-color: #4A3FB5;
        selection-color: white;
    }
"""


def _db_row_to_dict(row) -> dict:
    """将数据库查询结果 (tuple) 转为显示用的 dict

    DB 列顺序: id, word, phonetic, definition, example, mastery,
               is_favorite, notebook_id, created_at, last_reviewed, next_review
    """
    return {
        "english":      row[1] or "",
        "pronunciation": row[2] or "",
        "chinese":      row[3] or "",
        "example":      row[4] or "",
        "memory":       "",
        "mastery":      row[5] or 0,
        "_source":      "db",
        "_raw":         row,
    }


class LearningWindow(QWidget):
    """学习窗口 - 统一从数据库加载单词"""

    def __init__(self):
        super().__init__()
        self.current_words = []
        self.current_index = 0
        self.current_book_name = None
        self._current_notebook_id = None  # 当前选中的词汇本 ID
        self._drag_position = QPoint()
        self._db = Database("data/wordpet.db")
        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("学习 - WordPet")
        self.setFixedSize(440, 500)
        self.setStyleSheet(LEARNING_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # ===== 标题栏 =====
        title_layout = QHBoxLayout()
        self.book_label = QLabel("📖 请先选择词汇本")
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

        # ===== 单词卡片 =====
        card_widget = QWidget()
        card_widget.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)
        card_widget.setLayout(card_layout)

        self.word_label = QLabel("")
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #4A3FB5;")
        card_layout.addWidget(self.word_label)

        self.phonetic_label = QLabel("")
        self.phonetic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 15px; color: #059669;")
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

        self.memory_label = QLabel("")
        self.memory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.memory_label.setWordWrap(True)
        self.memory_label.setStyleSheet(
            "font-size: 13px; color: #7C3AED; "
            "background-color: #EDE9FE; "
            "padding: 8px 12px; border-radius: 8px;"
        )
        card_layout.addWidget(self.memory_label)

        main_layout.addWidget(card_widget)

        # ===== 进度 =====
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #6B6B8A; font-size: 13px;")
        main_layout.addWidget(self.progress_label)

        # ===== 底部按钮 =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        select_book_btn = QPushButton("📚 选择词汇本")
        select_book_btn.setStyleSheet(
            "background-color: #DC2626; color: white;"
            "border-radius: 8px; padding: 10px 16px;"
        )
        select_book_btn.clicked.connect(self._show_book_selector)
        buttons_layout.addWidget(select_book_btn)

        pass_btn = QPushButton("✅ Pass（已学会）")
        pass_btn.setStyleSheet(
            "background-color: #059669; color: white;"
            "border-radius: 8px; padding: 10px 16px;"
        )
        pass_btn.clicked.connect(self._on_pass)
        buttons_layout.addWidget(pass_btn)

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

    # ── 加载数据 ──────────────────────────────────────────────────────

    def load_from_database(self, notebook_id=None):
        """从数据库加载未学单词 (mastery == 0)，可指定词汇本"""
        rows = self._db.get_new_words(notebook_id)
        self._current_notebook_id = notebook_id

        # 获取词汇本名称
        if notebook_id:
            notebooks = self._db.get_all_notebooks()
            name = next((nb[1] for nb in notebooks if nb[0] == notebook_id), "未学单词")
            self.current_book_name = f"{name} - 未学单词"
        else:
            self.current_book_name = "全部词汇库 - 未学单词"

        self.book_label.setText(f"📖 {self.current_book_name}")

        if not rows:
            self.current_words = []
            self.show_current_word()
            return

        self.current_words = [_db_row_to_dict(r) for r in rows]
        random.shuffle(self.current_words)
        self.current_index = 0
        self.show_current_word()

    def show_current_word(self):
        if not self.current_words:
            self.word_label.setText("📚 没有可学习的单词")
            self._set_label_visible(self.phonetic_label, "")
            self._set_label_visible(self.definition_label, "去词汇库添加单词后再来学习吧")
            self._set_label_visible(self.example_label, "")
            self._set_label_visible(self.memory_label, "")
            self.play_btn.hide()
            self.progress_label.setText("0 / 0")
            return

        if self.current_index < len(self.current_words):
            word = self.current_words[self.current_index]
            self.word_label.setText(word.get("english", ""))
            self._set_label_visible(self.phonetic_label, word.get("pronunciation", ""))
            self._set_label_visible(self.definition_label, word.get("chinese", ""))
            self._set_label_visible(self.example_label, word.get("example", ""))
            self._set_label_visible(self.memory_label, word.get("memory", ""), "💡 ")
            self.play_btn.show()
            self.progress_label.setText(f"{self.current_index + 1} / {len(self.current_words)}")
            self._play_audio(word.get("english", ""))
        else:
            self.word_label.setText("🎉 本轮学习完成！")
            self._set_label_visible(self.phonetic_label, "")
            self._set_label_visible(self.definition_label, "恭喜你完成了本词汇本的学习")
            self._set_label_visible(self.example_label, "")
            self._set_label_visible(self.memory_label, "")
            self.play_btn.hide()
            self.progress_label.setText(f"{len(self.current_words)} / {len(self.current_words)}")

    # ── Pass ──────────────────────────────────────────────────────────

    def _on_pass(self):
        if not self.current_words or self.current_index >= len(self.current_words):
            return
        word = self.current_words[self.current_index]
        word_text = word.get("english", "")
        if word_text:
            self._db.mark_word_learned(word_text)
        self.current_index += 1
        self.show_current_word()

    # ── 音频（静默播放，不弹出播放器）────────────────────────────────

    def _play_current_audio(self):
        if self.current_words and self.current_index < len(self.current_words):
            self._play_audio(self.current_words[self.current_index]["english"])

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

    # ── 词汇本选择 ────────────────────────────────────────────────────

    def _show_book_selector(self):
        """从数据库读取所有词汇本，让用户选择"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择词汇本")
        dialog.setFixedSize(380, 300)
        dialog.setStyleSheet(BOOK_SELECTOR_STYLE)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.addWidget(QLabel("选择要学习的词汇本："))

        # ── 选项 1：全部词汇库 ─────────────────────────────────────
        new_count = self._db.count_new_words()
        btn_all = QPushButton(f"📋 全部词汇库  ({new_count} 个未学单词)")
        btn_all.setStyleSheet(
            "background-color: #059669; color: white; font-weight: bold; padding: 12px;"
        )
        btn_all.clicked.connect(lambda: self._select_source(None, dialog))
        layout.addWidget(btn_all)

        # ── 选项 2~N：各词汇本 ─────────────────────────────────────
        notebooks = self._db.get_all_notebooks()
        for nb_id, nb_name, _, word_count in notebooks:
            new_in_nb = self._db.count_new_words(nb_id)
            btn = QPushButton(f"📓 {nb_name}  ({new_in_nb} 个未学 / 共 {word_count} 词)")
            btn.clicked.connect(lambda checked, nid=nb_id: self._select_source(nid, dialog))
            layout.addWidget(btn)

        dialog.setLayout(layout)
        dialog.exec()

    def _select_source(self, notebook_id, dialog: QDialog):
        dialog.accept()
        self.load_from_database(notebook_id)

    # ── 拖拽 / 生命周期 ───────────────────────────────────────────────

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
        """首次显示时若未选词本则弹出选择对话框"""
        super().showEvent(event)
        if not self.current_words:
            QTimer.singleShot(120, self._show_book_selector)


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
        # 非 Windows 降级为 os.startfile
        os.startfile(filepath)
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
        return

    try:
        winmm = ctypes.windll.winmm
        # 打开音频文件
        open_cmd = f'open "{filepath}" alias {alias}'
        winmm.mciSendStringW(open_cmd, None, 0, None)
        # 播放
        play_cmd = f'play {alias}'
        winmm.mciSendStringW(play_cmd, None, 0, None)

        # 8 秒后关闭并清理临时文件
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
        # 最终降级
        try:
            os.startfile(filepath)
        except Exception:
            pass
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
