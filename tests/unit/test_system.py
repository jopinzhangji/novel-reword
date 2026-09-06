"""GG5 /system 单测（纯 service，无 fastapi 依赖）：system_status / patch_system。

- LLM 只读展示（framework 写被忽略）。
- 工作台互斥 + 联网检索白名单写 per-novel config/runtime.yaml，合并保留既有键。
- 校验非法输入（类型 / 范围 / 无当前小说）。
"""
import pytest

from src.workbench import system
from tests.unit.workbench_support import make_project, write_yaml


def _setup(project_root, *, novel_slug="alpha"):
    """建 config/system_config + novel_writing + current_novel → novel root。"""
    config_dir = project_root / "config"
    write_yaml(
        config_dir / "current_novel.yaml",
        {"slug": novel_slug, "root": str(project_root / "data" / "novels" / novel_slug)},
    )
    write_yaml(
        config_dir / "system_config.yaml",
        {
            "framework": {
                "llm": "openai_compatible",
                "llm_options": {"model": "deepseek-v4", "base_url": "https://x", "timeout": 180, "max_retries": 1},
            }
        },
    )
    write_yaml(config_dir / "novel_writing.yaml", {"author_workbench": {"enabled": False}})
    make_project(project_root, (novel_slug, "beta"))
    return project_root / "data" / "novels" / novel_slug


@pytest.fixture()
def project(tmp_path):
    """project_root（仓库根），内含 config/current_novel → data/novels/alpha。"""
    _setup(tmp_path)
    return tmp_path


def test_status_groups_llm_workbench_internet(project):
    st = system.system_status(project)
    assert st["framework"]["llm"] == "openai_compatible"
    assert st["framework"]["options"]["model"] == "deepseek-v4"
    assert st["framework"]["readonly"] is False  # v2 工作参数可写
    assert st["framework"]["writable"] == ["model", "base_url", "timeout", "max_retries", "api_key_env"]
    assert st["workbench"]["author_workbench_enabled"] is False
    assert st["internet_search"]["enabled"] is False
    assert st["current_novel"]["slug"] == "alpha"
    assert st["override_source"] is None  # 尚无 override


def test_patch_workbench_enable(project):
    st = system.patch_system(project, {"author_workbench_enabled": True})
    assert st["workbench"]["author_workbench_enabled"] is True
    # 落盘再读 effective 依然 true
    reloaded = system.system_status(project)
    assert reloaded["workbench"]["author_workbench_enabled"] is True
    assert reloaded["override_source"]  # override_source 出现


def test_patch_internet_and_preserves_existing_keys(project):
    root = project / "data" / "novels" / "alpha"
    # 预置既有 runtime 键，改后必须保留
    write_yaml(
        root / "config" / "runtime.yaml",
        {"runtime": {"novel_run": {"initial_scope_id": "main"}}, "agents": {"scopes": {"enabled_ids": ["main"]}}},
    )
    st = system.patch_system(
        project,
        {"internet_search": {"enabled": True, "provider": "playwright", "max_chars": 2000, "trust_level": "low"}},
    )
    assert st["internet_search"]["enabled"] is True
    assert st["internet_search"]["provider"] == "playwright"
    import yaml

    data = yaml.safe_load((root / "config" / "runtime.yaml").read_text(encoding="utf-8"))
    # 既有键保留
    assert data["runtime"]["novel_run"]["initial_scope_id"] == "main"
    assert data["agents"]["scopes"]["enabled_ids"] == ["main"]
    # 新键命中原先的默认路径
    assert data["runtime"]["author_harness"]["internet_search"]["enabled"] is True


def test_internet_partial_patch_only_touches_known(project):
    st = system.patch_system(project, {"internet_search": {"trust_level": "medium"}})
    assert st["internet_search"]["trust_level"] == "medium"
    assert st["internet_search"]["enabled"] is False  # 未写保持默认


def test_framework_work_params_writable(project):
    # LLM 工作参数（白名单）可写、落 per-novel top-level framework.llm_options、保既有 llm
    root = project / "data" / "novels" / "alpha"
    before = system.system_status(project)
    st = system.patch_system(
        project,
        {"framework": {"model": "deepseek-v5", "base_url": "https://y", "timeout": 120, "max_retries": 3}},
    )
    assert st["framework"]["llm"] == "openai_compatible"  # provider 类型只读不破
    assert st["framework"]["options"]["model"] == "deepseek-v5"
    assert st["framework"]["options"]["base_url"] == "https://y"
    assert st["framework"]["options"]["timeout"] == 120
    assert st["framework"]["options"]["max_retries"] == 3
    # 落盘：顶层 framework（非 runtime: 包装），且既有 config needed 不存在不干扰
    import yaml

    data = yaml.safe_load((root / "config" / "runtime.yaml").read_text(encoding="utf-8"))
    assert "framework" in data
    assert data["framework"]["llm_options"]["model"] == "deepseek-v5"
    # 再读 effective 依然生效
    assert system.system_status(project)["framework"]["options"]["model"] == "deepseek-v5"


def test_framework_provider_type_still_readonly(project):
    # 非白名单键（provider 类型）传入即忽略，不落盘、不崩
    before = system.system_status(project)
    st = system.patch_system(project, {"framework": {"llm": "tongyi"}})
    assert st["framework"]["llm"] == before["framework"]["llm"] == "openai_compatible"


def test_framework_api_key_env_writable(project):
    root = project / "data" / "novels" / "alpha"
    st = system.patch_system(project, {"framework": {"api_key_env": "MY_LLM_KEY"}})
    assert st["framework"]["api_key_env"] == "MY_LLM_KEY"
    import yaml

    data = yaml.safe_load((root / "config" / "runtime.yaml").read_text(encoding="utf-8"))
    assert data["framework"]["llm_options"]["api_key_env"] == "MY_LLM_KEY"


def test_rejects_bad_values(project):
    with pytest.raises(ValueError):
        system.patch_system(project, {"author_workbench_enabled": "yes"})
    with pytest.raises(ValueError):
        system.patch_system(project, {"internet_search": {"max_chars": 50}})  # 越界
    with pytest.raises(ValueError):
        system.patch_system(project, {"internet_search": {"trust_level": "ultra"}})  # 非法枚举
    with pytest.raises(ValueError):
        system.patch_system(project, {"internet_search": "on"})  # 非 dict
    with pytest.raises(ValueError):
        system.patch_system(project, {"framework": {"model": ""}})  # 空串
    with pytest.raises(ValueError):
        system.patch_system(project, {"framework": {"timeout": 0}})  # 越界
    with pytest.raises(ValueError):
        system.patch_system(project, {"framework": {"max_retries": 11}})  # 越界
    with pytest.raises(ValueError):
        system.patch_system(project, {"framework": "openai"})  # 非 dict


def test_no_current_novel_raises(tmp_path):
    # 无 current_novel.yaml → patch 拒绝，system_status 空 current_novel
    make_project(tmp_path, ("alpha",))
    st = system.system_status(tmp_path)
    assert st["current_novel"] is None
    with pytest.raises(ValueError):
        system.patch_system(tmp_path, {"author_workbench_enabled": True})