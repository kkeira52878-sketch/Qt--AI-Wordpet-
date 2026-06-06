# -*- coding: utf-8 -*-
"""
词汇库窗口 — 显示和管理用户词汇, 详情弹窗 / 搜索 / 重查词全走新三态 + WordCardRenderer。
"""
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QDialog, QComboBox, QTextEdit,
)
from PySide6.QtCore import Qt, QPoint, QRunnable, QThreadPool, QObject, Signal
from PySide6.QtGui import QColor

from database import Database
from word_card_renderer import (
    render_word_card, parse_meanings, search_in_json, get_first_definition,
)
from audio_player import synthesize_audio_bytes, play_audio_bytes

# 3b-2: 跨词本同步总线 — vocabulary 切词本时 publish(nb_id),
# learning/review_window subscribe 监听, 弹窗显示"⚠️ 词本已切换"提示条
import main as _main


# ── 进程级 in-flight 防御性去重 (vocabulary 域 runnable 专用) ──
_inflight_lock = threading.Lock()
_inflight: set = set()  # {(word, notebook_id), ...}


def _try_acquire_inflight(word: str, notebook_id: int) -> bool:
    key = (word, notebook_id)
    with _inflight_lock:
        if key in _inflight:
            return False
        _inflight.add(key)
        return True


def _release_inflight(word: str, notebook_id: int) -> None:
    with _inflight_lock:
        _inflight.discard((word, notebook_id))


# ── 调词 + 缓存 Runnable (vocabulary 域) ──────────────────────────


class _FetchSignals(QObject):
    done = Signal(str, dict)     # (word, result)
    failed = Signal(str, str)    # (word, reason)


class FetchAndSaveRunnable(QRunnable):
    """后台: dict_api.query_word → 预生成音频 → update_word_details。
    成功 emit done; 失败 (网络/未收录/异常) emit failed + mark_lookup_failed。
    """

    def __init__(self, db_path: str, word: str, notebook_id: int):
        super().__init__()
        self.db_path = db_path
        self.word = word
        self.notebook_id = notebook_id
        self.signals = _FetchSignals()

    def run(self):
        try:
            from dict_api import query_word
            result = query_word(self.word)
        except Exception as e:
            print(f"[Vocab-Runnable] 查询失败 ({self.word}): {e}")
            result = {}

        from database import Database
        db = Database(self.db_path)

        if result:
            # 预生成音频, 失败容忍 (gTTS 报错不影响主流程)
            audio = synthesize_audio_bytes(self.word)
            try:
                db.update_word_details(self.word, result, self.notebook_id, audio_bytes=audio)
                self.signals.done.emit(self.word, result)
            except Exception as e:
                print(f"[Vocab-Runnable] update 失败 ({self.word}): {e}")
                db.mark_lookup_failed(self.word, self.notebook_id)
                self.signals.failed.emit(self.word, str(e))
        else:
            db.mark_lookup_failed(self.word, self.notebook_id)
            self.signals.failed.emit(self.word, "词典未收录")


