# -*- coding: utf-8 -*-
"""
全局热键管理 - 监听 Ctrl+Shift+P 切换剪贴板监控
使用独立线程，避免阻塞主 UI 线程
"""

from PySide6.QtCore import Signal, QObject, QTimer
import threading


class HotkeyListener(QObject):
    """全局热键监听器 - Ctrl+Shift+P 触发 toggle 信号"""

    hotkey_detected = Signal()   # 每次触发热键时发出（由调用方决定行为）

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[HotkeyListener] 已启动，Ctrl+Shift+P 切换剪贴板监控")

    def _run(self):
        """在后台线程运行热键监听"""
        try:
            from pynput import keyboard
            hotkeys = keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+p': self._on_hotkey,
            })
            hotkeys.start()
            hotkeys.join()
        except Exception as e:
            print(f"[HotkeyListener] 启动失败: {e}")

    def _on_hotkey(self):
        """热键触发（在监听线程中调用，需转到主线程）"""
        # QTimer.singleShot(0, ...) 确保信号在主线程发出
        QTimer.singleShot(0, self.hotkey_detected.emit)
