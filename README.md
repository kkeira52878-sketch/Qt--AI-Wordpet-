# WordPet

> AI 英语单词学习桌宠 — Python / PySide6 桌面应用

桌宠形态悬浮在桌面，点击打开词汇库；划词或剪贴板监控自动添加生词；内置 B1 闪卡流、复习本、AI 词典查询、gTTS 发音。

---

## 截图/运行形态

桌宠 (`pet_window.py`) 是一个 100x100 像素的置顶圆形窗口, 默认停在屏幕右下角。点击 → 切换为"哈气"表情 + 播放 `manbo.mp3` 音效; 双击/右键 → 词汇库; 拖动 → 移动位置。

---

## 核心功能

| # | 功能 | 状态 |
|---|---|---|
| 1 | **桌宠形态** — 100x100 圆形, 3 态 (normal/yawn/listen), 始终置顶 | ✅ |
| 2 | **词汇库** — 增删改查 + 搜索 + 多词本 | ✅ |
| 3 | **学习模式 (B1 闪卡)** — Pass/Forget 流, 自动 gTTS 发音 | ✅ |
| 4 | **复习本** — 按 mastery 调度, 空状态有 4 行统计 | ✅ |
| 5 | **剪贴板监控** — 正则识别英文单词, 通知气泡 + 一键加入 | ✅ |
| 6 | **全局热键** — `Ctrl+Shift+P` 开启/暂停监控 | ✅ |
| 7 | **AI 词典查询** — Free Dictionary API, 自动写入 `meanings_json` | ✅ |
| 8 | **音频缓存** — gTTS 生成结果存 `audio_cache` 字段 | ✅ |

---

## 技术栈

- **Python 3.x** + **PySide6** (Qt for Python)
- **SQLite** (持久化词汇库 + 自动迁移)
- **gTTS** (英文 TTS) + Windows MCI (静音播放)
- **Free Dictionary API** (免 key)
- **pynput** (全局热键)

依赖列表见 `requirements.txt`。

---

## 快速开始

```powershell
# 1. 创建虚拟环境 (可选, 推荐)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 跑应用
cd src
python main.py
```

桌宠会出现在屏幕右下角。**首次运行**会自动建 `data/wordpet.db` + 导入内置词本。目前为了测试提交的版本中留有默认的单词本

---

## 运行测试

```powershell
# 全量 pytest (22 个用例, 约 1s)
python -m pytest tests/ -v

# 手动 smoke 工具 (不在 pytest 收集里)
python tests/smoke_test.py
```

测试覆盖:
- `test_flashcard.py` (4) — B1 闪卡流, Pass/Forget 状态机
- `test_migration.py` (5) — 数据库迁移 + 幂等性
- `test_notebook_bus.py` (4) — 跨词本同步总线
- `test_word_card_renderer.py` (9) — 单词卡片渲染 (detail/flashcard 双模式)

---

## 项目结构

```
WordPet/
├── src/
│   ├── main.py                 # 程序入口 + 剪贴板回调 + 跨词本总线
│   ├── pet_window.py           # 桌宠 (100x100, 3 态: normal/yawn/listen)
│   ├── vocabulary_window.py    # 词汇库 (搜索/增删/多词本)
│   ├── learning_window.py      # B1 闪卡 (Pass/Forget 状态机)
│   ├── review_window.py        # 复习本 (mastery 调度)
│   ├── notification_window.py  # 通知气泡 (剪贴板识别到生词时弹出)
│   ├── clipboard_monitor.py    # 剪贴板后台监控
│   ├── hotkey_manager.py       # Ctrl+Shift+P 全局热键
│   ├── database.py             # SQLite + 自动迁移 (meanings_json / lookup_status / audio_cache)
│   ├── dict_api.py             # Free Dictionary API
│   ├── audio_player.py         # gTTS 合成 + MCI 静默播放 (统一接口)
│   ├── word_card_renderer.py   # 单词卡片渲染 (detail/flashcard 双模式)
│   └── words.py                # 内置词库数据
├── tests/                      # 22 个 pytest 用例 + 1 个 manual smoke
├── asset/
│   ├── image/                  # 桌宠图片 (hakimi_*.png × 3)
│   └── audio/                  # 桌宠音效 (manbo.mp3)
├── data/                       # 运行时生成 (wordpet.db, gitignore)
├── requirements.txt
├── SPEC.md                     # 详细规格
└── README.md
```

---

## 桌宠状态机 (3 态)

| 状态 | 触发条件 | 视觉 |
|---|---|---|
| `STATE_NORMAL` | 启动 / 监控关闭 / 松开鼠标 | `hakimi_normal.png` |
| `STATE_YAWN` | 单击桌宠 (圆内) | `hakimi_yawn.png` + 播 `manbo.mp3` |
| `STATE_LISTEN` | 剪贴板监控开启 | `hakimi_listen.png` |

---

## 已知限制 / 后续路线

- **桌宠是静态图片切换**, 没有帧动画 (每个状态只有 1 张 PNG, 不循环)
- **窗口管理**: 词汇库/学习/复习窗口是独立 QWidget, 互不阻塞
- **音频播放**: 仅 Windows 上走 MCI, 其他平台降级 `os.startfile`

---

## 致谢

- 词典数据: [Free Dictionary API](https://dictionaryapi.dev/)
- 语音合成: [gTTS](https://gtts.readthedocs.io/)
- 桌宠形象: 哈基米 (PNG from internal assets，AI生成)

---

*文档版本: 1.1.0*
*最后更新: 2026-06-06*
