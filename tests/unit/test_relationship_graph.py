from src.runtime.relationship_graph import (
    ensure_graph_file,
    get_neighbors,
    get_relation,
    get_relation_change_log,
    infer_scene_relation,
    load_graph,
    relationship_graph_yaml_path,
    upsert_co_presence_edge,
    upsert_semantic_edge,
    sync_relationship_graph_after_scope_turn,
    sync_semantic_relations_from_event,
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


def test_infer_scene_relation_hits_and_misses():
    assert infer_scene_relation("二人剑拔弩张对峙于长街") == "rival"
    assert infer_scene_relation("她将身家性命托付于他") == "trust"
    assert infer_scene_relation("商议明日行程") is None


def test_upsert_semantic_edge_creates_typed_edge():
    graph = default_dict()
    edge = upsert_semantic_edge(
        graph,
        source_id="lin_yuan",
        target_id="su_wan",
        rel_type="trust",
        intensity="high",
        status="active",
        direction="su_wan->lin_yuan",
        evidence_event="capital.turn_0007",
        turn_index=7,
        scope_id="capital",
        reason="以性命相托",
    )
    assert edge["type"] == "trust"
    assert edge["direction"] == "su_wan->lin_yuan"
    assert get_relation(graph, "lin_yuan", "su_wan") is not None


def test_upsert_semantic_edge_accumulates_evidence_no_dup():
    graph = default_dict()
    for _ in range(2):
        upsert_semantic_edge(
            graph,
            source_id="a", target_id="b", rel_type="ally",
            evidence_event="capital.turn_0001", turn_index=1, scope_id="capital",
        )
    edge = get_relation(graph, "a", "b")
    assert len(edge["evidence_events"]) == 1  # 去重
    assert edge["type"] == "ally"


def test_sync_semantic_relations_upgrades_when_keyword_hits():
    from src.runtime.relationship_graph import default_graph
    graph = default_graph()
    touched = sync_semantic_relations_from_event(
        graph,
        scope_id="capital", turn_index=5,
        present_character_ids=["b", "a"],
        event_summary="二人针锋相对冲突升级",
    )
    assert len(touched) == 1
    edge = get_relation(graph, "a", "b")
    assert edge["type"] == "rival"
    assert "capital.turn_0005" in edge["evidence_events"]


def test_sync_semantic_relations_noop_without_keyword():
    from src.runtime.relationship_graph import default_graph
    graph = default_graph()
    touched = sync_semantic_relations_from_event(
        graph,
        scope_id="capital", turn_index=5,
        present_character_ids=["a", "b"],
        event_summary="商议明日行程",
    )
    assert touched == []
    assert get_relation(graph, "a", "b") is None  # 无命中不建边


def default_dict():
    from src.runtime.relationship_graph import default_graph
    return default_graph()
