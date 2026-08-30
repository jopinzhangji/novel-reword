"""
轻量关系知识图谱：节点为角色，边为角色关系，支持基础查询与 YAML 持久化。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


def relationship_graph_yaml_path(data_root: Path) -> Path:
    """与设计方案一致：`<data_root>/book/relationships/graph.yaml`。"""
    return Path(data_root) / "book" / "relationships" / "graph.yaml"


def default_graph() -> dict[str, Any]:
    """返回默认图谱结构。"""
    return {
        "version": 1,
        "nodes": [],
        "edges": [],
    }


def ensure_graph_file(path: Path) -> dict[str, Any]:
    """
    确保 graph.yaml 存在；不存在则写入默认结构并返回。
    存在时会做最小结构修正（补齐 nodes/edges）。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        graph = default_graph()
        save_graph(path, graph)
        return graph
    graph = load_graph(path)
    changed = False
    if not isinstance(graph.get("nodes"), list):
        graph["nodes"] = []
        changed = True
    if not isinstance(graph.get("edges"), list):
        graph["edges"] = []
        changed = True
    if changed:
        save_graph(path, graph)
    return graph


def load_graph(path: Path) -> dict[str, Any]:
    """读取关系图谱 YAML。文件不存在或不可解析时回退默认结构。"""
    path = Path(path)
    if not path.is_file():
        return default_graph()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return default_graph()
    if not isinstance(data, dict):
        return default_graph()
    out = default_graph()
    out.update(data)
    if not isinstance(out.get("nodes"), list):
        out["nodes"] = []
    if not isinstance(out.get("edges"), list):
        out["edges"] = []
    return out


