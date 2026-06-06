# -*- coding: utf-8 -*-
"""
桌宠窗口 - WordPet 核心入口
哈基米形态：常态 / 哈气 / 聆听 三种状态切换
右键菜单 + 拖拽支持 + 曼波音效
"""

import os
from PySide6.QtWidgets import QWidget, QMenu, QApplication, QLabel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QRegion


class PetWindow(QWidget):
    """桌宠窗口 - 哈基米形态，支持三状态切换"""

    clicked = Signal()  # 单击信号

    # 状态常量
    STATE_NORMAL = "normal"
    STATE_YAWN = "yawn"
    STATE_LISTEN = "listen"

    def __init__(self):
        super().__init__()
        self._press_position = QPoint()
        self._drag_position = QPoint()
        self._is_dragging = False

        # 挂载外部引用（由 main.py 写入）
        self._clipboard_monitor = None
        self._learning_window = None
        self._review_window = None

        # 状态机
        self._state = self.STATE_NORMAL
        self._monitoring = False  # 是否处于剪贴板监控模式
        self._mouse_pressed = False  # 鼠标是否按下

        # 窗口属性
        self.setFixedSize(100, 100)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 圆形遮罩（保持圆形外观）
        self.setMask(QRegion(0, 0, 100, 100, QRegion.Ellipse))

        # 移到右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - 130, screen.bottom() - 160)

        # 加载图片资源
        self._pixmaps = {}
        self._load_pixmaps()

        # 图片显示标签
        self._image_label = QLabel(self)
        self._image_label.setFixedSize(100, 100)
        self._image_label.setScaledContents(True)
        self._update_image()

    # ---------- 图片资源 ----------

    def _asset_dir(self):
        """获取资源目录"""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "asset")

    def _load_pixmaps(self):
        """加载三张哈基米图片"""
        image_dir = os.path.join(self._asset_dir(), "image")
        paths = {
            self.STATE_NORMAL: os.path.join(image_dir, "hakimi_normal.png"),
            self.STATE_YAWN: os.path.join(image_dir, "hakimi_yawn.png"),
            self.STATE_LISTEN: os.path.join(image_dir, "hakimi_listen.png"),
        }
        for state, path in paths.items():
            if os.path.exists(path):
                self._pixmaps[state] = QPixmap(path)
            else:
                print(f"[PetWindow] 图片不存在: {path}")
                self._pixmaps[state] = None

    def _update_image(self):
        """根据当前状态更新显示的图片"""
        pixmap = self._pixmaps.get(self._state)
        if pixmap and not pixmap.isNull():
            # 裁剪为圆形
            rounded = QPixmap(100, 100)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 100, 100)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, 100, 100, pixmap)
            painter.end()
            self._image_label.setPixmap(rounded)
        else:
            # 降级：绘制默认圆形
            self._draw_fallback()

    def _draw_fallback(self):
        """图片加载失败时的降级绘制"""
        fallback = QPixmap(100, 100)
        fallback.fill(Qt.transparent)
        painter = QPainter(fallback)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, 100, 100)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), Qt.transparent)

        monitoring = self._clipboard_monitor and self._clipboard_monitor.is_enabled
        if monitoring:
            body_color = Qt.GlobalColor.green
        else:
            body_color = Qt.GlobalColor.blue

        painter.setBrush(body_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 96, 96)
        painter.end()
        self._image_label.setPixmap(fallback)

    def _set_state(self, state):
        """切换状态并重绘"""
        if self._state != state:
            self._state = state
            self._update_image()

    # ---------- 音效 ----------

    def _play_manbo(self):
        """播放曼波音效"""
        audio_path = os.path.join(self._asset_dir(), "audio", "manbo.mp3")
        if not os.path.exists(audio_path):
            return
        try:
            # 使用 MCI API 静默播放（与项目现有音频播放方式一致）
            import ctypes
            from ctypes import wintypes
            mciSendStringW = ctypes.windll.winmm.mciSendStringW
            alias = "manbo_sound"
            mciSendStringW(f'open "{audio_path}" type mpegvideo alias {alias}', None, 0, None)
            mciSendStringW(f'play {alias} from 0', None, 0, None)
        except Exception as e:
            print(f"[PetWindow] 播放曼波音效失败: {e}")

    # ---------- 鼠标事件 ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            dx, dy = pos.x() - 50, pos.y() - 50
            if dx * dx + dy * dy <= 50 * 50:
                self._is_dragging = False
                self._press_position = event.globalPosition().toPoint()
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._mouse_pressed = True

                # 点击时：切换为哈气状态 + 播放曼波音效
                self._set_state(self.STATE_YAWN)
                self._play_manbo()

                event.accept()
            else:
                event.ignore()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if not self._drag_position.isNull():
                self._is_dragging = True
                self.move(event.globalPosition().toPoint() - self._drag_position)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_pressed = False
            release_pos = event.globalPosition().toPoint()
            manhattan_length = (release_pos - self._press_position).manhattanLength()
            if manhattan_length < 5 and not self._is_dragging:
                self.clicked.emit()

            self._drag_position = QPoint()
            self._is_dragging = False

            # 松开鼠标：如果正在监控剪贴板，切回聆听状态；否则切回常态
            monitoring = self._clipboard_monitor and self._clipboard_monitor.is_enabled
            if monitoring:
                self._set_state(self.STATE_LISTEN)
            else:
                self._set_state(self.STATE_NORMAL)

    # ---------- 监控状态切换 ----------

    def on_monitor_toggled(self):
        """剪贴板监控状态改变时调用（由 main.py 或右键菜单调用）"""
        monitoring = self._clipboard_monitor and self._clipboard_monitor.is_enabled
        if monitoring:
            # 开启监控 → 切换到聆听状态
            self._set_state(self.STATE_LISTEN)
        else:
            # 关闭监控 → 切换到常态
            self._set_state(self.STATE_NORMAL)

    # ---------- 右键菜单 ----------

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Microsoft YaHei', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #2c3e50;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
            QMenu::separator { height: 1px; background: #eee; margin: 4px 0; }
        """)

        menu.addAction("📚 词汇库", self._toggle_vocab)
        menu.addAction("📖 记单词", self._open_flashcard)
        menu.addSeparator()

        monitoring = self._clipboard_monitor and self._clipboard_monitor.is_enabled
        if monitoring:
            menu.addAction("🟢 监控中（点击关闭）", self._toggle_monitor)
        else:
            menu.addAction("⚪ 监控关闭（点击开启）", self._toggle_monitor)

        menu.addSeparator()
        menu.addAction("❌ 退出", QApplication.quit)
        menu.exec(pos)

    def _toggle_vocab(self):
        self.clicked.emit()

    def _open_learning(self):
        if self._learning_window:
            self._learning_window.load_from_database()
            self._learning_window.show()
            self._learning_window.raise_()
            self._learning_window.activateWindow()
        else:
            try:
                from main import learning_window
                if learning_window:
                    learning_window.load_from_database()
                    learning_window.show()
                    learning_window.raise_()
                    learning_window.activateWindow()
            except Exception:
                pass

    def _open_review(self):
        if self._review_window:
            self._review_window.load_from_database()
            self._review_window.show()
            self._review_window.raise_()
            self._review_window.activateWindow()
        else:
            try:
                from main import show_review_window
                show_review_window()
            except Exception:
                pass

    def _open_flashcard(self):
        """3b-2: 右键菜单'📖 记单词'入口 — 走 B1 闪卡流, 注入 vocabulary 当前词本 ID"""
        # 取 vocabulary 窗口的当前词本 ID (main.py 注入 self._vocabulary_window)
        nb_id = 1
        if self._vocabulary_window:
            nb_id = self._vocabulary_window._current_notebook_id or 1

        if self._learning_window:
            self._learning_window.load_from_database(nb_id)
            self._learning_window.show()
            self._learning_window.raise_()
            self._learning_window.activateWindow()
        else:
            try:
                from main import learning_window as _lw
                if _lw:
                    _lw.load_from_database(nb_id)
                    _lw.show()
                    _lw.raise_()
                    _lw.activateWindow()
            except Exception:
                pass

    def _toggle_monitor(self):
        """右键菜单切换剪贴板监控"""
        if self._clipboard_monitor:
            self._clipboard_monitor.toggle()
            self.on_monitor_toggled()  # 同步更新哈基米状态
