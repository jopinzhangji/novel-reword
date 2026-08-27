from src.runtime.relationship_graph import (
    ensure_graph_file,
    get_neighbors,
    get_relation,
    get_relation_change_log,
    load_graph,
    relationship_graph_yaml_path,
    upsert_co_presence_edge,
    sync_relationship_graph_after_scope_turn,
)
from src.retrieval.relationship import format_relation_snippet


def _sample_graph() -> dict:
    return {
        "version": 1,
        "nodes": [
            {"id": "lin_yuan", "name": "林远"},
            {"id": "su_wan", "name": "苏婉"},
            {"id": "xu_mo", "name": "许默"},
        ],
        "edges": [
            {
                "source_id": "lin_yuan",
                "target_id": "su_wan",
                "type": "ally",
                "intensity": 78,
                "status": "active",
                "evidence_events": ["capital.turn_0003"],
                "change_log": [
                    {
                        "turn": 3,
                        "from_status": "neutral",
                        "to_status": "active",
                        "reason": "并肩应对宫变",
                    }
                ],
            },
            {
                "source_id": "lin_yuan",
                "target_id": "xu_mo",
                "type": "rival",
                "intensity": 45,
                "status": "inactive",
                "evidence_events": ["capital.turn_0005"],
                "change_log": [],
            },
        ],
    }


def test_ensure_graph_file_creates_default(tmp_path):
    path = tmp_path / "graph.yaml"
    graph = ensure_graph_file(path)
    assert path.is_file()
    assert graph["version"] == 1
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_get_relation_and_change_log():
    graph = _sample_graph()
    edge = get_relation(graph, "lin_yuan", "su_wan")
    assert edge is not None
    assert edge["type"] == "ally"
    logs = get_relation_change_log(graph, "lin_yuan", "su_wan")
    assert len(logs) == 1
    assert "宫变" in logs[0]["reason"]


def test_get_neighbors_filters():
    graph = _sample_graph()
    active = get_neighbors(graph, "lin_yuan", active_only=True)
    assert len(active) == 1
    assert active[0]["target_id"] == "su_wan"
    rivals = get_neighbors(graph, "lin_yuan", relation_types=["rival"], active_only=False)
    assert len(rivals) == 1
    assert rivals[0]["target_id"] == "xu_mo"
    strong = get_neighbors(graph, "lin_yuan", active_only=False, min_intensity=70)
    assert len(strong) == 1
    assert strong[0]["target_id"] == "su_wan"


def test_load_graph_invalid_file_fallbacks(tmp_path):
    path = tmp_path / "graph.yaml"
    path.write_text("not: [valid", encoding="utf-8")
    graph = load_graph(path)
    assert graph["version"] == 1
    assert graph["edges"] == []


def test_format_relation_snippet():
    graph = _sample_graph()
    text = format_relation_snippet(graph, "lin_yuan", limit=5)
    assert "lin_yuan->su_wan:ally" in text
    assert "lin_yuan->xu_mo:rival" in text


def test_relationship_graph_yaml_path(tmp_path):
    root = tmp_path / "novel"
    p = relationship_graph_yaml_path(root)
    assert p == root / "book" / "relationships" / "graph.yaml"


def test_upsert_co_presence_keeps_existing_edge_type():
    graph = _sample_graph()
    upsert_co_presence_edge(
        graph,
        source_id="lin_yuan",
        target_id="su_wan",
        scope_id="capital",
        turn_index=9,
        summary_hint="再次同场",
    )
    edge = get_relation(graph, "lin_yuan", "su_wan")
    assert edge["type"] == "ally"
    assert "capital.turn_0009" in edge["evidence_events"]
    assert edge["change_log"][-1].get("scope_id") == "capital"


def test_sync_relationship_graph_after_scope_turn(tmp_path):
    dr = tmp_path / "novel"
    sync_relationship_graph_after_scope_turn(
        dr,
        characters_config={
            "characters": [
                {"id": "a", "name": "甲"},
                {"id": "b", "name": "乙"},
            ]
        },
        scope_id="capital",
        turn_index=1,
        present_character_ids=["b", "a"],
        event_summary="商议",
    )
    gpath = relationship_graph_yaml_path(dr)
    assert gpath.is_file()
    g2 = load_graph(gpath)
    ids = {n["id"] for n in g2["nodes"] if isinstance(n, dict)}
    assert ids == {"a", "b"}
    edge = get_relation(g2, "a", "b")
    assert edge is not None
    assert edge["type"] == "co_presence"
    assert "capital.turn_0001" in edge["evidence_events"]
