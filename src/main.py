# -*- coding: utf-8 -*-
"""
WordPet 主程序入口
桌宠形态 + 词汇库 + 学习/复习功能
整合 version1 的学习界面和 my version 的桌宠架构
"""

import sys
import os

# 设置工作目录到 src 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QPoint, QTimer, QRunnable, QThreadPool, Signal, QObject

# 全局变量 - 窗口实例
pet_window = None
vocab_window = None
learning_window = None
review_window = None
notification_window = None


# ========== 窗口管理 ==========

def toggle_vocab():
    """切换词汇库显示/隐藏"""
    global vocab_window
    if vocab_window:
        if vocab_window.isVisible():
            vocab_window.hide()
        else:
            vocab_window.show()
            vocab_window.raise_()


def show_learning_window():
    """显示学习窗口"""
    global learning_window
    if learning_window:
        learning_window.show()
        learning_window.raise_()
        learning_window.activateWindow()


def show_review_window():
    """显示复习窗口（从数据库刷新）"""
    global review_window
    if review_window:
        review_window.load_from_database()
        review_window.show()
        review_window.raise_()
        review_window.activateWindow()


# ========== 剪贴板/通知回调 ==========

class WordFetchSignals(QObject):
    """后台查词完成信号（需在主线程中接收）"""
    refresh_vocab = Signal()


_fetch_signals = None


def _on_new_word_found(words):
    """剪贴板发现新单词 - 在主线程触发"""
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
    """通知窗口点击单词 - 在主线程触发（添加到当前选中词汇本）"""
    from database import Database
    db = Database("data/wordpet.db")

    # 添加到当前词汇库窗口选中的词汇本
    notebook_id = 1
    if vocab_window:
        notebook_id = vocab_window._current_notebook_id

    result = db.add_word(word, notebook_id)
    if result == "exists":
        QTimer.singleShot(0, lambda: QMessageBox.information(
            vocab_window, "提示", f"'{word}' 已在词汇库中"
        ))
    elif result == "success":
        # 立即刷新词汇库
        if vocab_window:
            vocab_window._load_words()

        # 后台查词典补全信息（不阻塞 UI）
        runnable = FetchWordRunnable(db, word)
        QThreadPool.globalInstance().start(runnable)


def _get_bubble_pos():
    """获取通知气泡位置（右下角）"""
    screen = QApplication.primaryScreen()
    screen_size = screen.size()
    x = screen_size.width() - 310
    y = screen_size.height() - 280
    return QPoint(x, y)


class FetchWordRunnable(QRunnable):
    """后台查词典任务（非 UI 线程）"""

    class _Signals(QObject):
        done = Signal(str)  # 传回 word

    def __init__(self, db, word):
        super().__init__()
        self.db = db
        self.word = word
        self.signals = FetchWordRunnable._Signals()
        # 连接到主线程的刷新
        self.signals.done.connect(_on_fetch_done)

    def run(self):
        try:
            from dict_api import query_word
            result = query_word(self.word)
            if result:
                self.db.update_word_details(self.word, result)
        except Exception as e:
            print(f"[FetchWord] 查词失败: {e}")
        finally:
            # 通过信号在主线程刷新 UI
            self.signals.done.emit(self.word)


def _on_fetch_done(word):
    """查词完成后在主线程刷新词汇库"""
    if vocab_window:
        vocab_window._load_words()


# ==================== 初始化 ====================
def init_app():
    """初始化应用"""
    global pet_window, vocab_window, learning_window, review_window, notification_window

    # 确保目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("asset/image", exist_ok=True)

    # 创建数据库
    from database import Database
    db = Database("data/wordpet.db")

    # 创建各窗口
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

    # 连接桌宠点击信号
    pet_window.clicked.connect(toggle_vocab)

    # 连接通知气泡单词点击信号
    notification_window.word_clicked.connect(_on_word_clicked)

    # 创建剪贴板监控（只需传 db_path）
    clipboard_monitor = ClipboardMonitor("data/wordpet.db")
    clipboard_monitor.new_word_found.connect(_on_new_word_found)

    # 监控状态变化时同步更新哈基米状态
    def _on_monitor_toggled():
        if pet_window:
            pet_window.on_monitor_toggled()
    clipboard_monitor.toggled.connect(_on_monitor_toggled)

    # 保持引用，防止被 GC
    pet_window._clipboard_monitor = clipboard_monitor

    # ★ 把学习/复习窗口直接注入到 vocab_window，确保按钮能打开窗口
    vocab_window.set_learning_window(learning_window)
    vocab_window.set_review_window(review_window)

    # ★ 同样注入到 pet_window（右键菜单也能直接打开）
    pet_window._learning_window = learning_window
    pet_window._review_window = review_window

    # 显示桌宠
    pet_window.show()

    return True


# ==================== 程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 防止关闭词汇库时退出程序

    if init_app():
        sys.exit(app.exec())
