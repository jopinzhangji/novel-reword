# 配置加载与校验

import copy
import logging
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(__name__)

# 小说运行时（内容向）与系统级（LLM、调试、DevAgent）分离
SYSTEM_CONFIG_BASENAME = "system_config.yaml"
RUNTIME_NOVEL_BASENAME = "example_runtime.yaml"
# 小说写作基础（流程/设定研究/作者在环/storage 等），合并入 runtime
NOVEL_WRITING_BASENAME = "novel_writing.yaml"

# 未提供 config/example_runtime.yaml 时使用：仅含开局与 agents 占位，与下方默认 world/characters 的 id 一致。
# 作品级正文设定在绑定 current_novel 后从 data/novels/<slug>/config/ 加载。
DEFAULT_RUNTIME_NOVEL: dict = {
    "runtime": {
        "novel_run": {
            "initial_scope_id": "main",
            "initial_time": "（未设定）",
            "initial_place": "（未设定）",
            "protagonist_id": "protagonist",
        }
    },
    "agents": {
        "characters": {"enabled_ids": ["protagonist"]},
        "scopes": {"enabled_ids": ["main"]},
    },
}


def load_yaml(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_yaml_if_exists(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典：override 覆盖 base 同名键；子字典递归合并。"""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# 历史模板与旧 system_config 常为 30s，长上下文 Chat 易读超时；仅当仍为该值时抬高，避免覆盖作者显式设的更短超时
_LEGACY_LLM_TIMEOUT_S = 30.0
_ELEVATED_LLM_TIMEOUT_S = 180.0


def _elevate_legacy_framework_llm_timeout(merged: dict) -> None:
    """若 framework.llm_options.timeout 仍为旧默认 30，则提升为推荐值（与 system_config / OpenAI Provider 默认一致）。"""
    fw = merged.get("framework")
    if not isinstance(fw, dict):
        return
    opts = fw.get("llm_options")
    if not isinstance(opts, dict):
        return
    if "timeout" not in opts:
        return
    raw = opts["timeout"]
    try:
        tv = float(raw)
    except (TypeError, ValueError):
        return
    if tv != _LEGACY_LLM_TIMEOUT_S:
        return
    opts["timeout"] = (
        int(_ELEVATED_LLM_TIMEOUT_S)
        if isinstance(raw, int) and not isinstance(raw, bool)
        else _ELEVATED_LLM_TIMEOUT_S
    )
    logger.info(
        "[启动] framework.llm_options.timeout=30 为旧默认，已提升为 %s 秒（长上下文/兼容端点首包更稳妥）",
        _ELEVATED_LLM_TIMEOUT_S,
    )


def current_novel_root(config_dir: Path | None = None) -> Path | None:
    """读取 config/current_novel.yaml 中的 root，存在且有效则返回。"""
    config_dir = Path(config_dir or (PROJECT_ROOT / "config"))
    p = config_dir / "current_novel.yaml"
    if not p.is_file():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    root = (data.get("root") or "").strip()
    if not root:
        return None
    rp = Path(root)
    return rp if rp.is_dir() else None


def _merge_novel_writing_into_runtime(merged: dict, config_dir: Path) -> None:
    """
    将 novel_writing.yaml 中的键并入 merged['runtime']（深度合并，后者覆盖同名键）。
    支持两种写法：① 根下直接写 world_coordinator_enabled、setting_research…；
    ② 包在 novel_writing: 下（仅使用该子映射）。
    """
    path = config_dir / NOVEL_WRITING_BASENAME
    nw = load_yaml_if_exists(path)
    if not nw:
        return
    if isinstance(nw.get("novel_writing"), dict):
        fragment = nw["novel_writing"]
    else:
        fragment = nw
    if not isinstance(fragment, dict):
        return
    rt = merged.get("runtime")
    if not isinstance(rt, dict):
        merged["runtime"] = dict(fragment)
    else:
        merged["runtime"] = deep_merge(rt, fragment)


def load_runtime_config(config_dir: Path | None = None) -> dict:
    """
    加载「运行时」配置：
    1. system_config.yaml（可选）
    2. example_runtime.yaml（可选）— 缺失时使用内置 DEFAULT_RUNTIME_NOVEL（仅入口占位）
    3. novel_writing.yaml（可选）— 并入 runtime，覆盖其中同名键（小说写作基础：流程、设定研究、storage 等）

    顶层同名键以靠后的来源为准：system < example_runtime；runtime 内字段由 novel_writing 最后覆盖。
    绑定 current_novel 后，小说目录下 config/runtime.yaml 再叠加（见下方）。
    """
    config_dir = config_dir or (PROJECT_ROOT / "config")
    sys_path = config_dir / SYSTEM_CONFIG_BASENAME
    novel_path = config_dir / RUNTIME_NOVEL_BASENAME
    nw_path = config_dir / NOVEL_WRITING_BASENAME
    logger.debug(
        "[启动] 加载 runtime 配置: system=%s, novel=%s, novel_writing=%s",
        sys_path,
        novel_path,
        nw_path,
    )
    system = load_yaml_if_exists(sys_path)
    novel = load_yaml_if_exists(novel_path)
    if not novel:
        novel = copy.deepcopy(DEFAULT_RUNTIME_NOVEL)
        logger.info(
            "[启动] 未找到 %s，使用内置默认入口（agents / novel_run）；作品级内容以小说目录 config 为准。",
            RUNTIME_NOVEL_BASENAME,
        )
    out = deep_merge(system, novel)
    _merge_novel_writing_into_runtime(out, config_dir)
    # 若已绑定当前小说，优先叠加小说目录下 config/runtime.yaml（同名键覆盖）
    novel_root = current_novel_root(config_dir)
    if novel_root:
        nr_path = novel_root / "config" / "runtime.yaml"
        nr = load_yaml_if_exists(nr_path)
        if isinstance(nr, dict) and nr:
            out = deep_merge(out, nr)
            logger.debug("[启动] runtime 叠加小说级配置: %s", nr_path)

    _elevate_legacy_framework_llm_timeout(out)

    logger.debug("[启动] runtime 已合并, keys=%s", list(out.keys()) if isinstance(out, dict) else "?")
    return out


def load_world_config(config_dir: Path | None = None) -> dict:
    config_dir = config_dir or (PROJECT_ROOT / "config")
    novel_root = current_novel_root(config_dir)
    if novel_root:
        npath = novel_root / "config" / "world.yaml"
        if npath.is_file():
            logger.debug("[启动] 加载小说级世界配置: %s", npath)
            out = load_yaml(npath)
            logger.debug("[启动] world 已加载(小说级), scopes=%s", [s.get("id") for s in (out.get("scopes") or []) if isinstance(s, dict)])
            return out
    path = config_dir / "example_world.yaml"
    logger.debug("[启动] 加载世界配置: %s", path)
    out = load_yaml(path)
    logger.debug("[启动] world 已加载, scopes=%s", [s.get("id") for s in (out.get("scopes") or []) if isinstance(s, dict)])
    return out


def load_characters_config(config_dir: Path | None = None) -> dict:
    config_dir = config_dir or (PROJECT_ROOT / "config")
    novel_root = current_novel_root(config_dir)
    if novel_root:
        npath = novel_root / "config" / "characters.yaml"
        if npath.is_file():
            logger.debug("[启动] 加载小说级角色配置: %s", npath)
            out = load_yaml(npath)
            chars = out.get("characters") or []
            logger.debug("[启动] characters 已加载(小说级), 角色数=%s, ids=%s", len(chars), [c.get("id") for c in chars if isinstance(c, dict)])
            return out
    path = config_dir / "example_characters.yaml"
    logger.debug("[启动] 加载角色配置: %s", path)
    out = load_yaml(path)
    chars = out.get("characters") or []
    logger.debug("[启动] characters 已加载, 角色数=%s, ids=%s", len(chars), [c.get("id") for c in chars if isinstance(c, dict)])
    return out


def special_settings_config_dir(config_dir: Path | None = None) -> Path:
    """
    设定研究产出 setting_research_output.yaml 所在目录：必须为 <小说根>/config/。
    未绑定 current_novel 时抛出错误，要求作者先创建/选择作品（书名与目录）。
    """
    config_dir = Path(config_dir or (PROJECT_ROOT / "config"))
    novel_root = current_novel_root(config_dir)
    if not novel_root:
        raise RuntimeError(
            "尚未创建或选择当前作品：请先回到主流程，按程序提示完成「新建书名 / 选择作品」等交互步骤；"
            "绑定作品目录后再进入设定研究。请勿手写配置文件。"
        )
    return novel_root / "config"


def load_special_settings_config(config_dir: Path | None = None) -> dict | None:
    """加载特殊设定（战力/境界等）。已绑定小说时读 <小说>/config/setting_research_output.yaml；否则仅尝试全局 example_special_settings.yaml；不存在则返回 None。"""
    config_dir = Path(config_dir or (PROJECT_ROOT / "config"))
    novel_root = current_novel_root(config_dir)
    logger.debug("[启动] 加载特殊设定: config_dir=%s, novel_root=%s", config_dir, novel_root)
    if novel_root:
        path_sr = novel_root / "config" / "setting_research_output.yaml"
        if path_sr.is_file():
            logger.debug("[启动] 使用特殊设定文件: %s", path_sr)
            with open(path_sr, "r", encoding="utf-8") as f:
                out = yaml.safe_load(f) or {}
            logger.debug("[启动] special 已加载, keys=%s", list(out.keys()) if isinstance(out, dict) else "?")
            return out
    path_ex = config_dir / "example_special_settings.yaml"
    if path_ex.is_file():
        logger.debug("[启动] 使用特殊设定文件: %s", path_ex)
        with open(path_ex, "r", encoding="utf-8") as f:
            out = yaml.safe_load(f) or {}
        logger.debug("[启动] special 已加载, keys=%s", list(out.keys()) if isinstance(out, dict) else "?")
        return out
    logger.debug("[启动] 未找到特殊设定文件，跳过")
    return None


def update_world_brief(config_dir: Path | None, brief_text: str) -> bool:
    """
    将世界配置的封面简介（brief）更新为给定文案并写回 example_world.yaml。
    用于设定阶段选 p 保存时，将当前设定摘要写入世界配置，类似小说封面介绍。
    返回是否成功写入。
    """
    config_dir = Path(config_dir or (PROJECT_ROOT / "config"))
    path = config_dir / "example_world.yaml"
    if not path.is_file():
        logger.warning("世界配置文件不存在，无法更新 brief: %s", path)
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        brief_val = (brief_text or "").strip()
        # 将 brief 置于首位，便于作为封面简介阅读
        out = {"brief": brief_val}
        for k, v in data.items():
            if k != "brief":
                out[k] = v
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                out,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        logger.info("已更新世界配置封面简介: %s", path)
        return True
    except Exception as e:
        logger.warning("更新世界配置 brief 失败 %s: %s", path, e)
        return False


def add_setting_document_to_world_config(
    config_dir: Path | None,
    key: str,
    path_rel: str | None = None,
    title: str | None = None,
) -> bool:
    """
    在世界配置的 setting_documents 中追加一项设定文档配置（若该 key 已存在则跳过）。
    用于设定交流中新增方向时，将 data/book/setting 下对应 .md 登记到世界配置，保证配置与落盘设定一致且动态生成。
    path_rel 默认 book/setting/<safe_key>.md；title 默认 key。
    """
    config_dir = Path(config_dir or (PROJECT_ROOT / "config"))
    path = config_dir / "example_world.yaml"
    if not path.is_file():
        logger.warning("世界配置文件不存在，无法追加 setting_documents: %s", path)
        return False
    if not key:
        return False
    safe = (key or "").replace("/", "_").replace("\\", "_").strip() or "unknown"
    path_rel = path_rel or f"book/setting/{safe}.md"
    title = (title or key).strip()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        docs = list(data.get("setting_documents") or [])
        if not isinstance(docs, list):
            docs = []
        if any(isinstance(d, dict) and d.get("key") == key for d in docs):
            logger.debug("世界配置 setting_documents 中已存在 key=%s，跳过", key)
            return False
        docs.append({"key": key, "path": path_rel, "title": title})
        data["setting_documents"] = docs
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        logger.info("已向世界配置追加设定文档: key=%s, path=%s", key, path_rel)
        return True
    except Exception as e:
        logger.warning("追加世界配置 setting_documents 失败 %s: %s", path, e)
        return False


def is_world_config_empty(world_config: dict) -> bool:
    """判断世界配置是否为空（无世界名或未填写），便于启动时提示通过交流获取。"""
    if not world_config:
        return True
    w = world_config.get("world") or {}
    if not w:
        return True
    name = (w.get("name") or "").strip()
    return not name


def validate_runtime_and_ids(runtime: dict, world: dict, characters: dict) -> None:
    enabled_char = set(runtime.get("agents", {}).get("characters", {}).get("enabled_ids", []))
    enabled_scope = set(runtime.get("agents", {}).get("scopes", {}).get("enabled_ids", []))
    char_ids = {c["id"] for c in characters.get("characters", []) if "id" in c}
    scope_ids = {s["id"] for s in world.get("scopes", []) if "id" in s}
    missing_char = enabled_char - char_ids
    missing_scope = enabled_scope - scope_ids
    if missing_char:
        raise ValueError(f"runtime.agents.characters.enabled_ids 中存在未定义角色 id: {missing_char}")
    if missing_scope:
        raise ValueError(f"runtime.agents.scopes.enabled_ids 中存在未定义范围 id: {missing_scope}")


def load_all_config(config_dir: Path | None = None) -> dict:
    config_dir = config_dir or (PROJECT_ROOT / "config")
    logger.debug("[启动] load_all_config: 开始, config_dir=%s", config_dir)
    nr = current_novel_root(config_dir)
    if nr:
        logger.debug("[启动] load_all_config: 使用当前小说目录=%s", nr)
    else:
        logger.debug("[启动] load_all_config: 未绑定当前小说目录，使用全局 config")
    runtime = load_runtime_config(config_dir)
    world = load_world_config(config_dir)
    characters = load_characters_config(config_dir)
    logger.debug("[启动] load_all_config: 校验 runtime/world/characters id 一致性")
    validate_runtime_and_ids(runtime, world, characters)
    logger.debug("[启动] load_all_config: 完成（novel_root=%s）", nr if nr else "global")
    return {"runtime": runtime, "world": world, "characters": characters}


def get_initial_scene(runtime_config: dict, world_config: dict | None = None) -> dict:
    """
    从配置解析开局场景（具体小说内容在配置中，程序可写任意小说）。
    返回 {"scope_id": str, "time": str, "place": str}。
    runtime_config 为合并 system_config + example_runtime 后的整份内容（可有顶层 runtime 或直接 novel_run）；
    initial_scope_id 不填时取 agents.scopes.enabled_ids 第一个；
    initial_time 不填时用 world.time.start；initial_place 不填时用 "（未设定）"。
    """
    logger.debug("[启动] get_initial_scene: 解析开局场景")
    inner = runtime_config.get("runtime") or runtime_config
    novel_run = inner.get("novel_run") or {}
    scope_id = novel_run.get("initial_scope_id")
    if not scope_id:
        enabled = list(runtime_config.get("agents", {}).get("scopes", {}).get("enabled_ids", []))
        scope_id = enabled[0] if enabled else ""
    time_str = novel_run.get("initial_time")
    if not time_str and world_config:
        time_str = (world_config.get("time") or {}).get("start") or ""
    time_str = time_str or "（未设定）"
    place = novel_run.get("initial_place") or "（未设定）"
    logger.debug("[启动] get_initial_scene: scope_id=%s, time=%s, place=%s", scope_id, time_str, place)
    return {"scope_id": scope_id, "time": time_str, "place": place}
