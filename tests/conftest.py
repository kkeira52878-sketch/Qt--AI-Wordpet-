# -*- coding: utf-8 -*-
"""
pytest 配置 — 让 tests/ 能直接 import src/ 下的模块。
"""
import sys
import os

# 把 src/ 目录加入 sys.path, 便于 tests/ 内部 import src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
