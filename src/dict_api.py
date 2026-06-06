# -*- coding: utf-8 -*-
"""
词典 API 模块 — 使用 Free Dictionary API (无需密钥)。
返回完整 meanings 数组, 严格对齐 API 结构, 不做"取第一个 meaning"简化。
"""
import requests


def query_word(word: str) -> dict:
    """
    返回结构:
        {
            "phonetic": "/.../",                       # 取第一个非空 phonetic, 找不到再退到顶层
            "meanings": [                              # 全部 meanings, 原序保留
                {
                    "partOfSpeech": "noun",
                    "definitions": [
                        {"definition": "...", "example": "..."},
                        ...
                    ]
                },
                ...
            ]
        }

    失败 / 网络异常 / 词未收录 → 返回 {} (绝不抛异常)。
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
        if not data or not isinstance(data, list) or not data[0]:
            return {}

        entry = data[0]

        # ── 音标: 取第一个非空 phonetics[i].text; 找不到退到 entry.phonetic ──
        phonetic = ""
        for p in (entry.get("phonetics") or []):
            if isinstance(p, dict) and p.get("text"):
                phonetic = p["text"]
                break
        if not phonetic:
            phonetic = (entry.get("phonetic") or "") or ""

        # ── 完整 meanings: 原序保留, 跳过空 meaning ──
        raw_meanings = entry.get("meanings") or []
        meanings = []
        for m in raw_meanings:
            if not isinstance(m, dict):
                continue  # (c) 跳过非 dict 项
            defs_raw = m.get("definitions") or []
            defs = []
            for d in defs_raw:
                if not isinstance(d, dict):
                    continue  # (c) 跳过非 dict 子项
                defs.append({
                    "definition": (d.get("definition") or "").strip(),
                    "example":    (d.get("example") or "").strip(),
                })
            if defs:  # 跳过没有任何 definition 的空 meaning
                meanings.append({
                    "partOfSpeech": (m.get("partOfSpeech") or "").strip(),
                    "definitions": defs,
                })

        # 没有任何有效释义 → 视为未收录, 返回 {}
        if not meanings:
            return {}

        return {"phonetic": phonetic, "meanings": meanings}

    except requests.exceptions.Timeout:
        print(f"[Dict] 查询 '{word}' 超时")
        return {}
    except Exception as e:
        print(f"[Dict] 查询 '{word}' 出错: {e}")
        return {}
