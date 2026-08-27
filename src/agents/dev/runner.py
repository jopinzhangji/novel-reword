"""
DevAgent 测试运行器：执行 test_command，捕获退出码与输出。
与 TECH_IMPLEMENTATION §3.6「保证运行成功与测试通过」一致。
"""
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    summary: str  # 供 latest_run.json 的 test_summary 使用


def run_test_command(command: str, cwd: Path, use_current_python: bool = True) -> RunResult:
    """
    在 cwd 下执行 command（如 pytest tests/ -v），捕获退出码、stdout、stderr。
    use_current_python=True 时，将 command 中的 "pytest" 改为 "当前解释器 -m pytest"，确保使用当前 venv。
    自动生成简短 summary：若 stdout 中含 "passed"/"failed" 则尽量提取，否则用 exit_code 与末段输出。
    """
    cwd = Path(cwd)
    if use_current_python and command.strip().startswith("pytest"):
        # 使用当前 Python 解释器运行 pytest，确保 venv 生效（Windows 下 PATH 可能未含 venv）
        rest = command.strip()[6:].strip()
        command = f'"{sys.executable}" -m pytest {rest}'
    proc = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""
    summary = _make_summary(proc.returncode, out, err)
    return RunResult(exit_code=proc.returncode, stdout=out, stderr=err, summary=summary)


def _make_summary(exit_code: int, stdout: str, stderr: str) -> str:
    """从 pytest 或通用输出中提取简短摘要。"""
    combined = (stdout + "\n" + stderr).strip()
    # 常见 pytest 末行： "5 passed in 0.12s" 或 "2 failed, 3 passed in 0.5s"
    if "passed" in combined or "failed" in combined:
        for line in reversed(combined.splitlines()):
            line = line.strip()
            if "passed" in line or "failed" in line:
                return line
    if exit_code == 0:
        return "ok (exit 0)"
    return f"exit code {exit_code}"
