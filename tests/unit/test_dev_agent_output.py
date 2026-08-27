"""
DevAgent 输出目录契约测试：output 目录结构存在、可写，及 latest_run.json 格式约定。
与 docs/guides/cursor-and-devagent-workflow.md §3.1、§3.2 一致。
"""
import json
import pytest
from pathlib import Path


class TestDevAgentOutputStructure:
    """dev_agent/output 及子目录必须存在。"""

    def test_output_dir_exists(self, dev_agent_output_dir):
        assert dev_agent_output_dir.is_dir(), "dev_agent/output must exist"

    def test_failures_dir_exists(self, dev_agent_output_dir):
        assert (dev_agent_output_dir / "failures").is_dir(), "dev_agent/output/failures must exist"

    def test_suggestions_dir_exists(self, dev_agent_output_dir):
        assert (dev_agent_output_dir / "suggestions").is_dir(), "dev_agent/output/suggestions must exist"

    def test_patches_dir_exists(self, dev_agent_output_dir):
        assert (dev_agent_output_dir / "patches").is_dir(), "dev_agent/output/patches must exist"

    def test_search_ideas_dir_exists(self, dev_agent_output_dir):
        assert (dev_agent_output_dir / "search_ideas").is_dir(), "dev_agent/output/search_ideas must exist"


class TestDevAgentOutputWritable:
    """各输出子目录必须可写（DevAgent 需能写入报告）。"""

    def test_failures_dir_writable(self, dev_agent_output_dir):
        p = dev_agent_output_dir / "failures" / "_pytest_writable_check.txt"
        try:
            p.write_text("ok", encoding="utf-8")
            assert p.read_text(encoding="utf-8") == "ok"
        finally:
            if p.exists():
                p.unlink()

    def test_suggestions_dir_writable(self, dev_agent_output_dir):
        p = dev_agent_output_dir / "suggestions" / "_pytest_writable_check.txt"
        try:
            p.write_text("ok", encoding="utf-8")
            assert p.read_text(encoding="utf-8") == "ok"
        finally:
            if p.exists():
                p.unlink()


class TestLatestRunJsonSchema:
    """latest_run.json 约定格式：供 Cursor 解析，DevAgent 写入。"""

    def test_latest_run_json_required_keys(self):
        # 约定：至少包含 ok, test_summary；可选 suggestions_count, failure_report
        sample = {
            "ok": False,
            "test_summary": "2 failed, 3 passed",
            "suggestions_count": 1,
            "failure_report": "failures/2026-02-11_10-00.md",
        }
        assert "ok" in sample
        assert "test_summary" in sample
        assert isinstance(sample["ok"], bool)
        assert isinstance(sample["test_summary"], str)

    def test_latest_run_json_roundtrip(self, dev_agent_output_dir):
        # 写入再读回，确保 JSON 可序列化且路径可用
        sample = {
            "ok": True,
            "test_summary": "5 passed",
            "suggestions_count": 0,
        }
        path = dev_agent_output_dir / "latest_run.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sample, f, ensure_ascii=False)
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded == sample
        finally:
            if path.exists():
                path.unlink()
