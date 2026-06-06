# -*- coding: utf-8 -*-
"""
统一音频模块：gTTS 合成 + MCI 静默播放。

3 处调用方（vocabulary 详情 / learning 卡片 / review 卡片）共享同一份代码，
避免之前 learning_window.py / review_window.py 重复实现 _mci_play / _safe_unlink / _mci_counter。
"""

import os
import platform
import tempfile
import ctypes
import threading
from typing import Optional

from PySide6.QtCore import QTimer


# ── 进程内 alias 计数器（避免同时播放多段音频时 alias 冲突） ──
_mci_counter = 0
_mci_counter_lock = threading.Lock()


def _next_alias() -> str:
    global _mci_counter
    with _mci_counter_lock:
        _mci_counter += 1
        return f"wp_audio_{_mci_counter}"


def _safe_unlink(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


# ── 公开 API ──────────────────────────────────────────────────────


def synthesize_audio_bytes(text: str) -> Optional[bytes]:
    """gTTS 生成 MP3 bytes。失败 / 空文本 / 异常 → 返回 None（绝不抛）。"""
    if not text or not text.strip():
        return None
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        try:
            tts.save(tmp_path)
            with open(tmp_path, "rb") as f:
                data = f.read()
            return data if data else None
        finally:
            _safe_unlink(tmp_path)
    except Exception as e:
        print(f"[Audio] gTTS 生成失败: {e}")
        return None


def play_audio_bytes(audio_bytes: bytes, parent=None) -> None:
    """MCI 静默播放 MP3 bytes（来自 DB cache 场景）。写临时文件后调 MCI。"""
    if not audio_bytes:
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
            f.write(audio_bytes)
    except Exception as e:
        print(f"[Audio] 写临时文件失败: {e}")
        return
    play_audio_path(tmp_path, parent)


def play_audio_path(filepath: str, parent=None) -> None:
    """MCI 静默播放磁盘 MP3 文件（gTTS 已写好临时文件场景，避免重复 IO）。"""
    if not filepath or not os.path.exists(filepath):
        return

    if platform.system() != "Windows":
        # 非 Windows 降级
        try:
            os.startfile(filepath)  # type: ignore[attr-defined]
        except Exception:
            pass
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
        return

    try:
        winmm = ctypes.windll.winmm
        alias = _next_alias()
        winmm.mciSendStringW(f'open "{filepath}" alias {alias}', None, 0, None)
        winmm.mciSendStringW(f'play {alias}', None, 0, None)

        def _cleanup():
            try:
                winmm.mciSendStringW(f'close {alias}', None, 0, None)
            except Exception:
                pass
            _safe_unlink(filepath)

        if parent:
            QTimer.singleShot(8000, _cleanup)
        else:
            threading.Timer(8.0, _cleanup).start()
    except Exception as e:
        print(f"[Audio] MCI 播放失败: {e}")
        try:
            os.startfile(filepath)  # type: ignore[attr-defined]
        except Exception:
            pass
        if parent:
            QTimer.singleShot(5000, lambda: _safe_unlink(filepath))
