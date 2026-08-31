"""G4 关系图谱视图（SDD D13 §4 关系·全书谱 / 心图 / 角色对）。

确定性，委托 relationship_graph：全量 / ego 心图 / 单对 + change_log。
默认只出有效（status=active）边；inactive 边加 `inactive: True` 标以便前端虚线。
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from src.runtime.relationship_graph import (
    get_relation,
    get_relation_change_log,
    load_graph,
    relationship_graph_yaml_path,
)


def _load(novel_root: Path) -> dict:
    return load_graph(relationship_graph_yaml_path(novel_root))


def full_graph(novel_root: Path) -> dict:
    graph = _load(novel_root)
    edges = [e for e in graph.get("edges", []) if isinstance(e, dict)]
    for e in edges:
        e.setdefault("inactive", bool(e.get("status") and str(e.get("status")) != "active"))
    return {
        "nodes": [n for n in graph.get("nodes", []) if isinstance(n, dict)],
        "edges": edges,
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(edges),
    }


def _bfs_subgraph(graph: dict, center: str, hops: int) -> tuple[list[dict], list[dict]]:
    """以 center 为中心做 1..hops 跳 BFS，收集可达节点与边（含 inactive 用于展示）。"""
    edges = graph.get("edges", []) or []
    adj: dict[str, list[dict]] = {}
    for e in edges:
        if not isinstance(e, dict):
            continue
        s, t = e.get("source_id"), e.get("target_id")
        if s is None or t is None:
            continue
        adj.setdefault(s, []).append(e)
        adj.setdefault(t, []).append(e)
    out_nodes, out_edges, seen_nodes = [], [], {center}
    layer = [center]
    for _ in range(max(1, int(hops))):
        nxt: list[str] = []
        for node in layer:
            for e in adj.get(node, []):
                s, t = e.get("source_id"), e.get("target_id")
                if e in out_edges:
                    continue
                out_edges.append(e)
                other = t if s == node else s
                if other not in seen_nodes:
                    seen_nodes.add(other)
                    nxt.append(other)
        layer = nxt
        if not layer:
            break
    for n in graph.get("nodes", []) or []:
        if isinstance(n, dict) and n.get("id") in seen_nodes:
            out_nodes.append(n)
    for e in out_edges:
        e.setdefault("inactive", bool(e.get("status") and str(e.get("status")) != "active"))
    return out_nodes, out_edges


def ego_graph(novel_root: Path, center: str, hops: int = 2) -> dict:
    graph = _load(novel_root)
    nodes, edges = _bfs_subgraph(graph, center, int(hops))
    return {
        "center": center,
        "hops": int(hops),
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def pair(novel_root: Path, a: str, b: str) -> dict:
    graph = _load(novel_root)
    rel = get_relation(graph, a, b)
    reverse = get_relation(graph, b, a)
    log = get_relation_change_log(graph, a, b, limit=20)
    return {
        "source_id": a,
        "target_id": b,
        "relation": rel,
        "reverse_relation": reverse,
        "change_log": log,
        "has_relation": rel is not None or reverse is not None,
    }