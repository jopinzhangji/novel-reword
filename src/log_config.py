"""
小说主程序日志配置：同时输出到控制台与日志文件。
日志统一写入「日志文件夹」：默认 project_root / logs /，可通过环境变量 MIN_AUTOBOOK_LOG_DIR 覆盖。
日志文件名默认按日期结尾（min_autobook_YYYY-MM-DD.log），方便多次运行分文件查看。
在 run_novel / run_novel_with_author 入口处调用 setup_logging()，之后各模块使用 logging.getLogger(__name__) 即可。
"""
import logging
import os
import sys
from datetime import date
from pathlib import Path


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler 子类：每次 emit 后 flush，避免控制台无输出。"""
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        if self.stream:
            self.stream.flush()

# 默认日志文件夹名（相对项目根）；可通过环境变量 MIN_AUTOBOOK_LOG_DIR 覆盖
DEFAULT_LOG_DIR = "logs"


def setup_logging(
    project_root: Path,
    *,
    log_dir: str | Path | None = None,
    log_file_name: str | None = None,
    level: str | int | None = None,
) -> logging.Logger:
    """
    配置根 logger：添加 StreamHandler（控制台）与 FileHandler（日志文件），使所有子 logger 同时输出到前台与文件。
    project_root: 项目根目录。
    日志文件夹：默认 project_root / logs /；若传入 log_dir 则以 project_root / log_dir 为准；
    否则从环境变量 MIN_AUTOBOOK_LOG_DIR 读取（可为相对路径或绝对路径），未设则用 DEFAULT_LOG_DIR（"logs"）。
    日志文件名：默认 None 时按日期命名为 min_autobook_YYYY-MM-DD.log，便于多次运行分文件查看；
    若传入 log_file_name 或设置环境变量 MIN_AUTOBOOK_LOG_FILE 则使用该文件名。
    level: 日志级别，默认从环境变量 MIN_AUTOBOOK_LOG_LEVEL 读取（INFO/DEBUG/WARNING/ERROR），未设则为 INFO。
    返回名为 "min_autobook" 的 logger，供入口脚本使用。
    """
    root = logging.getLogger()
    if level is None:
        level = os.environ.get("MIN_AUTOBOOK_LOG_LEVEL", "INFO").upper()
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)
    root.setLevel(level)

    # 避免重复添加（例如测试或多次调用）
    if root.handlers:
        return logging.getLogger("min_autobook")

    if log_dir is not None:
        dir_path = Path(project_root) / Path(log_dir)
    else:
        env_dir = os.environ.get("MIN_AUTOBOOK_LOG_DIR", "").strip()
        dir_path = Path(env_dir) if env_dir else Path(project_root) / DEFAULT_LOG_DIR
        if not dir_path.is_absolute():
            dir_path = Path(project_root) / dir_path
    dir_path.mkdir(parents=True, exist_ok=True)

    if log_file_name is None:
        log_file_name = os.environ.get("MIN_AUTOBOOK_LOG_FILE", "").strip()
    if not log_file_name:
        log_file_name = f"min_autobook_{date.today().isoformat()}.log"
    elif not log_file_name.endswith(".log"):
        log_file_name = log_file_name + ".log"
    log_path = dir_path / log_file_name

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = _FlushingStreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(level)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(level)
    root.addHandler(sh)
    root.addHandler(fh)

    logger = logging.getLogger("min_autobook")
    logger.info("日志已初始化：控制台 + 文件 %s", log_path)
    return logger


def apply_design_phase_debug(runtime_config: dict) -> None:
    """
    若 runtime 配置中 debug.design_phase 或 debug.startup 为 true，则将对应 logger 设为 DEBUG，
    并同时将根 logger 的 handler 级别设为 DEBUG，否则 DEBUG 消息会被 handler 过滤掉。
    - design_phase: 设定讨论流程（会话加载、主菜单、讨论子循环、归纳、保存、逻辑校准等）。
    - startup: 程序启动阶段加载的设定文件（runtime/world/characters/special、编排器创建等）。
    """
    # debug 可能在顶层（合并后的 runtime 配置，通常来自 system_config.yaml）或在 runtime 块下
    debug_cfg = runtime_config.get("debug") or (runtime_config.get("runtime") or {}).get("debug") or {}
    if not isinstance(debug_cfg, dict):
        debug_cfg = {}
    if not debug_cfg.get("design_phase") and not debug_cfg.get("startup"):
        return
    level = logging.DEBUG
    # 关键：根 logger 的 handler 默认是 INFO，会过滤掉 DEBUG；开启 debug 时需把 handler 也设为 DEBUG
    root = logging.getLogger()
    for h in root.handlers:
        h.setLevel(level)
    root.setLevel(min(root.level, level))
    if debug_cfg.get("design_phase"):
        for name in (
            "src.author_loop.design_phase",
            "src.author_loop.design_session_persistence",
            "src.agents.setting_research",
            "src.agents.setting_research.agent",
        ):
            logging.getLogger(name).setLevel(level)
        logging.getLogger("min_autobook").debug("已开启设定讨论流程 DEBUG 日志（debug.design_phase=true）")
    if debug_cfg.get("startup"):
        for name in ("src.config", "src.orchestrator.orchestrator", "min_autobook"):
            logging.getLogger(name).setLevel(level)
        logging.getLogger("min_autobook").debug("已开启启动阶段设定加载 DEBUG 日志（debug.startup=true）")