def save_graph(path: Path, graph: dict[str, Any]) -> None:
    """写入关系图谱 YAML。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            graph,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def ensure_relationship_nodes_for_ids(
    graph: dict[str, Any],
    character_ids: Iterable[str],
    characters_config: dict[str, Any] | None = None,
) -> None:
    """为给定角色 id 补齐节点（不写回；由调用方 save_graph）。"""
    nodes = graph.setdefault("nodes", [])
    if not isinstance(nodes, list):
        graph["nodes"] = []
        nodes = graph["nodes"]
    existing = {n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")}
    id_to_name: dict[str, str] = {}
    if characters_config:
        for c in characters_config.get("characters") or []:
            if not isinstance(c, dict):
                continue
            cid = c.get("id")
            if not cid:
                continue
            id_to_name[str(cid)] = str(c.get("name") or cid)
    for cid in character_ids:
        if not cid or cid in existing:
            continue
        nodes.append({"id": cid, "name": id_to_name.get(cid, cid)})
        existing.add(cid)


def _canonical_pair(source_id: str, target_id: str) -> tuple[str, str]:
    a, b = source_id, target_id
    return (a, b) if a <= b else (b, a)


def upsert_co_presence_edge(
    graph: dict[str, Any],
    *,
    source_id: str,
    target_id: str,
    scope_id: str,
    turn_index: int,
    summary_hint: str,
) -> None:
    """
    为同场出现的角色对写入/更新一条无向风格边（固定为 source_id <= target_id）。
    若边已存在（任意语义类型），仅补充 evidence_events 与 change_log，不覆盖 type。
    """
    a, b = _canonical_pair(source_id, target_id)
    if a == b:
        return
    evidence = f"{scope_id}.turn_{turn_index:04d}"
    hint = (summary_hint or "").strip()
    reason = hint[:200] if hint else "同场出现"
    edges = graph.setdefault("edges", [])
    if not isinstance(edges, list):
        graph["edges"] = []
        edges = graph["edges"]
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("source_id") == a and edge.get("target_id") == b:
            ev = edge.setdefault("evidence_events", [])
            if isinstance(ev, list) and evidence not in ev:
                ev.append(evidence)
            cl = edge.setdefault("change_log", [])
            if isinstance(cl, list):
                cl.append(
                    {
                        "turn": turn_index,
                        "scope_id": scope_id,
                        "reason": reason,
                    }
                )
            return
    edges.append(
        {
            "source_id": a,
            "target_id": b,
            "type": "co_presence",
            "status": "active",
            "evidence_events": [evidence],
            "change_log": [
                {
                    "turn": turn_index,
                    "scope_id": scope_id,
                    "reason": reason,
                }
            ],
        }
    )


# --- 语义关系边（阶段 1a；设计文档 §4.5）---

# 场景级轻量词典：摘要命中关键词 → 整场角色对的语义关系类型（无命中保持 co_presence）。
# 顺序即优先级（冲突判定优先于温和关系，避免把一场冲突误判为日常信任）。
_SCENE_RELATION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("rival", ("冲突", "对峙", "剑拔弩张", "决裂", "反目", "对抗", "争", "争吵", "翻脸")),
    ("hate", ("仇恨", "杀意", "恨", "仇", "厌恶", "欺压")),
    ("trust", ("信任", "托付", "倚重", "信赖", "深信", "委以重任")),
    ("debt", ("救命", "报恩", "相助", "欠", "恩", "回报")),
    ("ally", ("联手", "并肩", "同盟", "结盟", "合力", "约定")),
    ("mentor", ("指点", "教导", "授业", "拜师", "收徒")),
    ("love", ("爱慕", "心动", "钟情", "倾心", "相恋")),
]


def infer_scene_relation(summary_hint: str) -> str | None:
    """
    从事件摘要推断"本场景的角色关系基调"：命中词典返回 rel_type，否则 None。
    供 sync_semantic_relations_from_event 做轻量语义落位（阶段 1a 不接 LLM，保确定性）。
    """
    text = (summary_hint or "").strip()
    if not text:
        return None
    for rel_type, keywords in _SCENE_RELATION_RULES:
        if any(k in text for k in keywords):
            return rel_type
    return None


def _find_edge(graph: dict[str, Any], a: str, b: str) -> dict[str, Any] | None:
    edges = graph.get("edges") or []
    for edge in edges:
        if isinstance(edge, dict) and edge.get("source_id") == a and edge.get("target_id") == b:
            return edge
    return None


def upsert_semantic_edge(
    graph: dict[str, Any],
    *,
    source_id: str,
    target_id: str,
    rel_type: str,
    intensity: str = "med",
    status: str = "active",
    direction: str | None = None,
    evidence_event: str,
    turn_index: int,
    scope_id: str,
    reason: str = "",
) -> dict[str, Any]:
    """
    写入/更新一条有类型的关系边（`rel_type`/`intensity`/`status`/可选 `direction`），
    记录归纳证据与 change_log。与 `upsert_co_presence_edge` 对称但带语义。
    若边已存在（任意类型），补 evidence/change_log 并按需更新语义字段；返回该边 dict。
    """
    a, b = _canonical_pair(source_id, target_id)
    reason = (reason or "").strip()[:200] or f"{rel_type}（{evidence_event}）"
    edges = graph.setdefault("edges", [])
    if not isinstance(edges, list):
        graph["edges"] = []
        edges = graph["edges"]
    edge = _find_edge(graph, a, b)
    if edge is None:
        edge = {
            "source_id": a,
            "target_id": b,
            "type": rel_type,
            "intensity": intensity,
            "status": status,
            "evidence_events": [],
            "change_log": [],
        }
        if direction:
            edge["direction"] = direction
        edges.append(edge)
    # 语义字段更新：仅当传入非空且（新类型为准）时覆盖，避免与既有高级语义冲突。
    edge["type"] = rel_type
    edge["intensity"] = intensity
    edge["status"] = status
    if direction:
        edge["direction"] = direction
    edge["last_updated_turn"] = turn_index
    ev = edge.setdefault("evidence_events", [])
    if isinstance(ev, list) and evidence_event not in ev:
        ev.append(evidence_event)
    cl = edge.setdefault("change_log", [])
    if isinstance(cl, list):
        cl.append(
            {
                "turn": turn_index,
                "scope_id": scope_id,
                "from_type": None,
                "to_type": rel_type,
                "reason": reason,
            }
        )
    return edge


def sync_semantic_relations_from_event(
    graph: dict[str, Any],
    *,
    scope_id: str,
    turn_index: int,
    present_character_ids: list[str],
    event_summary: str,
    llm_provider: Any = None,
) -> list[str]:
    """
    在共现边基础上，按场景摘要做轻量语义升级：命中词典则在"至少一条已带语义的边"上登记证据，
    其余在场对若仅 co_presence 则升级为该场景类型。返回本回合升级/登记的边标识列表。
    阶段 1a 为确定性实现（`infer_scene_relation`）；`llm_provider` 为未来 LLM 判定的保留扩展点。
    """
    present = sorted({str(x) for x in present_character_ids if x})
    if len(present) < 2:
        return []
    rel_type = infer_scene_relation(event_summary)
    if not rel_type:
        return []
    evidence = f"{scope_id}.turn_{turn_index:04d}"
    touched: list[str] = []
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            a, b = present[i], present[j]
            upsert_semantic_edge(
                graph,
                source_id=a,
                target_id=b,
                rel_type=rel_type,
                intensity="med",
                status="active",
                evidence_event=evidence,
                turn_index=turn_index,
                scope_id=scope_id,
                reason=f"{event_summary[:200] or '语义升级'}",
            )
            touched.append(f"{a}-{b}")
    return touched


def sync_relationship_graph_after_scope_turn(
    data_root: Path,
    *,
    characters_config: dict[str, Any] | None,
    scope_id: str,
    turn_index: int,
    present_character_ids: list[str],
    event_summary: str,
) -> None:
    """
    在范围事件写回后调用：为在场角色补节点，并在两两之间记录同场共现边（co_presence）。
    需要已配置 data_root；无在场角色则跳过。
    """
    root = Path(data_root)
    path = relationship_graph_yaml_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph = load_graph(path)
    present = sorted({str(x) for x in present_character_ids if x})
    if not present:
        return
    ensure_relationship_nodes_for_ids(graph, present, characters_config)
    if len(present) >= 2:
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                upsert_co_presence_edge(
                    graph,
                    source_id=present[i],
                    target_id=present[j],
                    scope_id=scope_id,
                    turn_index=turn_index,
                    summary_hint=event_summary,
                )
    save_graph(path, graph)


def get_relation(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
) -> dict[str, Any] | None:
    """
    查询 source_id -> target_id 的关系边。
    返回首条匹配边；不存在返回 None。
    """
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        if edge.get("source_id") == source_id and edge.get("target_id") == target_id:
            return edge
    return None


def get_neighbors(
    graph: dict[str, Any],
    character_id: str,
    *,
    relation_types: list[str] | None = None,
    active_only: bool = True,
    min_intensity: int | None = None,
) -> list[dict[str, Any]]:
    """
    查询某角色的关联边（入边 + 出边）。
    可按关系类型、状态、强度进行过滤。
    """
    allowed = set(relation_types or [])
    out: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source = edge.get("source_id")
        target = edge.get("target_id")
        if character_id not in (source, target):
            continue
        if allowed and edge.get("type") not in allowed:
            continue
        if active_only and str(edge.get("status") or "active") != "active":
            continue
        if min_intensity is not None:
            try:
                intensity = int(edge.get("intensity", 0))
            except (TypeError, ValueError):
                intensity = 0
            if intensity < min_intensity:
                continue
        out.append(edge)
    return out


def get_relation_change_log(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    查询两角色关系变更日志。
    日志来自 edge.change_log，按原有顺序返回尾部 limit 条。
    """
    edge = get_relation(graph, source_id, target_id)
    if not edge:
        return []
    logs = edge.get("change_log") or []
    if not isinstance(logs, list):
        return []
    if limit and limit > 0:
        return [x for x in logs if isinstance(x, dict)][-limit:]
    return [x for x in logs if isinstance(x, dict)]
