# -*- coding: utf-8 -*-
"""
剪贴板监控 - 后台监控剪贴板，识别英文单词
Ctrl+Shift+P 切换开关（由 hotkey_manager 驱动）
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QObject
import re

from database import Database

# 匹配纯英文单词（含缩略形式，最短3个字母避免噪声）
WORD_PATTERN = r"\b[a-zA-Z]{3,}(?:'[a-zA-Z]+)?\b"


class ClipboardMonitor(QObject):
    """剪贴板监控器 - 监听剪贴板变化并提取新英文单词"""

    new_word_found = Signal(list)   # 发现新单词时发出，携带单词列表
    toggled = Signal()              # 监控开关切换时发出

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.is_enabled = False
        self.db = Database(db_path)
        self._last_text = ""

        # 绑定系统剪贴板
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)

    # ---------- 内部槽 ----------

    def _on_clipboard_changed(self):
        """剪贴板内容变化回调"""
        if not self.is_enabled:
            return

        text = self.clipboard.text().strip()
        if not text or text == self._last_text:
            return
        self._last_text = text

        words = self._extract_words(text)
        # 过滤已在数据库中的单词
        new_words = [w for w in words if not self.db.get_one_word(w)]
        # 去重（保持顺序）
        seen = set()
        unique_new = []
        for w in new_words:
            if w not in seen:
                seen.add(w)
                unique_new.append(w)

        if unique_new:
            self.new_word_found.emit(unique_new)

    def _extract_words(self, text: str) -> list:
        """从文本中提取英文单词列表（小写）"""
        return re.findall(WORD_PATTERN, text.lower())

    # ---------- 公开方法 ----------

    def toggle(self):
        """切换监控开关"""
        if self.is_enabled:
            self.disable()
        else:
            self.enable()

    def enable(self):
        """开启监控"""
        self.is_enabled = True
        self._last_text = ""
        print("[ClipboardMonitor] 监控已开启")
        self.toggled.emit()

    def disable(self):
        """关闭监控"""
        self.is_enabled = False
        print("[ClipboardMonitor] 监控已关闭")
        self.toggled.emit()
