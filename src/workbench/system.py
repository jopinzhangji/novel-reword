"""G4c+/system 系统设置（SDD D13 §6.4 · GG5）。

读：effective LLM（只读展示）/ 工作台互斥 / 联网检索 三组，取自 `load_runtime_config`
（已含 per-novel `config/runtime.yaml` 覆盖）。
写：白名单键落 **per-novel** `data/novels/<slug>/config/runtime.yaml`（顶层 `runtime:` 下
`author_workbench` / `author_harness.internet_search`）——与 G3 features.yaml 同构的安全
覆盖，合并保留既有键、不动 `config/*.yaml` canonical；改后下一会话生效。

LLM 提供方 **v1 只读**（真实提供方由 .env/密钥驱动，中途改易断链），仅展示不写。
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
        "readonly": True,  # v1 只读展示，不破启动链
        "note": "v1 只读：LLM 提供方由环境密钥驱动，运行时中途改提供方易断链。",
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


def _write_override(novel_root: Path, runtime_patch: dict) -> Path:
    """把 `runtime:` 顶层补丁并进 per-novel config/runtime.yaml（合并保留既有键）。"""
    path = novel_root / "config" / "runtime.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.is_file():
        try:
            existing = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data = existing
        except yaml.YAMLError:
            data = {}
    patch = {"runtime": runtime_patch}
    # 释放顶层：把既有 runtime 片段与新 runtime_patch 按键合并（白名单键覆盖，其余保留）
    merged = data.setdefault("runtime", {})
    if not isinstance(merged, dict):
        merged = {}
        data["runtime"] = merged
    for k, v in runtime_patch.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
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
    framework（LLM）v1 只读：传入即忽略（不写），保持不破启动链。
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

    _write_override(novel_root, runtime_patch)
    return _status_from(project_root, novel_root)