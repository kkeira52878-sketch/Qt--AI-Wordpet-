# -*- coding: utf-8 -*-
"""
通知气泡窗口 - 显示剪贴板检测到的英文单词
20秒后自动消失，点击单词可添加到词汇库
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class NotificationWindow(QWidget):
    """通知气泡 - 显示检测到的单词，点击添加到词汇库"""

    word_clicked = Signal(str)   # 用户点击了某个单词
    closed = Signal()            # 气泡关闭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(290, 260)
        self.setObjectName("bubble")

        self.setStyleSheet("""
            QWidget#bubble {
                background-color: #F0FFF4;
                border-radius: 14px;
                border: 2px solid #50C878;
            }
            QLabel#title {
                font-weight: bold;
                font-size: 13px;
                color: #1a7a3c;
            }
            QLabel#hint {
                font-size: 11px;
                color: #888;
                padding: 2px 0 4px 0;
            }
            QListWidget {
                border: none;
                background: transparent;
            }
            QListWidget::item {
                padding: 7px 10px;
                border-radius: 7px;
                color: #2c3e50;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background-color: #D4F0E4;
                color: #1a5c30;
            }
            QPushButton#close_btn {
                background: transparent;
                color: #aaa;
                font-size: 16px;
                border: none;
                padding: 0;
            }
            QPushButton#close_btn:hover {
                color: #e74c3c;
            }
        """)

        # ——— 布局 ———
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)

        # 标题栏
        title_layout = QHBoxLayout()
        self._title_label = QLabel("🔍 检测到英文单词")
        self._title_label.setObjectName("title")
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self._close_window)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        # 提示文字
        self._hint_label = QLabel("点击单词即可添加到词汇库")
        self._hint_label.setObjectName("hint")
        main_layout.addWidget(self._hint_label)

        # 单词列表
        self._word_list = QListWidget()
        self._word_list.setFont(QFont("Consolas", 12))
        self._word_list.itemClicked.connect(self._on_word_clicked)
        main_layout.addWidget(self._word_list)

        # 自动消失计时器
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._close_window)

    # ---------- 公开方法 ----------

    def _show_notification(self, title: str, hint: str, words: list, pos):
        """显示通知气泡"""
        # 重置计时器
        self._hide_timer.stop()

        # 更新内容
        self._title_label.setText(title)
        self._hint_label.setText(hint)
        self._word_list.clear()

        for word in words:
            item = QListWidgetItem(f"📝  {word}")
            item.setData(Qt.UserRole, word)
            self._word_list.addItem(item)

        # 显示并定位
        self.move(pos)
        self.show()
        self.raise_()

        # 20 秒后自动消失
        self._hide_timer.start(20000)

    # ---------- 内部槽 ----------

    def _on_word_clicked(self, item: QListWidgetItem):
        """用户点击了某个单词"""
        word = item.data(Qt.UserRole)
        if not word:
            return

        # 标记已添加
        item.setText(f"✅  {word}  (已添加)")
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)  # 禁用，防止重复点击

        self.word_clicked.emit(word)

        # 1.5 秒后移除该条目
        QTimer.singleShot(1500, lambda: self._remove_item(item))

    def _remove_item(self, item: QListWidgetItem):
        """移除列表中的单词条目"""
        row = self._word_list.row(item)
        if row >= 0:
            self._word_list.takeItem(row)
        # 若全部添加完毕，自动关闭
        if self._word_list.count() == 0:
            QTimer.singleShot(500, self._close_window)

    def _close_window(self):
        """关闭气泡"""
        self._hide_timer.stop()
        self.hide()
        self.closed.emit()
