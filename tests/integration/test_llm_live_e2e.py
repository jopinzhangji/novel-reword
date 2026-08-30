"""
真实 LLM 联调测试（live）：默认跳过，仅在项目根 .env 中同时含 DASHSCOPE_API_KEY 与 LLM_E2E=1 时执行
（跑完联调后可从 .env 删除 LLM_E2E=1 恢复默认跳过；该文件被 gitignore，不入库）。

覆盖 Linux 移植后真实 LLM 下的作者在环一回合全链路：
设定阶段（保留已有设定 -> y 完成）-> 写作前分析（LLM）-> 正文生成（LLM）
-> 阶段一审阅 y -> 事件簿/状态写回 -> 阶段二确认 y -> 角色记忆写回。

产物落在 data/novels/e2e-llm-test/ 与 data/book/（均为 gitignored 本地数据，测试自行清理重建）。
运行：python -m pytest tests/integration/test_llm_live_e2e.py -q --timeout=700
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_llm_env() -> dict[str, str]:
    """从项目根 .env 读取 DASHSCOPE_API_KEY（若存在）；不存在返回空 dict。"""
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _setup_e2e_novel() -> None:
    """清理旧产物并构造带既有设定的绑定小说（跳过初稿引导与书名确认）。"""
    # 清理：上次联调产物与全局事件簿
    for target in [
        PROJECT_ROOT / "data/novels/e2e-llm-test",
        PROJECT_ROOT / "data/book",
        PROJECT_ROOT / "data/.turn_counter",
        PROJECT_ROOT / "logs",
    ]:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()

    cfg = PROJECT_ROOT / "data/novels/e2e-llm-test/config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "world.yaml").write_text(
        """world:
  name: 赤壤纪元
  era: 近未来公元2087年
  rules:
    - 火星殖民地依赖地球补给，水资源为最高战略资源
time:
  start: 拓荒历三年春
scopes:
  - id: main
    name: 主线
    description: 赤壤城殖民地主线
""",
        encoding="utf-8",
    )
    (cfg / "characters.yaml").write_text(
        """characters:
  - id: protagonist
    name: 林昭
    role: 水利工程师
    traits: [务实, 克制, 好奇]
    goals:
      - 修复赤壤城水循环系统的核心泄漏
    background: 地球移民二代，主动申请调往火星拓荒城，对封闭生态系统的极限有近乎执念的兴趣
""",
        encoding="utf-8",
    )
    (cfg / "runtime.yaml").write_text(
        """setting_research:
  enabled: false
  trigger: off
agents:
  characters:
    enabled_ids: [protagonist]
  scopes:
    enabled_ids: [main]
runtime:
  novel_run:
    initial_scope_id: main
    initial_time: 拓荒历三年春
    initial_place: 赤壤城水处理厂
""",
        encoding="utf-8",
    )
    # 已有设定（_has_setting 认定非新小说，设定阶段走「保留」分支）
    (cfg / "setting_research_output.yaml").write_text(
        """world_id: chi_rang_epoch
version: '0.1'
genre: 科幻
theme: 赤壤纪元
reference: 近未来火星殖民，水资源为核心战略资源
water_system:
  name: 水权配给体系
  description: 赤壤城的水资源按配给级分配，水循环工程师掌握殖民地命脉。
  levels:
  - id: w0
    name: 战略储备水
    order: 0
    note: 仅危机状态下启用的封存水源
  - id: w1
    name: 基础民生水
    order: 1
    note: 居民每日配给定额
tech_stage:
  name: 生态封闭度阶梯
  description: 殖民地封闭生态系统技术成熟度的分级，决定殖民地自持能力。
  levels:
  - id: t1
    name: 补给依赖期
    order: 1
    note: 生存依赖地球补给船
  - id: t2
    name: 半自持期
    order: 2
    note: 水与氧气循环自给，食物仍需补给
""",
        encoding="utf-8",
    )
    # 非初稿身份（跳过书名确认）
    (PROJECT_ROOT / "data/novels/e2e-llm-test/meta.yaml").write_text(
        "slug: e2e-llm-test\ntitle: 赤壤纪元（联调测试）\nstatus: design_done\n", encoding="utf-8"
    )
    # 绑定指针（含 slug，has_current_novel_pointer 才认）
    (PROJECT_ROOT / "config/current_novel.yaml").write_text(
        f"slug: e2e-llm-test\nroot: {PROJECT_ROOT / 'data/novels/e2e-llm-test'}\n",
        encoding="utf-8",
    )


@pytest.fixture
def restore_pointer():
    """测试后恢复 current_novel 指针原状（原无指针则删除）。"""
    pointer = PROJECT_ROOT / "config/current_novel.yaml"
    backup = pointer.read_bytes() if pointer.is_file() else None
    yield
    if backup is not None:
        pointer.write_bytes(backup)
    else:
        pointer.unlink(missing_ok=True)


class TestLLMLiveE2E:
    @pytest.mark.timeout(700)
    def test_one_turn_author_in_loop_with_real_llm(self, restore_pointer):
        llm_env = _load_llm_env()
        if not llm_env.get("DASHSCOPE_API_KEY") or llm_env.get("LLM_E2E") != "1":
            pytest.skip("未启用真实 LLM 联调（.env 需含 DASHSCOPE_API_KEY 与 LLM_E2E=1；默认跳过）")

        _setup_e2e_novel()

        env = {**os.environ, **llm_env}
        env["MIN_AUTOBOOK_TURNS"] = "1"
        env["MIN_AUTOBOOK_LOG_LEVEL"] = "INFO"
        env["MIN_AUTOBOOK_LOG_DIR"] = "/tmp/llm_e2e_logs"
        # 作者输入序列：保留设定 y / 菜单设定完成 y / 字数默认 / 无补充 / 同意生成 y / 阶段一 y / 阶段二 y
        author_inputs = "\n".join(["y", "y", "", "", "y", "y", "y"]) + "\n"

        proc = subprocess.run(
            [sys.executable, "-u", "run_novel_with_author.py"],
            cwd=PROJECT_ROOT,
            env=env,
            input=author_inputs,
            text=True,
            capture_output=True,
            timeout=600,
        )
        combined = proc.stdout + proc.stderr
        # 调试失败时可打印完整输出
        if proc.returncode != 0:
            print(combined[-6000:])

        assert proc.returncode == 0, f"作者在环一回合退出码 {proc.returncode}"
        # 主流程各阶段日志
        assert "设定阶段结束，进入正篇" in combined
        assert "已写回角色记忆" in combined
        # 正文落盘（范围事件正文单一数据源）
        turn_md = PROJECT_ROOT / "data/book/events/main/events/turn_0001.md"
        assert turn_md.is_file(), "事件簿正文未落盘"
        body = turn_md.read_text(encoding="utf-8")
        assert "## 摘要" in body and "## 正文" in body
        # 真实 LLM 内容（非 dummy 占位文案）
        assert "（壳）" not in body and "占位" not in body
        assert len(body) > 200, f"正文过短，疑似占位输出：{body[:200]}"
        print("\n[LLM E2E] 本回合正文预览：")
        print(body[:800])
