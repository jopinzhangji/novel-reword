"""G4 关系图谱（graph.py）：全书谱 / ego 心图 / 单对 + change_log。"""
from src.workbench import graph
from tests.unit.workbench_support import make_project, write_graph


def test_full_graph(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_graph(roots["alpha"])
    g = graph.full_graph(roots["alpha"])
    assert g["node_count"] == 4 and g["edge_count"] == 3
    active = [e for e in g["edges"] if not e["inactive"]]
    assert len(active) == 2
    inactive = [e for e in g["edges"] if e["inactive"]]
    assert len(inactive) == 1


def test_ego_graph_hops(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_graph(roots["alpha"])
    ego = graph.ego_graph(roots["alpha"], "苏A", hops=1)
    ids = {n["id"] for n in ego["nodes"]}
    assert ids == {"苏A", "李B", "钱C"}  # 一跳不含 丁D
    ego2 = graph.ego_graph(roots["alpha"], "苏A", hops=2)
    assert "丁D" in {n["id"] for n in ego2["nodes"]}


def test_pair_with_change_log(tmp_path):
    proj, roots = make_project(tmp_path, ("alpha",))
    write_graph(roots["alpha"])
    p = graph.pair(roots["alpha"], "苏A", "李B")
    assert p["has_relation"] is True
    assert p["relation"]["type"] == "trust"
    assert p["change_log"] == [{"turn": 1, "reason": "并肩"}]
    miss = graph.pair(roots["alpha"], "苏A", "丁D")  # 无该边 → has False
    assert miss["relation"] is None and miss["reverse_relation"] is None
    assert miss["has_relation"] is False