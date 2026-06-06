# -*- coding: utf-8 -*-
"""
WordPet 主程序入口 — 桌宠形态 + 词汇库 + 学习/复习功能。
剪贴板回调走新三态状态机 (add_word → 后台 QRunnable → success/failed)。
"""
import sys
import os
import threading

# 设置工作目录到 src 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QPoint, QTimer, QRunnable, QThreadPool, QObject, Signal

# 全局变量 - 窗口实例
pet_window = None
vocab_window = None
learning_window = None
review_window = None
notification_window = None


# ── 窗口管理 ──────────────────────────────────────────────────


def toggle_vocab():
    """切换词汇库显示/隐藏。"""
    global vocab_window
    if vocab_window:
        if vocab_window.isVisible():
            vocab_window.hide()
        else:
            vocab_window.show()
            vocab_window.raise_()


def show_learning_window():
    """显示学习窗口。"""
    global learning_window
    if learning_window:
        learning_window.show()
        learning_window.raise_()
        learning_window.activateWindow()


def show_review_window():
    """显示复习窗口 (从数据库刷新)。"""
    global review_window
    if review_window:
        review_window.load_from_database()
        review_window.show()
        review_window.raise_()
        review_window.activateWindow()


# ── 剪贴板/通知回调 (走新三态) ──────────────────────────────────


# 进程级 in-flight 防御性去重 (main 域 runnable 专用)
_inflight_lock = threading.Lock()
_inflight: set = set()


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


# ── 跨词本同步总线 (3b-2 引入, 风格统一 3b-1 的 LookupCoordinator) ──


class _NotebookBus:
    """简单同步事件总线: vocabulary 切词本时 publish(nb_id),
    learning/review_window 在 __init__ 末尾 subscribe 监听。
    PySide 主线程内同步调用, 零异步复杂度。
    """
    def __init__(self):
        self._subscribers: list = []  # list[callable]

    def subscribe(self, fn) -> None:
        self._subscribers.append(fn)

    def publish(self, nb_id) -> None:
        for fn in list(self._subscribers):
            try:
                fn(nb_id)
            except Exception as e:
                print(f"[NotebookBus] subscriber {fn} failed: {e}")


notebook_bus = _NotebookBus()


def _on_new_word_found(words):
    """剪贴板发现新单词 — 在主线程触发通知气泡。"""
    global notification_window
    if notification_window:
        pos = _get_bubble_pos()
        notification_window._show_notification(
            "检测到英文单词",
            "点击单词添加到词汇库",
            words,
            pos
        )


def _on_word_clicked(word):
    """通知窗口点击单词 — 走新三态: add_word (status='never') + 后台 QRunnable。"""
    from database import Database
    db = Database("data/wordpet.db")

    notebook_id = 1
    if vocab_window:
        notebook_id = vocab_window._current_notebook_id

    result = db.add_word(word, notebook_id)
    if result == "exists":
        return  # 已在词汇库, 不弹窗 (避免打扰)
    elif result == "success":
        if vocab_window:
            vocab_window._load_words()
        # 启动后台查词 (audio 预生成在 runnable 内)
        runnable = FetchWordRunnable(db, word, notebook_id)
        runnable.signals.done.connect(_on_fetch_done)
        runnable.signals.failed.connect(_on_fetch_failed)
        QThreadPool.globalInstance().start(runnable)


def _on_fetch_done(word: str, result: dict):
    """查词成功 — 刷新词汇库列表。"""
    if vocab_window:
        vocab_window._load_words()


def _on_fetch_failed(word: str, reason: str):
    """查词失败 — 单词仍在库 (status='failed'), 列表自动变灰。"""
    if vocab_window:
        vocab_window._load_words()


def _get_bubble_pos():
    """通知气泡位置 (右下角)。"""
    screen = QApplication.primaryScreen()
    screen_size = screen.size()
    x = screen_size.width() - 310
    y = screen_size.height() - 280
    return QPoint(x, y)


# ── 后台查词 + 缓存 Runnable (main 域) ──────────────────────────


class _FetchSignals(QObject):
    done = Signal(str, dict)    # (word, result)
    failed = Signal(str, str)   # (word, reason)


class FetchWordRunnable(QRunnable):
    """后台: dict_api.query_word → 预生成音频 → update_word_details。
    与 vocabulary_window.FetchAndSaveRunnable 形态一致, 但属于 main 域 in-flight 集。
    """

    def __init__(self, db, word, notebook_id):
        super().__init__()
        self.db = db
        self.word = word
        self.notebook_id = notebook_id
        self.signals = _FetchSignals()

    def run(self):
        try:
            from dict_api import query_word
            result = query_word(self.word)
        except Exception as e:
            print(f"[Main-FetchWord] 查询失败 ({self.word}): {e}")
            result = {}

        if result:
            from audio_player import synthesize_audio_bytes
            audio = synthesize_audio_bytes(self.word)
            try:
                self.db.update_word_details(self.word, result, self.notebook_id, audio_bytes=audio)
                self.signals.done.emit(self.word, result)
            except Exception as e:
                print(f"[Main-FetchWord] update 失败 ({self.word}): {e}")
                self.db.mark_lookup_failed(self.word, self.notebook_id)
                self.signals.failed.emit(self.word, str(e))
        else:
            self.db.mark_lookup_failed(self.word, self.notebook_id)
            self.signals.failed.emit(self.word, "词典未收录")


# ── 初始化 ──────────────────────────────────────────────────────


def init_app():
    """初始化应用。"""
    global pet_window, vocab_window, learning_window, review_window, notification_window

    os.makedirs("data", exist_ok=True)
    os.makedirs("asset/image", exist_ok=True)

    from database import Database
    db = Database("data/wordpet.db")

    from pet_window import PetWindow
    from vocabulary_window import VocabularyWindow
    from learning_window import LearningWindow
    from review_window import ReviewWindow
    from notification_window import NotificationWindow
    from clipboard_monitor import ClipboardMonitor

    pet_window = PetWindow()
    vocab_window = VocabularyWindow()
    learning_window = LearningWindow()
    review_window = ReviewWindow()
    notification_window = NotificationWindow()

    pet_window.clicked.connect(toggle_vocab)
    notification_window.word_clicked.connect(_on_word_clicked)

    clipboard_monitor = ClipboardMonitor("data/wordpet.db")
    clipboard_monitor.new_word_found.connect(_on_new_word_found)

    def _on_monitor_toggled():
        if pet_window:
            pet_window.on_monitor_toggled()
    clipboard_monitor.toggled.connect(_on_monitor_toggled)

    pet_window._clipboard_monitor = clipboard_monitor
    vocab_window.set_learning_window(learning_window)
    vocab_window.set_review_window(review_window)
    pet_window._learning_window = learning_window
    pet_window._review_window = review_window
    pet_window._vocabulary_window = vocab_window  # 3b-2 注入, _open_flashcard 用

    pet_window.show()
    return True


# ── 程序入口 ──────────────────────────────────────────────────


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if init_app():
        sys.exit(app.exec())
