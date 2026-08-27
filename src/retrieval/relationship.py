"""
关系图谱检索层：封装 relationship_graph 的查询，并提供 prompt 友好格式化。
"""
from __future__ import annotations

from typing import Any

from src.runtime.relationship_graph import (
    get_neighbors as _get_neighbors,
    get_relation as _get_relation,
    get_relation_change_log as _get_relation_change_log,
)


def get_relation(graph: dict[str, Any], source_id: str, target_id: str) -> dict[str, Any] | None:
    """代理 runtime 层关系查询函数。"""
    return _get_relation(graph, source_id, target_id)


def get_neighbors(
    graph: dict[str, Any],
    character_id: str,
    *,
    relation_types: list[str] | None = None,
    active_only: bool = True,
    min_intensity: int | None = None,
) -> list[dict[str, Any]]:
    """代理 runtime 层邻居查询函数。"""
    return _get_neighbors(
        graph,
        character_id,
        relation_types=relation_types,
        active_only=active_only,
        min_intensity=min_intensity,
    )


def get_relation_change_log(
    graph: dict[str, Any],
    source_id: str,
    target_id: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """代理 runtime 层关系变更日志查询函数。"""
    return _get_relation_change_log(graph, source_id, target_id, limit=limit)


def format_relation_snippet(
    graph: dict[str, Any],
    character_id: str,
    *,
    limit: int = 8,
) -> str:
    """
    将角色关系边格式化为简短文本，供后续注入 prompt。
    """
    neighbors = get_neighbors(graph, character_id, active_only=False)
    if not neighbors:
        return ""
    rows: list[str] = []
    for edge in neighbors[: max(1, limit)]:
        source = edge.get("source_id") or "?"
        target = edge.get("target_id") or "?"
        rel_type = edge.get("type") or "unknown"
        status = edge.get("status") or "active"
        intensity = edge.get("intensity")
        if intensity is None:
            rows.append(f"{source}->{target}:{rel_type}({status})")
        else:
            rows.append(f"{source}->{target}:{rel_type}({status},intensity={intensity})")
    return " | ".join(rows)
