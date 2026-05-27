# -*- coding: utf-8 -*-
"""
英语单词学习 App - 主程序
使用 PyQt6 构建
"""

import sys
import random
import time
import os
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette, QMovie
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# 导入单词数据
from words import ALL_VOCABULARY_BOOKS, VOCABULARY_BOOK_1, VOCABULARY_BOOK_2

# gTTS用于语音合成（可选，需要网络）
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class LoadingScreen(QWidget):
    """加载界面 - 显示'请输入文本'，停留1秒"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        """设置加载界面UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2C3E50;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 显示文字
        self.label = QLabel("请输入文本", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #ECF0F1;
                font-size: 32px;
                font-weight: bold;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
        """)

        layout.addWidget(self.label)
        self.setLayout(layout)


class HomeScreen(QWidget):
    """首页 - 显示四个功能图标"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 600)
        self.setup_ui()

    def setup_ui(self):
        """设置首页UI - 按照布局要求排列四个图标
        
        布局要求：
        - 图标4在页面最左上角，比3更靠上，图标呈长方形，跟3一样宽，但是没有那么长
        - 图标3在页面最上方中间，较小，水平的长方形
        - 图标1、2最大，一样大，并列排布
        """
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
            }
            QPushButton {
                color: white;
                border: none;
                border-radius: 12px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
        """)

        # 使用绝对定位实现布局
        # 图标4：个人主页 - 左上角位置，比3更靠上，较小，长方形
        # 与3一样宽(约200px)，但更短
        self.btn_profile = QPushButton("个人主页", self)
        self.btn_profile.setGeometry(15, 10, 80, 25)
        self.btn_profile.setStyleSheet("""
            QPushButton {
                background-color: #9B59B6;
                font-size: 11px;
            }
        """)

        # 图标3：更换单词本 - 顶部中间，水平长方形
        self.btn_change_book = QPushButton("更换单词本", self)
        self.btn_change_book.setGeometry(100, 45, 200, 35)
        self.btn_change_book.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                font-size: 14px;
            }
        """)

        # 图标1：学习新单词 - 左侧，最大
        self.btn_learning = QPushButton("学习新单词", self)
        self.btn_learning.setGeometry(30, 150, 165, 180)
        self.btn_learning.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                font-size: 20px;
            }
        """)

        # 图标2：复习本 - 右侧，最大，与1一样大
        self.btn_review = QPushButton("复习本", self)
        self.btn_review.setGeometry(205, 150, 165, 180)
        self.btn_review.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                font-size: 20px;
            }
        """)

        # 连接信号 - parent()是stacked widget, parent().parent()才是MainWindow
        self.btn_learning.clicked.connect(lambda: self.parent().parent().show_learning_screen())
        self.btn_review.clicked.connect(lambda: self.parent().parent().show_review_screen())
        self.btn_change_book.clicked.connect(lambda: self.parent().parent().show_change_book_screen())
        self.btn_profile.clicked.connect(lambda: self.parent().parent().show_profile_screen())


