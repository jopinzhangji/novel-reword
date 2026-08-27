"""
配置加载与校验测试：YAML 加载、enabled_ids 校验，与 TECH_IMPLEMENTATION §7、NEXT_ITERATION 第 1 项一致。
"""
import pytest
from pathlib import Path
import yaml

from src.config import (
    PROJECT_ROOT,
    current_novel_root,
    DEFAULT_RUNTIME_NOVEL,
    load_yaml,
    load_runtime_config,
    load_world_config,
    load_characters_config,
    load_all_config,
    validate_runtime_and_ids,
    get_initial_scene,
)


class TestLoadYaml:
    def test_load_existing_file(self):
        """example_runtime 为可选；此处仅测 load_yaml 能读任意存在的 yaml。"""
        path = PROJECT_ROOT / "config" / "novel_writing.yaml"
        if not path.exists():
            pytest.skip("config/novel_writing.yaml not found")
        data = load_yaml(path)
        assert isinstance(data, dict)

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_yaml(PROJECT_ROOT / "config" / "nonexistent.yaml")


class TestLoadConfigs:
    def test_load_runtime_config_without_example_runtime_uses_default(self, tmp_path: Path):
        """无 example_runtime.yaml 时合并内置 DEFAULT_RUNTIME_NOVEL。"""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "system_config.yaml").write_text("framework:\n  llm: dummy\n", encoding="utf-8")
        (config_dir / "novel_writing.yaml").write_text(
            "turn_body_max_chars: 2000\nstorage:\n  data_root: data\n", encoding="utf-8"
        )
        (config_dir / "example_world.yaml").write_text(
            "world:\n  name: ''\nscopes:\n  - id: main\n    name: 主线\n",
            encoding="utf-8",
        )
        (config_dir / "example_characters.yaml").write_text(
            "characters:\n  - id: protagonist\n    name: 主角\n",
            encoding="utf-8",
        )
        data = load_runtime_config(config_dir)
        assert data.get("agents", {}).get("characters", {}).get("enabled_ids") == DEFAULT_RUNTIME_NOVEL["agents"][
            "characters"
        ]["enabled_ids"]

    def test_load_runtime_config(self):
        try:
            data = load_runtime_config()
        except FileNotFoundError:
            pytest.skip("config not found")
        assert "agents" in data
        assert "characters" in data.get("agents", {})
        assert "scopes" in data.get("agents", {})
        # system_config +（可选 example_runtime 或内置默认）+ novel_writing 合并
        assert "framework" in data
        assert "debug" in data
        inner = data.get("runtime") or {}
        assert inner.get("turn_body_max_chars") == 2000
        assert "storage" in inner

    def test_load_world_config(self):
        try:
            data = load_world_config()
        except FileNotFoundError:
            pytest.skip("config not found")
        assert "scopes" in data or "world" in data

    def test_load_characters_config(self):
        try:
            data = load_characters_config()
        except FileNotFoundError:
            pytest.skip("config not found")
        assert "characters" in data
        assert isinstance(data["characters"], list)

    def test_load_config_prefer_current_novel_root(self, tmp_path: Path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        # 全局基础配置
        (config_dir / "example_runtime.yaml").write_text(
            "runtime:\n  novel_run:\n    initial_scope_id: s1\nagents:\n  characters:\n    enabled_ids: [c1]\n  scopes:\n    enabled_ids: [s1]\n",
            encoding="utf-8",
        )
        (config_dir / "system_config.yaml").write_text("framework:\n  llm: dummy\n", encoding="utf-8")
        (config_dir / "example_world.yaml").write_text(
            "world:\n  name: 全局世界\nscopes:\n  - id: s1\n    name: 全局范围\n",
            encoding="utf-8",
        )
        (config_dir / "example_characters.yaml").write_text(
            "characters:\n  - id: c1\n    name: 全局角色\n",
            encoding="utf-8",
        )
        # 小说级配置
        novel_root = tmp_path / "data" / "novels" / "book-a"
        (novel_root / "config").mkdir(parents=True, exist_ok=True)
        (novel_root / "config" / "runtime.yaml").write_text(
            "runtime:\n  turn_body_max_chars: 1234\nagents:\n  characters:\n    enabled_ids: [c2]\n  scopes:\n    enabled_ids: [s2]\n",
            encoding="utf-8",
        )
        (novel_root / "config" / "world.yaml").write_text(
            "world:\n  name: 小说世界\nscopes:\n  - id: s2\n    name: 小说范围\n",
            encoding="utf-8",
        )
        (novel_root / "config" / "characters.yaml").write_text(
            "characters:\n  - id: c2\n    name: 小说角色\n",
            encoding="utf-8",
        )
        (config_dir / "current_novel.yaml").write_text(
            yaml.dump({"slug": "book-a", "root": str(novel_root)}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        rt = load_runtime_config(config_dir)
        w = load_world_config(config_dir)
        c = load_characters_config(config_dir)
        assert current_novel_root(config_dir) == novel_root
        assert (((rt.get("runtime") or {}).get("turn_body_max_chars")) == 1234)
        assert (w.get("world") or {}).get("name") == "小说世界"
        assert (c.get("characters") or [{}])[0].get("id") == "c2"

    def test_legacy_llm_timeout_30_elevated_when_novel_runtime_overlays(self, tmp_path: Path):
        """小说 config/runtime.yaml 中 timeout: 30 会压过 system_config；合并后统一抬为 180。"""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "system_config.yaml").write_text(
            "framework:\n  llm: tongyi\n  llm_options:\n    timeout: 180\n",
            encoding="utf-8",
        )
        novel_root = tmp_path / "data" / "novels" / "tbook"
        (novel_root / "config").mkdir(parents=True)
        (novel_root / "config" / "runtime.yaml").write_text(
            "framework:\n  llm_options:\n    timeout: 30\n",
            encoding="utf-8",
        )
        (config_dir / "current_novel.yaml").write_text(
            yaml.dump({"root": str(novel_root)}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        rt = load_runtime_config(config_dir)
        assert float((rt.get("framework") or {}).get("llm_options", {}).get("timeout")) == 180.0


class TestValidateRuntimeAndIds:
    def test_valid_enabled_ids_passes(self):
        runtime = {
            "agents": {
                "characters": {"enabled_ids": ["a", "b"]},
                "scopes": {"enabled_ids": ["capital", "jianghu"]},
            }
        }
        world = {"scopes": [{"id": "capital"}, {"id": "jianghu"}, {"id": "frontier"}]}
        characters = {"characters": [{"id": "a"}, {"id": "b"}]}
        validate_runtime_and_ids(runtime, world, characters)

    def test_missing_character_id_raises(self):
        runtime = {
            "agents": {
                "characters": {"enabled_ids": ["a", "b", "c"]},
                "scopes": {"enabled_ids": ["capital"]},
            }
        }
        world = {"scopes": [{"id": "capital"}]}
        characters = {"characters": [{"id": "a"}, {"id": "b"}]}
        with pytest.raises(ValueError, match="未定义角色 id"):
            validate_runtime_and_ids(runtime, world, characters)

    def test_missing_scope_id_raises(self):
        runtime = {
            "agents": {
                "characters": {"enabled_ids": ["a"]},
                "scopes": {"enabled_ids": ["capital", "nonexistent"]},
            }
        }
        world = {"scopes": [{"id": "capital"}]}
        characters = {"characters": [{"id": "a"}]}
        with pytest.raises(ValueError, match="未定义范围 id"):
            validate_runtime_and_ids(runtime, world, characters)


class TestLoadAllConfig:
    def test_load_all_config_returns_three_keys(self):
        try:
            all_cfg = load_all_config()
        except FileNotFoundError:
            pytest.skip("config files not found")
        assert "runtime" in all_cfg
        assert "world" in all_cfg
        assert "characters" in all_cfg
        validate_runtime_and_ids(
            all_cfg["runtime"],
            all_cfg["world"],
            all_cfg["characters"],
        )


class TestGetInitialScene:
    """开局场景从配置读取，不写死在代码中（程序可写任意小说）。"""

    def test_from_novel_run(self):
        runtime = {
            "runtime": {
                "novel_run": {
                    "initial_scope_id": "capital",
                    "initial_time": "永和十年春",
                    "initial_place": "京城",
                }
            },
            "agents": {"scopes": {"enabled_ids": ["capital", "jianghu"]}},
        }
        scene = get_initial_scene(runtime, None)
        assert scene["scope_id"] == "capital"
        assert scene["time"] == "永和十年春"
        assert scene["place"] == "京城"

    def test_fallback_time_from_world(self):
        runtime = {"runtime": {"novel_run": {"initial_scope_id": "s1", "initial_place": "某地"}}, "agents": {"scopes": {"enabled_ids": ["s1"]}}}
        world = {"time": {"start": "开篇元年"}}
        scene = get_initial_scene(runtime, world)
        assert scene["time"] == "开篇元年"

    def test_fallback_scope_from_enabled_ids(self):
        runtime = {"runtime": {"novel_run": {}}, "agents": {"scopes": {"enabled_ids": ["jianghu", "capital"]}}}
        scene = get_initial_scene(runtime, None)
        assert scene["scope_id"] == "jianghu"
        assert scene["place"] == "（未设定）"
