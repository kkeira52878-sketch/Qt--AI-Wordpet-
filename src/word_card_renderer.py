# -*- coding: utf-8 -*-
"""
单词卡片渲染器：详情弹窗 / 学习卡片 / 复习卡片共用同一个 HTML 渲染函数。

设计要点：
  1. 纯函数, 不 import PySide6, 不依赖 QApplication — 可纯单测
  2. 返回 RenderResult (html + 元数据), 不直接构造 QWidget — 让调用方自由组合
  3. 私有 helpers 内化, 不再独立 word_format.py
  4. meanings_json 字段严格对齐 Free Dictionary API 结构, 不自创字段
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal


Mode = Literal['detail', 'learning', 'review', 'flashcard']
Status = Literal['success', 'failed', 'never']


@dataclass(frozen=True)
class RenderResult:
    """渲染结果. html 不含 <html>/<body> 包装, 由调用方 setHtml 注入。"""
    html: str
    show_fold_button: bool
    show_retry_button: bool  # 仅 detail 模式 + failed 时为 True


# ── 公开 API ──────────────────────────────────────────────────────


def render_word_card(
    word_data: dict,
    mode: Mode,
    *,
    expanded: bool = False,
) -> RenderResult:
    """渲染单词卡片为 HTML 字符串 + 按钮可见性元数据.

    Args:
        word_data: {
            'english':       str,
            'pronunciation': str,
            'meanings':      list[dict],    # Free Dictionary API 结构, 严格对齐
            'memory':        str,            # 记忆方法, 不进 meanings_json
            'mastery':       int,            # 0-5, 仅 detail 模式渲染
            'lookup_status': 'success' | 'failed' | 'never',
            'count_meanings': int,           # 由调用方预算后传入 (>= 0)
        }
        mode: 'detail' → 全部展开
              'learning' | 'review' → 默认折叠第 1 个, expanded=True 时等同 detail
        expanded: 仅 learning/review 生效, True = 强制全展开

    Returns:
        RenderResult (html, show_fold_button, show_retry_button)
    """
    # ── flashcard 模式: 不显 english/phonetic/memory, 隐藏折叠和重查按钮 ──
    if mode == 'flashcard':
        status = word_data.get('lookup_status', 'success')
        if status == 'failed':
            return RenderResult(
                html='<p style="color:#DC2626; font-style:italic; margin:6px 0;'
                     'font-family:Microsoft YaHei,sans-serif;">⚠️ 释义不可用</p>',
                show_fold_button=False,
                show_retry_button=False,
            )
        if status == 'never':
            return RenderResult(
                html='<p style="color:#9CA3AF; font-style:italic; margin:6px 0;'
                     'font-family:Microsoft YaHei,sans-serif;">⏳ 释义收集中…</p>',
                show_fold_button=False,
                show_retry_button=False,
            )
        # success: 走标准全释义渲染, 复用 _render_all_meanings 但 phonetic/memory 仍隐
        # (word_data 里的 phonetic 字段由调用方控制是否填, flashcard 模式下调用方
        #  本来就不传给 phonetic_label / memory_label, 所以 HTML 不带也行)
        return RenderResult(
            html=_render_all_meanings(word_data, word_data.get('meanings') or []),
            show_fold_button=False,
            show_retry_button=False,
        )

    status: Status = word_data.get('lookup_status', 'success')  # type: ignore[assignment]

    if status == 'failed':
        html = _render_failed_placeholder(word_data, mode)
        return RenderResult(html=html, show_fold_button=False, show_retry_button=(mode == 'detail'))
    if status == 'never':
        html = _render_pending_placeholder(word_data, mode)
        return RenderResult(html=html, show_fold_button=False, show_retry_button=False)

    # status == 'success'
    meanings = word_data.get('meanings') or []
    count = word_data.get('count_meanings', len(meanings))

    if mode == 'detail' or expanded:
        html = _render_all_meanings(word_data, meanings)
        return RenderResult(html=html, show_fold_button=False, show_retry_button=False)

    # learning / review 默认折叠
    html = _render_first_meaning_with_fold(word_data, meanings)
    show_fold = count > 1  # 折叠按钮显示条件: 超过 1 个 meaning 才有展开价值
    return RenderResult(html=html, show_fold_button=show_fold, show_retry_button=False)


# ── 私有 helpers ──────────────────────────────────────────────────


def _esc(s: str) -> str:
    """HTML 实体转义, 防止 QTextEdit 解析 < > & 等特殊字符。"""
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _render_failed_placeholder(word_data: dict, mode: Mode) -> str:
    english = _esc(word_data.get('english', ''))
    if mode == 'detail':
        return (
            f'<div style="font-family:Microsoft YaHei,sans-serif; padding:8px;">'
            f'<p style="color:#DC2626; font-weight:bold; font-size:14px; margin:4px 0;">'
            f'⚠️ 词典查询失败，&quot;{english}&quot; 的释义不可用</p>'
            f'<p style="color:#6B6B8A; font-size:12px; margin:4px 0;">'
            f'点击下方"🔄 重新查词"重试, 或在 notes 中手动补全。</p>'
            f'</div>'
        )
    # learning / review: 简化占位
    return (
        f'<div style="font-family:Microsoft YaHei,sans-serif; padding:6px;">'
        f'<p style="color:#DC2626; font-style:italic; font-size:13px; margin:4px 0;">'
        f'⚠️ 词典查询失败，跳过此词</p>'
        f'</div>'
    )


def _render_pending_placeholder(word_data: dict, mode: Mode) -> str:
    english = _esc(word_data.get('english', ''))
    return (
        f'<div style="font-family:Microsoft YaHei,sans-serif; padding:6px;">'
        f'<p style="color:#9CA3AF; font-style:italic; font-size:13px; margin:4px 0;">'
        f'⏳ &quot;{english}&quot; 词典数据收集中…</p>'
        f'</div>'
    )


def _render_all_meanings(word_data: dict, meanings: List[Dict]) -> str:
    """按 partOfSpeech 分组, 每组 <ol> 列出所有 definitions, 例句小一号灰色斜体。
    顶部附 掌握度 (mastery) 信息, 仅 detail 模式用到 (mode=='detail' 时调用)。
    """
    parts: List[str] = []
    parts.append('<div style="font-family:Microsoft YaHei,sans-serif; color:#1A1A2E; font-size:13px;">')

    # 顶部掌握度
    mastery = word_data.get('mastery') or 0
    if mastery:
        parts.append(
            f'<p style="margin:4px 0 10px 0; color:#7C3AED; font-size:12px;">'
            f'⭐ 掌握度: {"★" * mastery}{"☆" * (5 - mastery)}</p>'
        )

    if not meanings:
        parts.append(
            '<p style="color:#9CA3AF; font-style:italic; margin:6px 0;">'
            '（词典已收录但无 meanings 数据, 可在 notes 中手动补全）</p>'
        )
    else:
        for meaning in meanings:
            pos = (meaning.get("partOfSpeech") or "").strip()
            if pos:
                parts.append(
                    f'<p style="margin:8px 0 2px 0;">'
                    f'<b style="color:#4A3FB5;">{_esc(pos)}</b></p>'
                )
            defs = meaning.get("definitions", []) or []
            if defs:
                parts.append('<ol style="margin:2px 0 8px 22px; padding-left:2px;">')
                for d in defs:
                    if not isinstance(d, dict):
                        continue
                    text = (d.get("definition") or "").strip()
                    example = (d.get("example") or "").strip()
                    if not text:
                        continue  # (c) 跳过缺 definition 的子项
                    parts.append(f'<li style="margin-bottom:3px;">{_esc(text)}')
                    if example:
                        parts.append(
                            f'<div style="color:#4B5563; font-style:italic;'
                            f'font-size:12px; margin:2px 0 4px 6px;">'
                            f'e.g. &quot;{_esc(example)}&quot;</div>'
                        )
                    parts.append('</li>')
                parts.append('</ol>')

    parts.append('</div>')
    return "".join(parts)


def _render_first_meaning_with_fold(word_data: dict, meanings: List[Dict]) -> str:
    """只显示 meanings[0] (若存在), 底部"显示全部 N 个释义"提示由调用方按钮承担。
    learning / review 模式专用。
    """
    if not meanings:
        # success 状态但 meanings 为空 (理论不该发生, 防御)
        return (
            '<p style="color:#9CA3AF; font-style:italic; margin:6px 0;">'
            '（该词无 meanings 数据）</p>'
        )

    m0 = meanings[0] if isinstance(meanings[0], dict) else {}
    pos = (m0.get("partOfSpeech") or "").strip()
    defs = m0.get("definitions", []) or []

    parts: List[str] = []
    parts.append('<div style="font-family:Microsoft YaHei,sans-serif; color:#1A1A2E; font-size:13px;">')

    if pos:
        parts.append(
            f'<p style="margin:4px 0 4px 0;">'
            f'<b style="color:#4A3FB5;">{_esc(pos)}</b></p>'
        )

    if defs:
        parts.append('<ol style="margin:2px 0 6px 22px; padding-left:2px;">')
        # learning/review 只显示第 1 条 definition (用户聚焦当前释义)
        d0 = defs[0] if isinstance(defs[0], dict) else {}
        text = (d0.get("definition") or "").strip()
        example = (d0.get("example") or "").strip()
        if text:
            parts.append(f'<li style="margin-bottom:3px;">{_esc(text)}')
            if example:
                parts.append(
                    f'<div style="color:#4B5563; font-style:italic;'
                    f'font-size:12px; margin:2px 0 4px 6px;">'
                    f'e.g. &quot;{_esc(example)}&quot;</div>'
                )
            parts.append('</li>')
        parts.append('</ol>')

    parts.append('</div>')
    return "".join(parts)


# ── 工具函数 (供 windows 调用方辅助) ──────────────────────────────


def parse_meanings(json_str: Optional[str]) -> List[Dict]:
    """安全解析 meanings_json 字段, 任意错误 / 空 / 顶层非 list → 返回 []。"""
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def serialize_meanings(meanings: List[Dict]) -> str:
    """释义列表序列化为 JSON 字符串 (UTF-8 可读)。"""
    if not meanings:
        return "[]"
    return json.dumps(meanings, ensure_ascii=False)


def search_in_json(json_str: Optional[str], query_lower: str) -> bool:
    """对 meanings_json 做大小写无关 substring 搜索 (避免逐条解析)。
    JSON 字符串天然包含原始释义文本, 搜索足够准确。
    """
    return bool(json_str) and query_lower in json_str.lower()


def get_first_definition(meanings: List[Dict]) -> str:
    """从 meanings 列表中取第一条非空 definition, 用于列表 snippet。"""
    for m in meanings:
        if not isinstance(m, dict):
            continue
        for d in (m.get("definitions") or []):
            if not isinstance(d, dict):
                continue
            text = (d.get("definition") or "").strip()
            if text:
                return text
    return ""
