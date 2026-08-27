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
