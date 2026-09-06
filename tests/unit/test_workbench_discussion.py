"""§6.9 设定讨论/synopsis 读口单测（纯 service，确定性、无 LLM）。"""
from pathlib import Path

from src.workbench.discussion import discussion_snapshot
from src.workbench.common import novel_meta

from tests.unit.workbench_support import make_project, write_yaml


def _build(root: Path) -> None:
    write_yaml(
        root / "config" / "world.yaml",
        {
            "world": {"name": "火星殖民", "era": "近未来", "rules": "燃料守恒"},
            "scopes": [{"id": "sc1", "name": "殖民站", "description": "主场景"}],
        },
    )
    write_yaml(
        root / "config" / "setting_research_output.yaml",
        {
            "version": 1,
            "genre": "科幻",
            "world_brief": "近未来火星殖民恒星际文明的权力与技术阶段。",
            "power_system": {"name": "技术阶段", "description": "曲率引擎等级", "levels": [{"id": "p0", "name": "曲率入门", "note": "第一级"}]},
            "level_system": {"name": "职级", "description": "殖民站管理层级", "chapters": [{"id": "c1", "name": "拓荒者"}, {"id": "c2", "name": "执政官"}]},
        },
    )
    write_yaml(
        root / "config" / "design_session.yaml",
        {"summary": "探讨了技术阶段与职级", "last_updated": "2026-09-06", "session_file": "s1.jsonl"},
    )
    write_yaml(
        root / "config" / "author_interaction_state.yaml",
        {"phase_state": {"phase": "DESIGN_DISCUSSION", "subphase": "power_system"}},
    )
    write_yaml(root / "meta.yaml", {"slug": "alpha", "title": "火星", "synopsis": "近未来火星殖民官场"})


def test_discussion_snapshot_full(tmp_path):
    _proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    _build(root)
    snap = discussion_snapshot(root)
    assert snap["synopsis"] == "近未来火星殖民官场"
    assert snap["phase"]["phase"] == "DESIGN_DISCUSSION"
    assert snap["phase"]["subphase"] == "power_system"
    assert snap["world"]["name"] == "火星殖民"
    assert snap["world"]["era"] == "近未来"
    assert snap["world"]["scopes"][0]["id"] == "sc1"
    # 设定方向各计数
    by_name = {s["name"]: s for s in snap["settings"]}
    assert by_name["技术阶段"]["levels_count"] == 1
    assert by_name["职级"]["chapters_count"] == 2
    assert by_name["职级"]["levels_count"] == 0
    # 具体内容（等级/章节阶梯）：供面板「以上世界模型与设定」直接呈现
    assert by_name["技术阶段"]["levels"] == [{"name": "曲率入门", "note": "第一级"}]
    assert by_name["职级"]["chapters"] == [{"name": "拓荒者", "note": ""}, {"name": "执政官", "note": ""}]
    assert snap["world_brief"] == "近未来火星殖民恒星际文明的权力与技术阶段。"
    assert snap["genre"] == "科幻"
    assert snap["discussion_summary"]["summary"] == "探讨了技术阶段与职级"
    assert snap["discussion_summary"]["last_updated"] == "2026-09-06"
    assert snap["discussion_summary"]["session_file"] == "s1.jsonl"


def test_discussion_snapshot_status_and_suggestion(tmp_path):
    _proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    _build(root)
    snap = discussion_snapshot(root)
    st = snap["status"]
    assert st["has_synopsis"] is True
    assert st["world_filled"] is True
    assert st["direction_count"] == 2
    assert st["directions_with_detail"] == 2  # 技术阶段(l1)有 level、职级有 chapters
    assert st["design_session_present"] is True
    assert snap["suggestion"]  # 非空建议存在


def test_discussion_snapshot_suggestion_guides_empty(tmp_path):
    _proj, roots = make_project(tmp_path, ("alpha",))
    snap = discussion_snapshot(roots["alpha"])  # 全空 → 建议引导填简介/世界/设定方向
    assert "简介" in snap["suggestion"] or "设定方向" in snap["suggestion"]
    assert snap["status"]["has_synopsis"] is False
    assert snap["status"]["world_filled"] is False