# ── 样式 (保留) ──────────────────────────────────────────────
LIGHT_STYLE = """
    QWidget {
        background-color: #F0F4FF;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        color: #1A1A2E;
    }
    QLabel#title {
        font-size: 20px;
        font-weight: bold;
        color: #4A3FB5;
    }
    QLabel#stats {
        font-size: 12px;
        color: #6B6B8A;
    }
    QPushButton {
        background-color: #4A3FB5;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #3730A3;
    }
    QPushButton#close_btn {
        background-color: transparent;
        color: #6B6B8A;
        font-size: 20px;
        padding: 0;
    }
    QPushButton#close_btn:hover {
        color: #DC2626;
    }
    QPushButton#learn_btn,
    QPushButton#review_btn {
        background-color: #4A3FB5;
    }
    QPushButton#learn_btn:hover,
    QPushButton#review_btn:hover {
        background-color: #3730A3;
    }
    QPushButton#add_btn {
        background-color: #7C3AED;
    }
    QPushButton#add_btn:hover {
        background-color: #6D28D9;
    }
    QPushButton#delete_btn {
        background-color: #DC2626;
    }
    QPushButton#delete_btn:hover {
        background-color: #B91C1C;
    }
    QPushButton#clear_btn {
        background-color: #6B7280;
    }
    QPushButton#clear_btn:hover {
        background-color: #4B5563;
    }
    QPushButton#notebook_new_btn {
        background-color: #F59E0B;
        color: white;
        font-size: 12px;
        padding: 6px 12px;
    }
    QPushButton#notebook_new_btn:hover {
        background-color: #D97706;
    }
    QPushButton#notebook_del_btn {
        background-color: #EF4444;
        color: white;
        font-size: 12px;
        padding: 6px 12px;
    }
    QPushButton#notebook_del_btn:hover {
        background-color: #DC2626;
    }
    QListWidget {
        border: 2px solid #C7D2FE;
        border-radius: 8px;
        background-color: #FFFFFF;
        color: #1A1A2E;
        outline: none;
    }
    QListWidget::item {
        padding: 10px 12px;
        border-bottom: 1px solid #E0E7FF;
        color: #1A1A2E;
    }
    QListWidget::item:selected {
        background-color: #4A3FB5;
        color: #FFFFFF;
    }
    QListWidget::item:hover {
        background-color: #EEF2FF;
    }
    QLineEdit {
        border: 2px solid #C7D2FE;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        background-color: #FFFFFF;
        color: #1A1A2E;
    }
    QLineEdit:focus {
        border-color: #4A3FB5;
    }
    QLineEdit::placeholder {
        color: #9CA3AF;
    }
    QComboBox {
        border: 2px solid #C7D2FE;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
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

DIALOG_STYLE = """
    QDialog {
        background-color: #F0F4FF;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }
    QLabel {
        color: #1A1A2E;
        font-size: 14px;
    }
    QLineEdit {
        background-color: #FFFFFF;
        color: #1A1A2E;
        border: 2px solid #C7D2FE;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 16px;
        min-height: 36px;
    }
    QLineEdit:focus {
        border-color: #4A3FB5;
    }
    QPushButton {
        background-color: #4A3FB5;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 14px;
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }
    QPushButton:hover { background-color: #3730A3; }
    QPushButton#cancel_btn {
        background-color: #6B7280;
    }
    QPushButton#cancel_btn:hover { background-color: #4B5563; }
"""


# ── 工具: DB tuple → word_data dict ──────────────────────────────


def _row_to_word_data(row) -> dict:
    """DB tuple → 渲染所需的 word_data dict。
    tuple 列顺序: id(0), word(1), phonetic(2), definition(3), example(4),
                  mastery(5), is_favorite(6), notebook_id(7),
                  created_at(8), last_reviewed(9), next_review(10),
                  notes(11), meanings_json(12), lookup_status(13), audio_cache(14)
    """
    if row is None:
        return {}
    meanings = parse_meanings(row[12] if len(row) > 12 else None)
    return {
        "english":       row[1] or "",
        "pronunciation": row[2] or "",
        "meanings":      meanings,
        "memory":        "",
        "mastery":       row[5] or 0,
        "lookup_status": row[13] if len(row) > 13 else "never",
        "count_meanings": len(meanings),
    }


# ── 主窗口 ──────────────────────────────────────────────────────


class VocabularyWindow(QWidget):
    """词汇库窗口 — 无框可拖拽, 显示单词列表和学习入口。"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.db = Database("data/wordpet.db")
        self._drag_position = QPoint()
        self._current_notebook_id = 1

        self._learning_window = None
        self._review_window = None

        self._setup_ui()
        self._refresh_notebooks()
        self._load_words()

    # ── 窗口注入接口 ──

    def set_learning_window(self, window):
        self._learning_window = window

    def set_review_window(self, window):
        self._review_window = window

    # ── UI 搭建 ──

    def _setup_ui(self):
        self.setWindowTitle("词汇库 - WordPet")
        self.setFixedSize(500, 520)
        self.setStyleSheet(LIGHT_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)

        # 标题栏
        title_layout = QHBoxLayout()
        self.title_label = QLabel("📚 词汇库")
        self.title_label.setObjectName("title")
        title_layout.addWidget(self.title_label)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("stats")
        title_layout.addWidget(self.stats_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        # 词汇本选择器
        notebook_layout = QHBoxLayout()
        notebook_layout.setSpacing(6)

        notebook_label = QLabel("📓 词汇本：")
        notebook_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4A3FB5;")
        notebook_layout.addWidget(notebook_label)

        self.notebook_combo = QComboBox()
        self.notebook_combo.setMinimumWidth(160)
        self.notebook_combo.currentIndexChanged.connect(self._on_notebook_changed)
        notebook_layout.addWidget(self.notebook_combo)

        new_nb_btn = QPushButton("➕ 新建")
        new_nb_btn.setObjectName("notebook_new_btn")
        new_nb_btn.clicked.connect(self._on_new_notebook)
        notebook_layout.addWidget(new_nb_btn)

        del_nb_btn = QPushButton("🗑️ 删除")
        del_nb_btn.setObjectName("notebook_del_btn")
        del_nb_btn.clicked.connect(self._on_delete_notebook)
        notebook_layout.addWidget(del_nb_btn)

        main_layout.addLayout(notebook_layout)

        # 学习入口按钮 (3b-2: 学习/复习合并成 1 个 "📖 记单词" 按钮, 走 B1 闪卡流)
        flashcard_btn = QPushButton("📖 记单词")
        flashcard_btn.setObjectName("learn_btn")  # 复用 learn_btn 紫样式
        flashcard_btn.setMinimumHeight(36)
        flashcard_btn.clicked.connect(self._open_flashcard)
        main_layout.addWidget(flashcard_btn)

        # 搜索栏
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索单词（模糊匹配）...")
        self.search_input.textChanged.connect(self._on_search)
        main_layout.addWidget(self.search_input)

        # 单词列表
        self.word_list = QListWidget()
        self.word_list.itemClicked.connect(self._on_item_clicked)
        main_layout.addWidget(self.word_list)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        add_btn = QPushButton("➕ 添加单词")
        add_btn.setObjectName("add_btn")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self._on_add)
        button_layout.addWidget(add_btn)

        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setObjectName("delete_btn")
        delete_btn.setMinimumHeight(36)
        delete_btn.clicked.connect(self._on_delete)
        button_layout.addWidget(delete_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("clear_btn")
        clear_btn.setMinimumHeight(36)
        clear_btn.clicked.connect(self._on_clear)
        button_layout.addWidget(clear_btn)

        main_layout.addLayout(button_layout)

    # ── 词汇本管理 ──

    def _refresh_notebooks(self):
        notebooks = self.db.get_all_notebooks()
        self.notebook_combo.blockSignals(True)
        self.notebook_combo.clear()
        for nb in notebooks:
            nb_id, nb_name, _, word_count = nb
            self.notebook_combo.addItem(f"{nb_name} ({word_count}词)", nb_id)
        for i in range(self.notebook_combo.count()):
            if self.notebook_combo.itemData(i) == self._current_notebook_id:
                self.notebook_combo.setCurrentIndex(i)
                break
        self.notebook_combo.blockSignals(False)

    def _on_notebook_changed(self, index):
        """切换词汇本 + 3b-2: 通知 bus, learning/review 弹窗显示"词本已切换"提示条"""
        if index < 0:
            return
        nb_id = self.notebook_combo.itemData(index)
        if nb_id is not None:
            self._current_notebook_id = nb_id
            self._load_words()
            # 3b-2: 跨词本同步 — 通知 learning/review 弹窗 (Q2 选 b, 弹窗不自动重载)
            try:
                _main.notebook_bus.publish(nb_id)
            except Exception as e:
                print(f"[VocabWindow] bus.publish failed: {e}")

    def _on_new_notebook(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("新建词汇本")
        dialog.setFixedSize(320, 160)
        dialog.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        label = QLabel("请输入词汇本名称：")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(label)

        input_edit = QLineEdit()
        input_edit.setPlaceholderText("例如：GRE词汇")
        input_edit.setMinimumHeight(40)
        layout.addWidget(input_edit)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("创建")
        ok_btn.setMinimumHeight(36)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setMinimumHeight(36)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        dialog.setLayout(layout)
        input_edit.setFocus()
        input_edit.returnPressed.connect(dialog.accept)

        if dialog.exec() != QDialog.Accepted:
            return

        name = input_edit.text().strip()
        if not name:
            return

        result = self.db.create_notebook(name)
        if result == "exists":
            QMessageBox.information(self, "提示", f"词汇本 '{name}' 已存在")
        else:
            self._current_notebook_id = result
            self._refresh_notebooks()
            self._load_words()

    def _on_delete_notebook(self):
        if self._current_notebook_id == 1:
            QMessageBox.information(self, "提示", "默认词汇本不可删除")
            return

        nb_name = self._get_current_notebook_name()
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除词汇本 '{nb_name}' 及其所有单词吗？\n此操作不可恢复！")
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet("""
            QMessageBox { background-color: #F0F4FF; }
            QLabel { color: #1A1A2E; font-size: 14px; }
            QPushButton {
                background-color: #4A3FB5; color: #FFFFFF;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        yes_btn = msg.addButton("确定删除", QMessageBox.YesRole)
        no_btn = msg.addButton("取消", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self.db.delete_notebook(self._current_notebook_id)
            self._current_notebook_id = 1
            self._refresh_notebooks()
            self._load_words()

    def _get_current_notebook_name(self):
        index = self.notebook_combo.currentIndex()
        if index >= 0:
            text = self.notebook_combo.itemText(index)
            return text.rsplit(" (", 1)[0]
        return Database.DEFAULT_NOTEBOOK

    # ── 数据加载 ──

    def _load_words(self, filter_text: str = ""):
        """加载单词到列表 (按当前词汇本), 搜索命中英文/notes/全释义。
        snippet 来源: meanings_json[0].definitions[0] (回退到旧 definition 列)。
        """
        words = self.db.get_all_word(self._current_notebook_id)
        self.word_list.clear()

        if filter_text:
            ft = filter_text.lower()
            words = [
                w for w in words
                if ft in (w[1] or "").lower()
                or search_in_json(w[12] if len(w) > 12 else None, ft)
                or (len(w) > 12 and w[12] and ft in (w[12] or "").lower())  # 旧 definition (兜底)
            ]

        for word in words:
            display_text = word[1] or ""
            meanings = parse_meanings(word[12] if len(word) > 12 else None)
            snippet = get_first_definition(meanings) or (word[3] or "")
            if snippet:
                snippet = snippet[:28] + ("…" if len(snippet) > 28 else "")
                display_text += f"  —  {snippet}"

            status = word[13] if len(word) > 13 else "never"
            if status == "failed":
                display_text = f"⚠️  {display_text}  (未收录)"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, word[1])
            if status == "failed":
                item.setForeground(Qt.gray)
            self.word_list.addItem(item)

        total = len(words)
        self.stats_label.setText(
            f"找到 {total} 个" if filter_text else f"共 {total} 个单词"
        )

    def _on_search(self, text: str):
        self._load_words(text.strip())

    # ── 手动添加 (走 add_word + 后台 runnable) ──

    def _on_add(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加单词")
        dialog.setFixedSize(360, 190)
        dialog.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        nb_name = self._get_current_notebook_name()
        label = QLabel(f"添加到「{nb_name}」：请输入英文单词")
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1A1A2E;")
        layout.addWidget(label)

        input_edit = QLineEdit()
        input_edit.setPlaceholderText("例如：apple")
        input_edit.setMinimumHeight(44)
        layout.addWidget(input_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        ok_btn = QPushButton("确定")
        ok_btn.setMinimumHeight(38)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setMinimumHeight(38)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        dialog.setLayout(layout)
        input_edit.setFocus()
        input_edit.returnPressed.connect(dialog.accept)

        if dialog.exec() != QDialog.Accepted:
            return

        word_text = input_edit.text().strip()
        if not word_text:
            return

        word = word_text.lower()
        result = self.db.add_word(word, self._current_notebook_id)

        if result == "exists":
            QMessageBox.information(self, "提示", f"'{word}' 已在此词汇本中")
        elif result == "success":
            self._load_words(self.search_input.text().strip())
            # 启动后台查词, 完成后 _on_fetch_done 触发列表刷新
            runnable = FetchAndSaveRunnable(
                "data/wordpet.db", word, self._current_notebook_id
            )
            runnable.signals.done.connect(self._on_fetch_done)
            runnable.signals.failed.connect(self._on_fetch_failed)
            QThreadPool.globalInstance().start(runnable)

    def _on_fetch_done(self, word: str, result: dict):
        # 查词成功 → 刷新列表 (meanings_json 已写入)
        self._load_words(self.search_input.text().strip())

    def _on_fetch_failed(self, word: str, reason: str):
        # 查词失败 → 刷新列表 (status='failed' + 灰色 + ⚠️)
        self._load_words(self.search_input.text().strip())

    # ── 详情弹窗 (走 WordCardRenderer) ──

    def _on_item_clicked(self, item: QListWidgetItem):
        word_text = item.data(Qt.UserRole)
        word_row = self.db.get_one_word(word_text, self._current_notebook_id)
        if not word_row:
            word_row = self.db.get_one_word(word_text)
        if not word_row:
            return

        self._show_detail_dialog(word_row)

    def _show_detail_dialog(self, word_row):
        """详情弹窗: 走 WordCardRenderer(mode='detail'), 重新查词按钮在 pending 期间 disabled。"""
        word_text = word_row[1]
        word_data = _row_to_word_data(word_row)
        notes = word_row[11] if len(word_row) > 11 else ""

        dialog = QDialog(self)
        dialog.setWindowTitle(f"单词详情 — {word_text}")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #F0F4FF;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QLabel { color: #1A1A2E; font-size: 14px; }
            QTextEdit {
                background-color: #FFFFFF;
                color: #1A1A2E;
                border: 2px solid #C7D2FE;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton {
                background-color: #4A3FB5; color: white;
                border: none; border-radius: 8px;
                padding: 10px 16px; font-size: 14px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton:hover { background-color: #3730A3; }
            QPushButton:disabled { background-color: #C7D2FE; color: #6B6B8A; }
            QPushButton#retry_btn {
                background-color: #F59E0B;
            }
            QPushButton#retry_btn:hover { background-color: #D97706; }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # 标题
        title = QLabel(f"📝 {word_text}")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #4A3FB5;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 音标 (有才显示)
        phonetic = word_data.get("pronunciation", "")
        if phonetic:
            ph = QLabel(f"🔤 {phonetic}")
            ph.setStyleSheet("font-size: 14px; color: #7C3AED;")
            ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(ph)

        # 释义 QTextEdit — 走 WordCardRenderer
        meanings_edit = QTextEdit()
        meanings_edit.setReadOnly(True)
        meanings_edit.setMinimumHeight(160)
        meanings_edit.setMaximumHeight(320)
        result = render_word_card(word_data, mode='detail')
        meanings_edit.setHtml(result.html)
        layout.addWidget(meanings_edit)

        # 播放发音按钮 (跟 learning_window.py:170 风格一致)
        play_btn = QPushButton("🔊 播放发音")
        play_btn.setFixedWidth(140)
        play_btn.setStyleSheet(
            "background-color: #7C3AED; color: white;"
            "border-radius: 8px; padding: 8px 16px;"
        )
        play_btn.clicked.connect(
            lambda: self._play_audio_for_dialog(word_text, self._current_notebook_id, dialog)
        )
        layout.addWidget(play_btn, alignment=Qt.AlignCenter)

        # 备注
        layout.addWidget(QLabel("📝 notes："))
        notes_edit = QTextEdit(notes)
        notes_edit.setPlaceholderText("Your ideas / 手动补全的释义也可写在这里")
        notes_edit.setMaximumHeight(80)
        layout.addWidget(notes_edit)

        # 按钮行
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 save notes")
        save_btn.clicked.connect(
            lambda: self._save_word_notes(word_text, notes_edit.toPlainText(), dialog)
        )
        btn_layout.addWidget(save_btn)

        # 重新查词按钮 — 仅 failed 时显示
        retry_btn = QPushButton("🔄 重新查词")
        retry_btn.setObjectName("retry_btn")
        retry_btn.setVisible(result.show_retry_button)
        retry_btn.clicked.connect(
            lambda: self._retry_lookup(word_text, self._current_notebook_id, dialog, retry_btn, meanings_edit)
        )
        btn_layout.addWidget(retry_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def _retry_lookup(self, word_text: str, notebook_id: int, dialog, retry_btn, meanings_edit):
        """详情弹窗点击'重新查词': mark_lookup_pending + 启动 runnable + pending 期间按钮 disabled。"""
        if not _try_acquire_inflight(word_text, notebook_id):
            return  # 防御性: 已有同词查询在飞
        retry_btn.setDisabled(True)
        retry_btn.setText("🔄 查询中…")
        dialog.setWindowTitle(f"单词详情 — {word_text}  (重新查询中…)")

        # 状态机: success/failed → never
        self.db.mark_lookup_pending(word_text, notebook_id)

        def _on_done(w: str, result_dict: dict):
            _release_inflight(w, notebook_id)
            # 原地刷新弹窗: 重新查 DB, 重新渲染
            new_row = self.db.get_one_word(w, notebook_id)
            if new_row:
                wd = _row_to_word_data(new_row)
                r = render_word_card(wd, mode='detail')
                meanings_edit.setHtml(r.html)
                retry_btn.setVisible(r.show_retry_button)
            retry_btn.setDisabled(False)
            retry_btn.setText("🔄 重新查词")
            dialog.setWindowTitle(f"单词详情 — {w}")
            self._load_words(self.search_input.text().strip())

        def _on_failed(w: str, reason: str):
            _release_inflight(w, notebook_id)
            retry_btn.setDisabled(False)
            retry_btn.setText("🔄 重新查词")
            dialog.setWindowTitle(f"单词详情 — {w}  (⚠️ 仍然失败: {reason})")
            self._load_words(self.search_input.text().strip())

        runnable = FetchAndSaveRunnable("data/wordpet.db", word_text, notebook_id)
        runnable.signals.done.connect(_on_done)
        runnable.signals.failed.connect(_on_failed)
        QThreadPool.globalInstance().start(runnable)

    def _save_word_notes(self, word_text, notes, dialog):
        self.db.update_word_notes(word_text, notes, self._current_notebook_id)
        QMessageBox.information(self, "success", f"'{word_text}' notes saved")
        dialog.accept()

    def _play_audio_for_dialog(self, word_text, notebook_id, dialog):
        """详情弹窗播放发音: 先查 DB cache, 命中直接 MCI 播放; 未命中 gTTS + 缓存。"""
        if not word_text:
            return
        cached = self.db.get_audio_cache(word_text, notebook_id)
        if cached:
            play_audio_bytes(cached, dialog)
            return
        audio = synthesize_audio_bytes(word_text)
        if audio:
            self.db.save_audio_cache(word_text, notebook_id, audio)
            play_audio_bytes(audio, dialog)

    # ── 删除 / 清空 ──

    def _on_delete(self):
        current_item = self.word_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个单词")
            return
        word_text = current_item.data(Qt.UserRole)
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText(f"确定要删除 '{word_text}' 吗？")
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet("""
            QMessageBox { background-color: #F0F4FF; }
            QLabel { color: #1A1A2E; font-size: 14px; }
            QPushButton {
                background-color: #4A3FB5; color: #FFFFFF;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        yes_btn = msg.addButton("确定", QMessageBox.YesRole)
        no_btn = msg.addButton("取消", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self.db.del_word(word_text, self._current_notebook_id)
            self._load_words(self.search_input.text().strip())

    def _on_clear(self):
        nb_name = self._get_current_notebook_name()
        msg = QMessageBox(self)
        msg.setWindowTitle("确认清空")
        msg.setText(f"确定要清空「{nb_name}」中的所有单词吗？\n此操作不可恢复！")
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet("""
            QMessageBox { background-color: #F0F4FF; }
            QLabel { color: #1A1A2E; font-size: 14px; }
            QPushButton {
                background-color: #4A3FB5; color: #FFFFFF;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #3730A3; }
        """)
        yes_btn = msg.addButton("确定清空", QMessageBox.YesRole)
        no_btn = msg.addButton("取消", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self.db.del_all(self._current_notebook_id)
            self._load_words()

    # ── 学习 / 复习入口 ──

    def _open_learning(self):
        win = self._learning_window
        if win:
            win.load_from_database(self._current_notebook_id)
            win.show()
            win.raise_()
            win.activateWindow()
        else:
            try:
                import main as _m
                w = _m.learning_window
                if w:
                    w.load_from_database(self._current_notebook_id)
                    w.show()
                    w.raise_()
                    w.activateWindow()
            except Exception as e:
                print(f"[VocabWindow] 无法打开学习窗口: {e}")

    def _open_review(self):
        win = self._review_window
        if win:
            win.load_from_database(self._current_notebook_id)
            win.show()
            win.raise_()
            win.activateWindow()
        else:
            try:
                import main as _m
                _m.show_review_window()
            except Exception as e:
                print(f"[VocabWindow] 无法打开复习窗口: {e}")

    def _open_flashcard(self):
        """3b-2: 顶部"📖 记单词"按钮入口 — 走 B1 闪卡流 (只调 learning_window, 合并学习/复习)"""
        win = self._learning_window
        if win:
            win.load_from_database(self._current_notebook_id)
            win.show()
            win.raise_()
            win.activateWindow()
        else:
            try:
                import main as _m
                w = _m.learning_window
                if w:
                    w.load_from_database(self._current_notebook_id)
                    w.show()
                    w.raise_()
                    w.activateWindow()
            except Exception as e:
                print(f"[VocabWindow] 无法打开闪卡窗口: {e}")

    # ── 拖拽 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if not self._drag_position.isNull():
                self.move(event.globalPosition().toPoint() - self._drag_position)
                event.accept()

    def showEvent(self, event):
        self._refresh_notebooks()
        self._load_words()
        super().showEvent(event)
