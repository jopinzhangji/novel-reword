"""G1c 屏外线批处理（trigger=batch）：批次触发 + 幂等空转 + 上限钳制（SDD D10 §4/§8）。"""
from pathlib import Path

from src.runtime.character_growth import (
    GrowthGuard,
    apply_off_screen_batch,
    load_growth_state,
    scan_off_screen_batch_for_all,
)
from src.runtime.file_sync import (
    append_off_screen_thread,
    load_off_screen_threads,
    off_screen_threads_yaml_path,
)
from src.runtime.memory_layers import THREAD_OFF_SCREEN
from src.runtime.storage import MemoryStorage


def _tmp_root(tmp_path) -> Path:
    return tmp_path / "novel"


def _add(root: Path, cid: str, summary: str, turn_index: int):
    append_off_screen_thread(
        root, cid, {"thread": THREAD_OFF_SCREEN, "summary": summary, "turn_index": turn_index}
    )


def test_batch_no_pending_is_noop(tmp_path):
    """无待处理条目 → 直接空转（不扫成长、不写盘），返回空。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    fired, audit, consumed = apply_off_screen_batch(st, root, character_id="li")
    assert fired == [] and audit == [] and consumed == []
    assert off_screen_threads_yaml_path(root, "li").is_file() is False


def test_batch_triggers_evolution_and_marks_consumed(tmp_path):
    """有累积未消费条目 → 批次触发演进（跨条目平衡批内保持），条目标 consumed 后幂等。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    # 先损耗后收益 → 批内跨条目平衡放行 resource_gain
    _add(root, "li", "行商失败，损失惨重", 60)
    _add(root, "li", "此后寻得一株灵草，得到回报", 61)
    fired, _, consumed = apply_off_screen_batch(st, root, character_id="li", guard=GrowthGuard())
    assert "resource_gain" in fired
    assert len(consumed) == 2
    state = load_growth_state("li", root)
    assert state.resource_state.get("增益") == 1
    assert state.resource_state.get("损耗") == 1
    # 消费标记已落盘：下次批次 → 空转（幂等，满足"无新戏不空转"）
    back = load_off_screen_threads(root, "li")
    assert len(back) == 2 and all(b.get("consumed") for b in back)
    fired2, _, consumed2 = apply_off_screen_batch(st, root, character_id="li", guard=GrowthGuard())
    assert fired2 == [] and consumed2 == []
    assert state.resource_state.get("增益") == 1  # 未重复涨


def test_batch_max_entries_chunks(tmp_path):
    """max_entries 上限只处理一"批"，剩余留待下轮，跨批最终全部消费。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    for i in range(5):
        _add(root, "zhao", f"运货{i}，折损些许", 100 + i)
    _, _, consumed1 = apply_off_screen_batch(st, root, character_id="zhao", max_entries=2)
    assert len(consumed1) == 2
    # 未消费的仍存在
    assert sum(1 for e in load_off_screen_threads(root, "zhao") if not e.get("consumed")) == 3
    _, _, consumed2 = apply_off_screen_batch(st, root, character_id="zhao")
    assert len(consumed2) == 3  # 剩余一起消费


def test_scan_batch_for_all_skips_empty_characters(tmp_path):
    """扫描入口对无内容的角色自动空转；有内容角色批次演进。"""
    root = _tmp_root(tmp_path)
    st = MemoryStorage()
    # 仅 li 有屏外条目，wang 无 → wang 空转
    _add(root, "li", "在巡查中遭埋伏，重伤濒死", 40)
    _add(root, "li", "被一名蒙面人仗义出手救走，欠下人情", 41)
    fired_by_char, audit = scan_off_screen_batch_for_all(
        st, root, character_ids=["li", "wang"], guard=GrowthGuard()
    )
    assert "wang" not in fired_by_char
    assert "near_death" in fired_by_char["li"]
    assert "rescue_debt" in fired_by_char["li"]
    assert load_growth_state("li", root).power_state.get("突破契机") == 1
    # 已全部消费，二扫为空 → 空转
    fired2, _ = scan_off_screen_batch_for_all(st, root, character_ids=["li", "wang"], guard=GrowthGuard())
    assert fired2 == {}