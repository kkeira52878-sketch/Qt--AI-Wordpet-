# WordPet - AI 英语单词学习桌宠

## 1. 项目概述

### 项目名称
**WordPet** - AI 英语单词学习桌宠

### 项目目标
创建一个以桌宠形态呈现的英语单词学习助手，用户通过点击桌宠打开词汇库，支持划词添加、剪贴板监控、复习等功能。

### 核心功能
1. **桌宠形态** - 悬浮桌面的小宠物，点击切换词汇库显示
2. **词汇库** - 管理已添加的单词，支持搜索、删除、清空
3. **学习模式** - 显示单词本中的单词，支持发音播放
4. **复习本** - 存储需要复习的单词，支持定期复习
5. **剪贴板监控** - 后台监控剪贴板，自动识别英文单词
6. **全局热键** - Ctrl+Shift+P 开启/暂停剪贴板监控

---

## 2. 技术架构

### 技术栈
- **框架**: PySide6 (Qt for Python)
- **语言**: Python 3.x
- **UI框架**: 多窗口架构（桌宠 + 词汇库 + 学习/复习）
- **数据库**: SQLite（持久化词汇库）
- **API**: Free Dictionary API（免费，无需密钥）
- **语音**: gTTS（英文发音）
- **热键**: pynput（全局键盘监听）

### 项目结构
```
version2/
├── src/
│   ├── main.py                 # 程序入口
│   ├── pet_window.py          # 桌宠窗口（置顶圆形）
│   ├── vocabulary_window.py   # 词汇库窗口
│   ├── learning_window.py     # 学习窗口
│   ├── review_window.py       # 复习窗口
│   ├── database.py            # SQLite 数据库
│   ├── dict_api.py            # 词典 API
│   ├── notification_window.py # 通知气泡
│   ├── clipboard_monitor.py   # 剪贴板监控
│   └── hotkey_manager.py      # 全局热键
├── data/
│   └── wordpet.db              # SQLite 数据库
├── asset/
│   └── image/                  # 桌宠图片资源
├── requirements.txt            # Python 依赖
└── SPEC.md                     # 本规格文档
```

---

## 3. 功能详细规格

### 3.1 桌宠窗口 (PetWindow)

**窗口属性:**
- 尺寸: 100x100 像素
- 无边框、透明背景、圆形
- 始终置顶: `Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint`

**交互行为:**
- 单击: 切换词汇库窗口显示/隐藏
- 右键: 显示上下文菜单（显示词汇库、学习、复习、退出）
- 拖拽: 移动桌宠位置

### 3.2 词汇库窗口 (VocabularyWindow)

**功能:**
- 显示所有已添加的单词
- 搜索单词
- 添加/删除/清空单词
- 打开学习窗口和复习窗口

**交互:**
- 无框可拖拽
- 点击单词显示详情
- 右上角关闭按钮

### 3.3 学习窗口 (LearningWindow)

**功能:**
- 选择单词本（日常词汇/学术词汇）
- 显示单词信息（英文、音标、释义、例句、记忆方法）
- 播放英文发音
- Pass 按钮将单词加入复习本

### 3.4 复习窗口 (ReviewWindow)

**功能:**
- 显示复习本中的单词
- 播放英文发音
- Pass 按钮显示下一个
- 清空复习本

### 3.5 剪贴板监控

**功能:**
- 后台监控剪贴板变化
- 识别英文单词（正则匹配）
- 发现新单词时弹出通知气泡
- 点击气泡中的单词添加到词汇库

**控制:**
- Ctrl+Shift+P: 开启监控
- ESC: 暂停监控

### 3.6 通知气泡 (NotificationWindow)

**功能:**
- 显示检测到的单词列表
- 点击单词添加到词汇库
- 20秒后自动消失

---

## 4. 数据模型

### words 表
| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER | 主键自增 |
| word | TEXT | 单词原文 |
| phonetic | TEXT | 音标 |
| definition | TEXT | 释义 |
| example | TEXT | 例句 |
| mastery | INTEGER | 掌握程度 (0-5) |
| is_favorite | BOOLEAN | 是否收藏 |
| created_at | DATETIME | 添加时间 |
| last_reviewed | DATETIME | 最后复习时间 |
| next_review | DATETIME | 下次复习时间 |

---

## 5. 验收标准

### MVP
- [x] 桌宠窗口显示和交互
- [x] 词汇库窗口显示和管理单词
- [x] 学习窗口选择单词本和学习单词
- [x] 复习窗口显示复习本
- [x] 数据库持久化

### 进阶功能
- [ ] 剪贴板监控自动添加单词
- [ ] 全局热键控制
- [ ] 通知气泡显示

---

## 6. 整合说明

### 整合来源
- **version1**: 单词数据（words.py）、学习/复习UI、gTTS发音
- **my version**: 桌宠架构、数据库、剪贴板监控、热键管理、通知窗口

### 整合策略
1. 以 my version 的桌宠架构为主体
2. 将 version1 的学习/复习界面作为独立窗口
3. 统一使用 PySide6

---

*文档版本: 2.0*
*最后更新: 2026-05-28*