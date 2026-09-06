"""G4c+/system 系统设置（SDD D13 §6.4 · GG5）。

读：effective LLM（v2 工作参数可写）/ 工作台互斥 / 联网检索 三组，取自 `load_runtime_config`
（已含 per-novel `config/runtime.yaml` 覆盖）。
写：白名单键落 **per-novel** `data/novels/<slug>/config/runtime.yaml`——运行时组（顶层
`runtime:` 下 `author_workbench` / `author_harness.internet_search`）与 LLM 组（**顶层
`framework.llm_options`**，因 `_framework_info` 读 top-level `framework`，区别于运行时组的
`runtime:` 包装）——合并保留既有键、不动 `config/*.yaml` canonical；改后下一会话生效。

LLM：**v2 工作参数可写**（`model`/`base_url`/`timeout`/`max_retries`/`api_key_env`）；
提供方类型（`framework.llm`）与密钥值本身仍只读（展示不写）。
确定性、无 LLM；写口全走白名单校验。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.author_harness.internet_search import load_internet_search_settings
from src.config import current_novel_root, load_runtime_config

# 白名单：author_workbench（可写单键）↔ 顶层 .runtime.<path>
_WORKBENCH_PATH = ("author_workbench", "enabled")

# 白名单：internet_search 可写子键 ↔ .author_harness.internet_search.<sub>
_INTERNET_SUBKEYS = {
    "enabled": bool,
    "provider": str,
    "max_chars": int,
    "trust_level": str,
}

# 白名单：LLM 工作参数可写子键 ↔ 顶层 .framework.llm_options.<sub>（v2）
_LLM_WRITABLE_SUBS = ("model", "base_url", "timeout", "max_retries", "api_key_env")

# LLM 展示用的敏感键不外漏（暴露 key/env 名即可，不返回密钥值）
_LLM_DISPLAY_KEYS = ("model", "base_url", "timeout", "max_retries")


def _nested_set(data: dict, path: tuple[str, ...], value: Any) -> None:
    cur = data
    for k in path[:-1]:
        nxt = cur.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[k] = nxt
        cur = nxt
    cur[path[-1]] = value


def _merge_patch(target: dict, patch: dict) -> None:
    """把补丁深合并进 target：dict 递归、标量/其它替换。保既有键。"""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _merge_patch(target[k], v)
        else:
            target[k] = v


def _framework_info(runtime_config: dict) -> dict:
    fw = runtime_config.get("framework") or {}
    if not isinstance(fw, dict):
        fw = {}
    opts = fw.get("llm_options")
    opts = opts if isinstance(opts, dict) else {}
    display = {k: opts.get(k) for k in _LLM_DISPLAY_KEYS if k in opts}
    api_key_env = opts.get("api_key_env") or "（未配置）"
    return {
        "llm": fw.get("llm") or "dummy",
        "api_key_env": api_key_env,
        "options": display,
        "writable": list(_LLM_WRITABLE_SUBS),  # v2 白名单工作参数（含 api_key_env）
        "readonly": False,
        "note": "v2 可写：model/base_url/timeout/max_retries/api_key_env（白名单）；"
        "提供方类型与密钥值仍只读，改后下一会话生效。",
    }


def _internet_info(runtime_config: dict) -> dict:
    st = load_internet_search_settings(runtime_config)
    return {
        "enabled": st.enabled,
        "provider": st.provider,
        "max_chars": st.max_chars,
        "trust_level": st.trust_level,
        "timeout_ms": st.timeout_ms,
        "max_results": st.max_results,
        "min_query_tokens": st.min_query_tokens,
        "require_classifier_signal": st.require_classifier_signal,
    }


def _status_from(project_root: Path, novel_root: Path | None) -> dict:
    project_root = Path(project_root)
    rt = load_runtime_config(project_root / "config")
    runtime = rt.get("runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    awb = runtime.get("author_workbench")
    awb = awb if isinstance(awb, dict) else {}
    override_path = None
    diagrams = None
    if novel_root is not None:
        p = novel_root / "config" / "runtime.yaml"
        if p.is_file():
            override_path = str(p)
    return {
        "current_novel": {
            "slug": Path(novel_root).name if novel_root else None,
            "root": str(novel_root) if novel_root else None,
        }
        if novel_root
        else None,
        "framework": _framework_info(rt),
        "workbench": {"author_workbench_enabled": bool(awb.get("enabled", False))},
        "internet_search": _internet_info(rt),
        "override_source": override_path,
        "effect_note": "LLM 由环境驱动；工作台互斥/联网写口落 per-novel runtime.yaml，改后下一会话生效。",
    }


def system_status(project_root: Path | str) -> dict:
    """读 effective 系统设置（LLM 只读 / 工作台互斥 / 联网检索）。"""
    project_root = Path(project_root)
    return _status_from(project_root, current_novel_root(project_root / "config"))


def _load_override(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.is_file():
        try:
            existing = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data = existing
        except yaml.YAMLError:
            data = {}
    return data


def _write_override(novel_root: Path, runtime_patch: dict) -> Path:
    """把 `runtime:` 顶层补丁并进 per-novel config/runtime.yaml（深合并保留既有键）。"""
    path = novel_root / "config" / "runtime.yaml"
    data = _load_override(path)
    merged = data.setdefault("runtime", {})
    if not isinstance(merged, dict):
        merged = {}
        data["runtime"] = merged
    _merge_patch(merged, runtime_patch)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def _write_framework_override(novel_root: Path, llm_patch: dict) -> Path:
    """LLM 工作参数补丁并进 per-novel config/runtime.yaml 的 **顶层 `framework`**。

    与 `_write_override`（运行时组 `runtime:` 包装）关键差异：`_framework_info`/
    `load_runtime_config` 读的是 **top-level `framework`**，故 framework 覆盖写顶层，
    不套 `runtime:`。深合并保留既有 `framework.llm` 与其它 llm_options。
    """
    path = novel_root / "config" / "runtime.yaml"
    data = _load_override(path)
    fw = data.setdefault("framework", {})
    if not isinstance(fw, dict):
        fw = {}
        data["framework"] = fw
    opts = fw.setdefault("llm_options", {})
    if not isinstance(opts, dict):
        opts = {}
        fw["llm_options"] = opts
    _merge_patch(opts, llm_patch)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


def patch_system(project_root: Path | str, patch: dict) -> dict:
    """白名单写入 per-novel config/runtime.yaml，返回更新后的 effective 状态。

    支持键：
      - author_workbench_enabled: bool            → runtime.author_workbench.enabled
      - internet_search: dict                     → runtime.author_harness.internet_search.<sub>
        可写子键：enabled(bool) / provider(str) /
                  max_chars(int, 200..8000) / trust_level(str in {low,mid,high})
    framework（LLM）**v2 工作参数可写**（白名单）→ 顶层 `framework.llm_options.<sub>`；
    提供方类型与密钥值不在白名单内（传 `framework.llm` 之类非白名单键即忽略）。
    """
    project_root = Path(project_root)
    novel_root = current_novel_root(project_root / "config")
    if novel_root is None:
        raise ValueError("未绑定当前小说（config/current_novel.yaml 缺失或无效），无法写系统设置")
    if not isinstance(patch, dict):
        raise ValueError("patch 必须是 dict")

    runtime_patch: dict[str, Any] = {}
    if "author_workbench_enabled" in patch:
        val = patch["author_workbench_enabled"]
        if not isinstance(val, bool):
            raise ValueError("author_workbench_enabled 必须是布尔值")
        _nested_set(runtime_patch, list(_WORKBENCH_PATH), val)

    is_patch = patch.get("internet_search")
    if is_patch is not None:
        if not isinstance(is_patch, dict):
            raise ValueError("internet_search 必须是 dict")
        is_cur: dict[str, Any] = {}
        for sub in _INTERNET_SUBKEYS:
            if sub not in is_patch:
                continue
            val = is_patch[sub]
            sub_t = _INTERNET_SUBKEYS[sub]
            if sub_t is bool:
                if not isinstance(val, bool):
                    raise ValueError(f"internet_search.{sub} 必须是布尔值")
            elif sub_t is str:
                if not isinstance(val, str) or not val.strip():
                    raise ValueError(f"internet_search.{sub} 须为非空字符串")
            if sub == "max_chars":
                if not isinstance(val, int) or not (200 <= val <= 8000):
                    raise ValueError("internet_search.max_chars 须为 200..8000 的整数")
            if sub == "trust_level":
                if not isinstance(val, str) or val not in ("low", "medium", "high"):
                    raise ValueError("internet_search.trust_level 须为 low/medium/high")
            is_cur[sub] = val
        runtime_patch["author_harness"] = {"internet_search": dict(is_cur)}

    if runtime_patch:
        _write_override(novel_root, runtime_patch)

    fw_patch = patch.get("framework")
    if fw_patch is not None:
        if not isinstance(fw_patch, dict):
            raise ValueError("framework 必须是 dict")
        llm_patch: dict[str, Any] = {}
        for sub in _LLM_WRITABLE_SUBS:
            if sub not in fw_patch:
                continue
            val = fw_patch[sub]
            if sub in ("model", "base_url", "api_key_env"):
                if not isinstance(val, str) or not val.strip():
                    raise ValueError(f"framework.{sub} 须为非空字符串")
            elif sub == "timeout":
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not (1 <= val <= 300):
                    raise ValueError("framework.timeout 须为 1..300 的秒数")
            elif sub == "max_retries":
                if isinstance(val, bool) or not isinstance(val, int) or not (0 <= val <= 10):
                    raise ValueError("framework.max_retries 须为 0..10 的整数")
            llm_patch[sub] = val
        if llm_patch:
            _write_framework_override(novel_root, llm_patch)

    return _status_from(project_root, novel_root)