class LearningScreen(QWidget):
    """学习新单词界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_words = []  # 当前单词本中的单词
        self.current_index = 0
        self.current_book_name = None
        self.audio_player = None
        self.setup_ui()

    def setup_ui(self):
        """设置学习界面UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 8px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            #btn_pass {
                background-color: #3498DB;
            }
            #btn_pass:hover {
                background-color: #2980B9;
            }
            #btn_play_audio {
                background-color: #E74C3C;
                font-size: 14px;
                padding: 8px;
            }
            #btn_play_audio:hover {
                background-color: #C0392B;
            }
            #btn_back {
                background-color: #95A5A6;
                font-size: 14px;
                padding: 8px;
            }
            #btn_back:hover {
                background-color: #7F8C8D;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 返回按钮
        self.btn_back = QPushButton("返回首页", self)
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(lambda: self.parent().parent().show_home_screen())

        # 单词显示区域
        self.word_area = QVBoxLayout()
        self.word_area.setSpacing(10)

        # 图片显示（如果有的话，在单词上方）
        self.image_label = QLabel("", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(200, 150)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                background-color: white;
            }
        """)

        # 发音按钮
        self.btn_play_audio = QPushButton("🔊 播放发音", self)
        self.btn_play_audio.setObjectName("btn_play_audio")
        self.btn_play_audio.clicked.connect(self.play_current_audio)

        # 单词（英文）
        self.english_label = QLabel("", self)
        self.english_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.english_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)

        # 音标
        self.pronunciation_label = QLabel("", self)
        self.pronunciation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pronunciation_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #7F8C8D;
            }
        """)

        # 中文释义
        self.chinese_label = QLabel("", self)
        self.chinese_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chinese_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #34495E;
            }
        """)

        # 例句
        self.example_label = QLabel("", self)
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7F8C8D;
                font-style: italic;
            }
        """)

        # 记忆方法
        self.memory_label = QLabel("", self)
        self.memory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.memory_label.setWordWrap(True)
        self.memory_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #BDC3C7;
            }
        """)

        self.word_area.addWidget(self.image_label)
        self.word_area.addWidget(self.btn_play_audio)
        self.word_area.addWidget(self.english_label)
        self.word_area.addWidget(self.pronunciation_label)
        self.word_area.addWidget(self.chinese_label)
        self.word_area.addWidget(self.example_label)
        self.word_area.addWidget(self.memory_label)

        # Pass 按钮（测试用）
        self.btn_pass = QPushButton("Pass (加入复习本)", self)
        self.btn_pass.setObjectName("btn_pass")
        self.btn_pass.clicked.connect(self.on_pass_clicked)

        main_layout.addWidget(self.btn_back)
        main_layout.addLayout(self.word_area)
        main_layout.addWidget(self.btn_pass)

        self.setLayout(main_layout)

        # 初始化音频播放器
        self.init_audio_player()

    def init_audio_player(self):
        """初始化音频播放器"""
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

    def play_current_audio(self):
        """播放当前单词的发音"""
        if self.current_index < len(self.current_words):
            word = self.current_words[self.current_index]
            self.play_audio(word["english"])

    def play_audio(self, text):
        """播放指定文本的发音"""
        if not GTTS_AVAILABLE:
            return

        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            # 生成语音
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(temp_path)

            # 播放
            self.audio_player.setSource(QUrl.fromLocalFile(temp_path))
            self.audio_player.play()

            # 播放完成后删除临时文件
            def cleanup():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            QTimer.singleShot(3000, cleanup)

        except Exception as e:
            print(f"播放音频失败: {e}")

    def load_book(self, book_name):
        """加载指定单词本"""
        self.current_book_name = book_name
        for book in ALL_VOCABULARY_BOOKS:
            if book["name"] == book_name:
                self.current_words = book["words"].copy()
                random.shuffle(self.current_words)
                self.current_index = 0
                self.show_current_word()
                return

    def show_current_word(self):
        """显示当前单词"""
        if self.current_index < len(self.current_words):
            word = self.current_words[self.current_index]
            self.english_label.setText(word["english"])
            self.pronunciation_label.setText(word["pronunciation"])
            self.chinese_label.setText(word["chinese"])
            self.example_label.setText(word["example"])
            self.memory_label.setText(f"💡 {word['memory']}")

            # 显示图片（如果有的话）
            if word.get("image"):
                pixmap = QPixmap(word["image"])
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
            else:
                self.image_label.clear()

            # 自动播放发音
            self.play_audio(word["english"])
        else:
            self.english_label.setText("🎉 学习完成！")
            self.pronunciation_label.setText("")
            self.chinese_label.setText("恭喜你完成了本单词本的学习")
            self.example_label.setText("")
            self.memory_label.setText("")
            self.image_label.clear()

    def on_pass_clicked(self):
        """Pass按钮点击处理 - 加入复习本并显示下一个"""
        if self.current_index < len(self.current_words):
            word = self.current_words[self.current_index]
            self.parent().parent().add_to_review(word)
            self.current_index += 1
            self.show_current_word()


class ReviewScreen(QWidget):
    """复习本界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = 0
        self.setup_ui()

    def setup_ui(self):
        """设置复习界面UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 8px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            #btn_play_audio {
                background-color: #E74C3C;
                font-size: 14px;
                padding: 8px;
            }
            #btn_play_audio:hover {
                background-color: #C0392B;
            }
            #btn_back {
                background-color: #95A5A6;
                font-size: 14px;
                padding: 8px;
            }
            #btn_back:hover {
                background-color: #7F8C8D;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 返回按钮
        self.btn_back = QPushButton("返回首页", self)
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(lambda: self.parent().parent().show_home_screen())

        # 单词显示区域
        self.word_area = QVBoxLayout()
        self.word_area.setSpacing(10)

        # 图片显示（如果有的话，在单词上方）
        self.image_label = QLabel("", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(200, 150)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                background-color: white;
            }
        """)

        # 发音按钮
        self.btn_play_audio = QPushButton("🔊 播放发音", self)
        self.btn_play_audio.setObjectName("btn_play_audio")
        self.btn_play_audio.clicked.connect(self.play_current_audio)

        # 单词（英文）
        self.english_label = QLabel("", self)
        self.english_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.english_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)

        # 音标
        self.pronunciation_label = QLabel("", self)
        self.pronunciation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pronunciation_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #7F8C8D;
            }
        """)

        # 中文释义
        self.chinese_label = QLabel("", self)
        self.chinese_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chinese_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #34495E;
            }
        """)

        # 例句
        self.example_label = QLabel("", self)
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7F8C8D;
                font-style: italic;
            }
        """)

        # 记忆方法
        self.memory_label = QLabel("", self)
        self.memory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.memory_label.setWordWrap(True)
        self.memory_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #BDC3C7;
            }
        """)

        self.word_area.addWidget(self.image_label)
        self.word_area.addWidget(self.btn_play_audio)
        self.word_area.addWidget(self.english_label)
        self.word_area.addWidget(self.pronunciation_label)
        self.word_area.addWidget(self.chinese_label)
        self.word_area.addWidget(self.example_label)
        self.word_area.addWidget(self.memory_label)

        # Pass 按钮（复习用，不需要加入复习本）
        self.btn_pass = QPushButton("Pass (下一个)", self)
        self.btn_pass.clicked.connect(self.on_pass_clicked)

        main_layout.addWidget(self.btn_back)
        main_layout.addLayout(self.word_area)
        main_layout.addWidget(self.btn_pass)

        self.setLayout(main_layout)

        # 初始化音频播放器
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

    def play_current_audio(self):
        """播放当前单词的发音"""
        if hasattr(self, 'review_words') and self.current_index < len(self.review_words):
            word = self.review_words[self.current_index]
            self.play_audio(word["english"])

    def play_audio(self, text):
        """播放指定文本的发音"""
        if not GTTS_AVAILABLE:
            return

        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(temp_path)

            self.audio_player.setSource(QUrl.fromLocalFile(temp_path))
            self.audio_player.play()

            def cleanup():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            QTimer.singleShot(3000, cleanup)

        except Exception as e:
            print(f"播放音频失败: {e}")

    def load_review_words(self, review_words):
        """加载复习本单词"""
        self.review_words = review_words
        self.current_index = 0
        if review_words:
            self.show_current_word()
        else:
            self.english_label.setText("📚 复习本为空")
            self.pronunciation_label.setText("")
            self.chinese_label.setText("快去学习新单词吧！")
            self.example_label.setText("")
            self.memory_label.setText("")
            self.image_label.clear()

    def show_current_word(self):
        """显示当前单词"""
        if self.current_index < len(self.review_words):
            word = self.review_words[self.current_index]
            self.english_label.setText(word["english"])
            self.pronunciation_label.setText(word["pronunciation"])
            self.chinese_label.setText(word["chinese"])
            self.example_label.setText(word["example"])
            self.memory_label.setText(f"💡 {word['memory']}")

            # 显示图片（如果有的话）
            if word.get("image"):
                pixmap = QPixmap(word["image"])
                if not pixmap.isNull():
                    self.image_label.setPixmap(pixmap.scaled(
                        self.image_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
            else:
                self.image_label.clear()
        else:
            self.english_label.setText("🎉 复习完成！")
            self.pronunciation_label.setText("")
            self.chinese_label.setText("恭喜你完成了本轮复习")
            self.example_label.setText("")
            self.memory_label.setText("")
            self.image_label.clear()

    def on_pass_clicked(self):
        """Pass按钮点击处理 - 显示下一个"""
        if self.current_index < len(self.review_words):
            self.current_index += 1
            self.show_current_word()


class ChangeBookScreen(QWidget):
    """更换单词本界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置更换单词本界面UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 10px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 18px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:selected {
                background-color: #27AE60;
            }
            #btn_back {
                background-color: #95A5A6;
                font-size: 14px;
                padding: 8px;
            }
            #btn_back:hover {
                background-color: #7F8C8D;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 返回按钮
        self.btn_back = QPushButton("返回首页", self)
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(lambda: self.parent().parent().show_home_screen())

        # 标题
        self.title_label = QLabel("选择单词本", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)

        # 单词本列表
        self.books_layout = QVBoxLayout()
        self.books_layout.setSpacing(15)

        # 当前选择的单词本
        self.current_book_label = QLabel("", self)
        self.current_book_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_book_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7F8C8D;
            }
        """)

        main_layout.addWidget(self.btn_back)
        main_layout.addWidget(self.title_label)
        main_layout.addLayout(self.books_layout)
        main_layout.addWidget(self.current_book_label)

        self.setLayout(main_layout)

    def update_books(self, current_book=None):
        """更新单词本列表"""
        # 清除旧的按钮
        while self.books_layout.count():
            item = self.books_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新的按钮
        for book in ALL_VOCABULARY_BOOKS:
            btn = QPushButton(f"📚 {book['name']} ({len(book['words'])}个单词)", self)
            btn.clicked.connect(lambda checked, b=book: self.on_book_selected(b))
            if current_book and book["name"] == current_book:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                        font-size: 18px;
                        padding: 15px;
                    }
                """)
            self.books_layout.addWidget(btn)

        if current_book:
            self.current_book_label.setText(f"当前选择: {current_book}")
        else:
            self.current_book_label.setText("请选择一个单词本开始学习")

    def on_book_selected(self, book):
        """单词本被选中"""
        self.parent().parent().select_vocabulary_book(book["name"])
        self.parent().parent().show_learning_screen()


class ProfileScreen(QWidget):
    """个人主页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置个人主页UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 10px;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 18px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            #btn_back {
                background-color: #95A5A6;
                font-size: 14px;
                padding: 8px;
            }
            #btn_back:hover {
                background-color: #7F8C8D;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 返回按钮
        self.btn_back = QPushButton("返回首页", self)
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(lambda: self.parent().parent().show_home_screen())

        # 标题
        self.title_label = QLabel("个人主页", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2C3E50;
            }
        """)

        # 功能按钮
        self.btn_login = QPushButton("登录账号", self)
        self.btn_login.clicked.connect(self.show_not_implemented)

        self.btn_switch = QPushButton("切换账号", self)
        self.btn_switch.clicked.connect(self.show_not_implemented)

        main_layout.addWidget(self.btn_back)
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.btn_login)
        main_layout.addWidget(self.btn_switch)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def show_not_implemented(self):
        """显示'暂未实现该功能'"""
        QMessageBox.information(
            self,
            "提示",
            "暂未实现该功能，敬请期待",
            QMessageBox.StandardButton.Ok
        )


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.current_book = None  # 当前选择的单词本
        self.review_words = []    # 复习本单词列表
        self.setup_ui()

    def setup_ui(self):
        """设置主窗口UI"""
        self.setFixedSize(400, 600)
        self.setWindowTitle("英语单词学习")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECF0F1;
            }
        """)

        # 创建堆栈窗口
        self.stack = QStackedWidget()

        # 创建各个页面
        self.loading_screen = LoadingScreen()
        self.home_screen = HomeScreen()
        self.learning_screen = LearningScreen()
        self.review_screen = ReviewScreen()
        self.change_book_screen = ChangeBookScreen()
        self.profile_screen = ProfileScreen()

        # 添加到堆栈
        self.stack.addWidget(self.loading_screen)      # 0
        self.stack.addWidget(self.home_screen)          # 1
        self.stack.addWidget(self.learning_screen)      # 2
        self.stack.addWidget(self.review_screen)        # 3
        self.stack.addWidget(self.change_book_screen)    # 4
        self.stack.addWidget(self.profile_screen)        # 5

        self.setCentralWidget(self.stack)

        # 显示加载界面，1秒后跳转首页
        self.stack.setCurrentIndex(0)
        QTimer.singleShot(1000, self.show_home_screen)

    def show_home_screen(self):
        """显示首页"""
        self.stack.setCurrentIndex(1)

    def show_learning_screen(self):
        """显示学习界面"""
        # 如果没有选择单词本，先进入选择单词本界面
        if self.current_book is None:
            self.change_book_screen.update_books()
            self.stack.setCurrentIndex(4)
            return

        self.learning_screen.load_book(self.current_book)
        self.stack.setCurrentIndex(2)

    def show_review_screen(self):
        """显示复习界面"""
        self.review_screen.load_review_words(self.review_words)
        self.stack.setCurrentIndex(3)

    def show_change_book_screen(self):
        """显示更换单词本界面"""
        self.change_book_screen.update_books(self.current_book)
        self.stack.setCurrentIndex(4)

    def show_profile_screen(self):
        """显示个人主页"""
        self.stack.setCurrentIndex(5)

    def select_vocabulary_book(self, book_name):
        """选择单词本"""
        self.current_book = book_name

    def add_to_review(self, word):
        """将单词加入复习本"""
        # 检查是否已经在复习本中
        for w in self.review_words:
            if w["id"] == word["id"]:
                return
        self.review_words.append(word)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())