# -*- coding: utf-8 -*-
"""
WordCardRenderer 单测 — 4 个用例, 不依赖 QApplication / PySide6。
"""
import pytest

from word_card_renderer import (
    render_word_card,
    parse_meanings,
    serialize_meanings,
    get_first_definition,
    search_in_json,
)


def _make_word_data(**overrides) -> dict:
    """构造一个最小可用的 word_data dict, 测试时只关心被覆盖的字段。"""
    base = {
        "english": "serendipity",
        "pronunciation": "/ˌserənˈdɪpəti/",
        "meanings": [],
        "memory": "",
        "mastery": 0,
        "lookup_status": "success",
        "count_meanings": 0,
    }
    base.update(overrides)
    return base


# ── 用例 1: success + 2 个 meanings, mode='detail' 渲染全部 ───────


def test_success_two_meanings_detail_renders_all():
    meanings = [
        {
            "partOfSpeech": "noun",
            "definitions": [
                {"definition": "意外发现美好事物的运气", "example": "Pure serendipity."},
                {"definition": "天赐之福", "example": ""},
            ],
        },
        {
            "partOfSpeech": "verb",
            "definitions": [
                {"definition": "意外发现 (罕用)", "example": "I serendipitied a cafe."},
            ],
        },
    ]
    wd = _make_word_data(
        english="serendipity",
        meanings=meanings,
        count_meanings=2,
        mastery=3,
    )
    result = render_word_card(wd, mode="detail")

    # detail 模式: 不显示折叠按钮, 不显示重新查词
    assert result.show_fold_button is False
    assert result.show_retry_button is False

    # HTML 必须包含 2 个 partOfSpeech
    assert "noun" in result.html
    assert "verb" in result.html

    # 必须包含 3 个 definition 文本 (2 + 1)
    assert "意外发现美好事物的运气" in result.html
    assert "天赐之福" in result.html
    assert "意外发现 (罕用)" in result.html

    # 例句存在时必须出现
    assert "Pure serendipity." in result.html
    # verb 那条 definition 没 example, 不应强行渲染 e.g. 块
    # (无法直接断言"没有", 但可以确认 verb 的定义文本存在)

    # 掌握度
    assert "★★★" in result.html


# ── 用例 2: failed 状态渲染占位 ──────────────────────────────────


def test_failed_status_renders_placeholder():
    wd = _make_word_data(
        english="asdfghjkl",
        meanings=[],
        count_meanings=0,
        lookup_status="failed",
    )
    result = render_word_card(wd, mode="detail")

    # detail 模式 + failed: 显示重新查词按钮, 不显示折叠
    assert result.show_retry_button is True
    assert result.show_fold_button is False

    # 必须包含失败占位文案
    assert "⚠️" in result.html
    assert "词典查询失败" in result.html
    assert "asdfghjkl" in result.html  # 单词名出现


def test_failed_status_learning_mode_no_retry_button():
    """learning / review 模式下 failed 状态不显示重新查词按钮。"""
    wd = _make_word_data(
        english="asdfghjkl",
        meanings=[],
        count_meanings=0,
        lookup_status="failed",
    )
    result = render_word_card(wd, mode="learning")
    assert result.show_retry_button is False
    assert result.show_fold_button is False
    assert "⚠️" in result.html


# ── 用例 3: never 状态渲染占位 ──────────────────────────────────


def test_never_status_renders_pending_placeholder():
    wd = _make_word_data(
        english="newword",
        meanings=[],
        count_meanings=0,
        lookup_status="never",
    )
    result = render_word_card(wd, mode="learning")
    assert result.show_retry_button is False
    assert result.show_fold_button is False
    assert "⏳" in result.html
    assert "词典数据收集中" in result.html
    assert "newword" in result.html


# ── 用例 4: count_meanings=1 时不显示折叠按钮 ─────────────────────


def test_count_meanings_one_no_fold_button():
    """learning / review 模式下, 即使 mode=learning, count_meanings=1 不显示折叠按钮。"""
    meanings = [
        {
            "partOfSpeech": "noun",
            "definitions": [
                {"definition": "苹果", "example": "I eat an apple."},
            ],
        }
    ]
    wd = _make_word_data(
        english="apple",
        meanings=meanings,
        count_meanings=1,  # 关键: 只有 1 个 meaning
        lookup_status="success",
    )
    result = render_word_card(wd, mode="learning")
    assert result.show_fold_button is False, "count=1 不应有折叠按钮"

    # 但 HTML 仍应包含首个 meaning
    assert "苹果" in result.html
    assert "noun" in result.html

    result2 = render_word_card(wd, mode="review")
    assert result2.show_fold_button is False


# ── 补充: helpers 行为 ──────────────────────────────────────────


def test_parse_meanings_resilience():
    """parse_meanings 对各种异常输入都返回 [], 不抛。"""
    assert parse_meanings(None) == []
    assert parse_meanings("") == []
    assert parse_meanings("not json") == []
    assert parse_meanings('{"not": "list"}') == []  # 顶层不是 list → []
    assert parse_meanings('[]') == []
    # 正常 list
    assert parse_meanings('[{"a": 1}]') == [{"a": 1}]


def test_search_in_json_substring():
    """query 必须已 lowercase (契约: query_lower)。"""
    json_str = '[{"definitions": [{"definition": "苹果", "example": "apple"}]}]'
    assert search_in_json(json_str, "苹果") is True
    assert search_in_json(json_str, "apple") is True  # 小写查询命中
    assert search_in_json(json_str, "Apple") is False  # 未小写 → 命中失败 (由调用方负责 lower)
    assert search_in_json(json_str, "不存在") is False
    assert search_in_json(None, "x") is False
    assert search_in_json("", "x") is False


def test_get_first_definition_skips_empty():
    meanings = [
        {"definitions": [{"definition": ""}, {"definition": ""}]},
        {"definitions": [{"definition": "first valid"}]},
    ]
    assert get_first_definition(meanings) == "first valid"


def test_round_trip_serialize_parse():
    """serialize → parse 应保持数据一致。"""
    meanings = [{"partOfSpeech": "noun", "definitions": [{"definition": "测试", "example": "test"}]}]
    s = serialize_meanings(meanings)
    assert "测试" in s  # UTF-8 可读
    assert parse_meanings(s) == meanings