def test_discussion_snapshot_missing_files_safe(tmp_path):
    _proj, roots = make_project(tmp_path, ("alpha",))
    snap = discussion_snapshot(roots["alpha"])  # 无 world/setting/design/state 文件
    assert snap["synopsis"] == ""
    assert snap["phase"]["phase"] is None
    assert snap["phase"]["subphase"] is None
    assert snap["world"]["name"] == ""
    assert snap["world"]["scopes"] == []
    assert snap["settings"] == []
    assert snap["discussion_summary"]["summary"] == ""
    assert "suggestion" in snap and "status" in snap

def test_archived_discussion_detail_yaml(tmp_path):
    """归档讨论下钻：session_file 指向的 .yaml 结构化 events 被规整为 blocks。"""
    from src.workbench.discussion import archived_discussion_detail
    from tests.unit.workbench_support import write_yaml

    _proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    # 索引只存摘要 + session_file
    write_yaml(
        root / "config" / "design_session.yaml",
        {"summary": "探讨了技术阶段与职级", "last_updated": "2026-09-06",
         "session_file": "book/setting/sessions/session_20260906_120000.md"},
    )
    # 完整对话写入 book/setting/sessions/session_<ts>.yaml（与 .md 同名）
    write_yaml(
        root / "book" / "setting" / "sessions" / "session_20260906_120000.yaml",
        {
            "events": [
                {"type": "discussion", "timestamp": "T1",
                 "initial_message": "想写火星殖民官场",
                 "rounds": [{"author": "主要写政斗", "agent": "建议技术阶段分五级"},
                            {"author": "老板", "agent": "职级设拓荒者/执政官"}],
                 "extracted_directions": ["power_system", "level_system"]},
                {"type": "summary", "timestamp": "T2",
                 "world": ["火星殖民"], "scopes": ["殖民站"], "characters": [], "special": []},
            ],
            "state_snapshot": {},
        },
    )
    det = archived_discussion_detail(root)
    assert det["has_archive"] is True
    assert det["source"] == "yaml"
    assert det["summary"] == "探讨了技术阶段与职级"
    kinds = [b["kind"] for b in det["blocks"]]
    assert kinds == ["discussion", "summary"]
    d, s = det["blocks"]
    assert d["initial_message"] == "想写火星殖民官场"
    assert len(d["rounds"]) == 2
    assert d["rounds"][0] == {"author": "主要写政斗", "agent": "建议技术阶段分五级"}
    assert d["extracted_directions"] == ["power_system", "level_system"]
    assert s["world"] == ["火星殖民"]


def test_archived_discussion_detail_md_fallback(tmp_path):
    """仅存 .md（无同名 .yaml）时回退给原文 markdown。"""
    from src.workbench.discussion import archived_discussion_detail
    from tests.unit.workbench_support import write_yaml, write_txt

    _proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    write_yaml(
        root / "config" / "design_session.yaml",
        {"summary": "s", "last_updated": "2026-09-06",
         "session_file": "book/setting/sessions/session_20260906_090000.md"},
    )
    write_txt(root / "book" / "setting" / "sessions" / "session_20260906_090000.md",
              "# 设定会话\n\n## [1] discussion T\n- **作者**：\n主要写政斗\n")
    det = archived_discussion_detail(root)
    assert det["source"] == "md"
    assert "# 设定会话" in det["raw_markdown"]


def test_archived_discussion_detail_index_only_safe(tmp_path):
    """无 .yaml/.md 时只回索引摘要，不抛错。"""
    from src.workbench.discussion import archived_discussion_detail
    from tests.unit.workbench_support import write_yaml

    _proj, roots = make_project(tmp_path, ("alpha",))
    root = roots["alpha"]
    write_yaml(
        root / "config" / "design_session.yaml",
        {"summary": "s", "last_updated": "2026-09-06"},  # 无 session_file
    )
    det = archived_discussion_detail(root)
    assert det["source"] == "index_only"
    assert det["blocks"] == []
    assert det["has_archive"] is False  # 仅摘要无 file/blocks
