"""G4 工作台测试支撑：构造临时 novel_root（确定性数据树）。"""
from pathlib import Path

import yaml


def write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_txt(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_project(tmp_path: Path, slugs=("alpha", "beta")) -> tuple[Path, dict[str, Path]]:
    """建 data/novels/{slug}/ 每部含 meta.yaml 与 config/characters.yaml。"""
    novels = Path(tmp_path) / "data" / "novels"
    roots: dict[str, Path] = {}
    for i, slug in enumerate(slugs):
        root = novels / slug
        write_yaml(
            root / "meta.yaml",
            {"title": f"小说{i}", "slug": slug, "status": "draft", "created_at": "2026-01-01", "world_name": ""},
        )
        write_yaml(
            root / "config" / "characters.yaml",
            {
                "characters": [
                    {"id": "苏A", "name": "苏A", "role": "主角", "traits": [], "goals": [], "background": ""},
                    {"id": "李B", "name": "李B", "role": "盟友", "traits": [], "goals": [], "background": ""},
                    {"id": "钱C", "name": "钱C", "role": "反派", "traits": [], "goals": [], "background": ""},
                ]
            },
        )
        roots[slug] = root
    return tmp_path, roots


def write_index(project_root: Path, slugs) -> None:
    write_yaml(
        Path(project_root) / "data" / "novels" / "index.yaml",
        {"novels": [{"slug": s, "title": s, "status": "draft", "updated_at": "2026-01-01"} for s in slugs]},
    )


def write_outline(root: Path, *, ch_refs=None, beat_refs=None) -> None:
    """写 outline.yaml + progress.yaml。ch_refs/beat_refs 可给「不存在」引用以测 missing_ref。"""
    outline = {
        "version": 1,
        "chapters": [
            {
                "id": "ch1",
                "title": "第一章",
                "dramatic_question": "能活过今夜吗",
                "beats": [
                    {"id": "b1", "intent": "开场遇袭", "suggested_scope_id": "sc1", "tags": ["动作"], "status": "active"},
                    {"id": "b2", "intent": "真相初现", "tags": ["悬疑"], "status": "planned"},
                ],
            },
            {"id": "ch2", "title": "第二章", "dramatic_question": "谁是叛徒", "beats": [{"id": "c1", "intent": "追查", "status": "planned"}]},
        ],
    }
    write_yaml(Path(root) / "book" / "outline" / "outline.yaml", outline)
    progress = {
        "version": 1,
        "chapter_id": ch_refs if ch_refs is not None else "ch1",
        "beat_id": beat_refs if beat_refs is not None else "b1",
        "turns_in_beat": 2,
    }
    write_yaml(Path(root) / "book" / "outline" / "progress.yaml", progress)


def write_graph(root: Path) -> None:
    write_yaml(
        Path(root) / "book" / "relationships" / "graph.yaml",
        {
            "version": 1,
            "nodes": [
                {"id": "苏A", "name": "苏A"},
                {"id": "李B", "name": "李B"},
                {"id": "钱C", "name": "钱C"},
                {"id": "丁D", "name": "丁D"},
            ],
            "edges": [
                {"type": "trust", "source_id": "苏A", "target_id": "李B", "status": "active", "intensity": 3,
                 "change_log": [{"turn": 1, "reason": "并肩"}], "evidence_events": []},
                {"type": "rival", "source_id": "苏A", "target_id": "钱C", "status": "active", "intensity": 2,
                 "change_log": [], "evidence_events": []},
                {"type": "old", "source_id": "李B", "target_id": "丁D", "status": "inactive", "intensity": 1,
                 "change_log": [], "evidence_events": []},
            ],
        },
    )


def write_growth(root: Path, cid: str, dims: dict, log: list) -> None:
    write_yaml(
        Path(root) / "book" / "characters" / str(cid) / "growth_state.yaml",
        {"version": 1, "character_id": cid, "updated_at": "2026-01-01", **dims,
         "transition_log": log},
    )


def write_char_event(root: Path, cid: str, turn: int, summary: str) -> None:
    write_txt(
        Path(root) / "book" / "characters" / str(cid) / "events" / f"turn_{turn:04d}.md",
        f"# 回合 {turn}\n\n{summary}\n",
    )


def write_scope_event(root: Path, scope: str, turn: int, present: list[str], summary: str) -> None:
    present_s = ",".join(present)
    write_txt(
        Path(root) / "book" / "events" / scope / "events" / f"turn_{turn:04d}.md",
        f"# 回合 {turn}\n\nscope_id: '{scope}'\ntime: ''\nplace: ''\npresent_characters: {present_s}\n\n"
        f"## 摘要\n\n{summary}\n\n",
    )


def write_off_screen(root: Path, cid: str, entries: list) -> None:
    write_yaml(
        Path(root) / "book" / "characters" / str(cid) / "threads" / "off_screen.yaml",
        {"version": 1, "entries": entries},
    )