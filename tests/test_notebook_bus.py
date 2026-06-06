# -*- coding: utf-8 -*-
"""
跨词本同步总线验收 — 3 个用例覆盖 _NotebookBus 基础行为 + 窗窗 subscribe 行为。
"""
import os

# Qt 必须在 import 任何 QWidget 类之前初始化 (offscreen 模式, 不需显示器)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import main
from main import _NotebookBus


# ── 辅助: 进程级一次性 QApplication (pytest scope 共享) ──


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ── 用例 1: subscribe + publish 链路通, listener 收到 nb_id ──


def test_notebook_bus_subscribe_publish():
    bus = _NotebookBus()
    received = []
    bus.subscribe(lambda nb_id: received.append(nb_id))
    bus.publish(42)
    bus.publish(7)
    assert received == [42, 7], f"listener 应收到 [42, 7], 实际 {received}"


# ── 用例 2: 多个 subscriber 都能收到 ──


def test_notebook_bus_multiple_subscribers():
    bus = _NotebookBus()
    r1, r2, r3 = [], [], []
    bus.subscribe(lambda nb_id: r1.append(nb_id))
    bus.subscribe(lambda nb_id: r2.append(nb_id * 2))
    bus.subscribe(lambda nb_id: r3.append(nb_id + 100))
    bus.publish(5)
    assert r1 == [5], f"subscriber1 应收 [5], 实际 {r1}"
    assert r2 == [10], f"subscriber2 应收 [10], 实际 {r2}"
    assert r3 == [105], f"subscriber3 应收 [105], 实际 {r3}"


# ── 用例 3: LearningWindow.__init__ 末尾 subscribe, bus._subscribers +1 ──


def test_learning_window_subscribes_on_init(qapp, monkeypatch):
    """LearningWindow 构造后, 注入的 fake_bus._subscribers 列表应多 1 项 (它自己)。"""
    fake_bus = _NotebookBus()
    # 替换 main.notebook_bus 为 fake (monkeypatch 自动还原)
    monkeypatch.setattr(main, "notebook_bus", fake_bus)

    # 确认 mock 生效: publish 不应触发原始 bus 的 listener
    from learning_window import LearningWindow
    original_count = len(fake_bus._subscribers)

    lw = LearningWindow()  # __init__ 末尾会调 fake_bus.subscribe(...)
    assert len(fake_bus._subscribers) == original_count + 1, \
        f"LearningWindow.__init__ 应调用 1 次 fake_bus.subscribe"

    # 验证 publisher → listener 链路 (LearningWindow._on_notebook_changed_from_bus)
    # 这里只验 mock bus 被订阅, 不调 listener (那需要可见的弹窗 + 词本数据)
    lw.deleteLater()


# ── 附加: ReviewWindow 也对称 subscribe (Q5=a) ──


def test_review_window_subscribes_on_init(qapp, monkeypatch):
    fake_bus = _NotebookBus()
    monkeypatch.setattr(main, "notebook_bus", fake_bus)

    from review_window import ReviewWindow
    original_count = len(fake_bus._subscribers)

    rw = ReviewWindow()
    assert len(fake_bus._subscribers) == original_count + 1, \
        f"ReviewWindow.__init__ 应调用 1 次 fake_bus.subscribe (Q5=a 跟 learning 对称)"

    rw.deleteLater()
