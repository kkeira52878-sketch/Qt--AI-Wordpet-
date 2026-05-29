# -*- coding: utf-8 -*-
"""
词典 API 模块 - 使用 Free Dictionary API（无需密钥）
"""

import requests


def query_word(word: str) -> dict:
    """
    查询单词信息。
    返回包含 phonetic/definition/example 的字典，
    失败时返回空字典 {}（不抛出异常）。
    """
    if not word or not word.strip():
        return {}

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.strip()}"
        response = requests.get(url, timeout=8)

        if response.status_code != 200:
            print(f"[Dict] 查询 '{word}' 失败: HTTP {response.status_code}")
            return {}

        data = response.json()
        if not data or not isinstance(data, list):
            return {}

        entry = data[0]

        # ——— 音标 ———
        phonetic = ""
        phonetics = entry.get("phonetics", [])
        for p in phonetics:
            if p.get("text"):
                phonetic = p["text"]
                break
        # 兜底：顶层 phonetic 字段
        if not phonetic:
            phonetic = entry.get("phonetic", "")

        # ——— 释义 ———
        definition = ""
        example = ""
        meanings = entry.get("meanings", [])
        for meaning in meanings:
            defs = meaning.get("definitions", [])
            if defs:
                definition = defs[0].get("definition", "")
                example = defs[0].get("example", "")
                break

        return {
            "phonetic": phonetic,
            "definition": definition,
            "example": example,
        }

    except requests.exceptions.Timeout:
        print(f"[Dict] 查询 '{word}' 超时")
        return {}
    except Exception as e:
        print(f"[Dict] 查询 '{word}' 出错: {e}")
        return {}
