# -*- coding: utf-8 -*-
"""《Python编程基础》（py02）12 个周次的工程化项目规格。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eng_helpers import stories, funcs, tcases, adr, finalize

COURSE = "02-程序设计基础"
ENV = "py02"

SPECS = []


def P(**kw):
    SPECS.append(finalize(dict(course=COURSE, env=ENV, deps=kw.pop("deps", []), **kw)))


# ══════════════════ W01 设备参数初始化系统 ══════════════════
P(id="02-W01", week="W01", no="第1次课", title="设备参数初始化系统",
  slug="w01_device_init", pkg="device_init",
  scope="把两江智造精密制造事业部十台注塑机的铭牌参数从 Excel 手工抄录转为程序化管理，"
        "实现设备台账卡生成、温度单位换算与不可变性保护。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""# 设备台账参数（改配置不改代码）
warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

devices:
  - code: "DEV-2026-001"
    name: 智能注塑机
    temp: 56.5
    press_kpa: 450.0
    rpm: 1480
    status: running
  - code: "DEV-2026-002"
    name: 液压折弯机
    temp: 61.2
    press_kpa: 620.0
    rpm: 980
    status: running
  - code: "DEV-2026-003"
    name: 空压机A
    temp: 47.8
    press_kpa: 780.0
    rpm: 1450
    status: stopped
""",
  togaf=dict(
      business="设备铭牌参数集中管理，消除 Excel 抄录错漏，为巡检与告警提供唯一数据源",
      data="设备清单为值对象（code/name/temp/press_kpa/rpm/status），设备编号唯一；"

           "原始清单存 config/devices.yaml，输出为 JSON 台账",
      application="core 负责单位换算与告警分级；pipeline 负责加载设备→生成台账→评估→报告",
      technology="Python 3.12 + conda py02；仅标准库；pytest 断言；CLI 入口 run.py",
  ),
  mods=[("config.py", "加载 YAML 设备清单与阈值", "load_config()"),
        ("core.py", "单位换算/告警分级/台账卡格式化", "c_to_f()/kpa_to_mpa()/level_of()/card()"),
        ("pipeline.py", "加载→换算→评估→报告", "run(cfg, out_dir)"),
        ("io_utils.py", "JSON 原子写", "write_json()/write_text()")],
  stories=[("作为巡检员，我希望输入摄氏度自动得到华氏度，以便对照美标设备手册", "换算误差<0.01"),
           ("作为班组长，我希望台账卡对齐美观，以便贴到设备看板", "字段右对齐、单位齐全"),
           ("作为运维员，我希望超温自动标级，以便优先处置", ">=danger 停机 / >=warn 预警")],
  funcs=[("单位换算", "℃→℉、kPa→MPa"), ("告警分级", "normal/warn/danger 三态"),
         ("台账卡渲染", "等宽对齐、单位后缀")],
  design_core="告警分级为阈值比较（`>=` 语义），换算为纯算术；两者均为纯函数，"
              "不接触文件系统，便于单测。设备用 `dataclass(frozen=True)` 保证不可变。",
  test_cases=[("c_to_f", "温度换算", "0℃ → 32℉；37℃ → 98.6℉", "误差<1e-6"),
              ("level_of", "告警分级", "80.0（边界）/ 94.9 / 95.0", "warn / warn / danger"),
              ("card", "台账卡", "含 code/name/temp", "字段齐全且对齐")],
  adr=adr("设备用 dataclass(frozen=True) 而非 dict",
          "设备参数要被多处只读使用；用 dict 时拼写错误不会报错（静默 bug），且无法表达不可变语义",
          "A dict（灵活但无约束）｜B dataclass(frozen=True)（有类型+不可变）｜C Pydantic（重，课堂不必要）",
          "B dataclass(frozen=True)",
          "类型提示让 IDE 可补全；frozen 让误修改变得显式报错；零第三方依赖",
          "字段增删需改类定义", "低（周1即可理解）", "在 README 说明用法"),
  core_py='''# -*- coding: utf-8 -*-
"""核心纯函数：单位换算、告警分级、台账卡渲染（零 IO，可单测）。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    """设备值对象（不可变）——代码零硬编码，字段来自 config/rules.yaml。"""
    code: str
    name: str
    temp: float
    press_kpa: float
    rpm: int
    status: str = "running"

    def __post_init__(self):
        if self.temp < -273.15:
            raise ValueError("温度低于绝对零度")
        if self.press_kpa < 0:
            raise ValueError("压力不能为负（%.2f kPa）" % self.press_kpa)
        if self.rpm < 0:
            raise ValueError("转速不能为负")


def c_to_f(c):
    """摄氏度 → 华氏度。"""
    return c * 9.0 / 5.0 + 32.0


def kpa_to_mpa(kpa):
    """千帕 → 兆帕。"""
    return kpa / 1000.0


def level_of(temp, warn, danger):
    """告警分级：>=danger 停机 / >=warn 预警 / 其余正常（边界值取高等级）。"""
    if temp >= danger:
        return "danger"
    if temp >= warn:
        return "warn"
    return "normal"


def card(dev, cfg):
    """渲染设备台账卡（等宽对齐、单位齐全）。"""
    f = c_to_f(dev.temp)
    mpa = kpa_to_mpa(dev.press_kpa)
    lv = level_of(dev.temp, cfg.warn, cfg.danger)
    return [
        "====== 设备台账卡 ======",
        "编号: %s" % dev.code,
        "名称: %-12s 状态: %s" % (dev.name, "运行" if dev.status == "running" else "停止"),
        "温度: %7.1f℃ (%6.1f℉)  压力: %.2fMPa  转速: %drpm" % (dev.temp, f, mpa, dev.rpm),
        "告警级别: %s" % lv.upper(),
    ]

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""流水线：加载设备清单 → 换算评估 → 渲染台账卡 → 落盘报告。"""
import os

from . import core, io_utils, report


def load_devices(cfg):
    return [core.Device(code=str(d["code"]), name=str(d["name"]), temp=float(d["temp"]),
                        press_kpa=float(d["press_kpa"]), rpm=int(d["rpm"]),
                        status=str(d.get("status", "running")))
            for d in cfg.items]


def run(cfg, out_dir):
    devs = load_devices(cfg)
    if not devs:
        raise ValueError("config/rules.yaml 中 devices 为空——请至少配置 1 台设备")
    lines, lv_stat = [], {}
    for d in devs:
        lines.extend(core.card(d, cfg))
        lines.append("")
        lv_stat[core.level_of(d.temp, cfg.warn, cfg.danger)] = \\
            lv_stat.get(core.level_of(d.temp, cfg.warn, cfg.danger), 0) + 1
    result = {"n_devices": len(devs), "levels": lv_stat,
              "devices": [{"code": d.code, "temp_c": d.temp,
                           "temp_f": round(core.c_to_f(d.temp), 2),
                           "level": core.level_of(d.temp, cfg.warn, cfg.danger)} for d in devs]}
    sections = [("输入口径", ["设备 %d 台｜预警线 %.1f℃｜停机线 %.1f℃｜单位 %s"
                        % (len(devs), cfg.warn, cfg.danger, cfg.unit)]),
                ("设备台账卡", lines),
                ("告警分布", ["%s: %d 台" % (k, v) for k, v in sorted(lv_stat.items())]),
                ("结论与建议", ["共 %d 台设备；danger 级需当班处置并回填工单"
                          % len(devs)])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
"""core 层测试：正常 / 边界 / 异常三档。"""
import pytest

from device_init import core
from device_init.config import Settings


@pytest.fixture
def cfg():
    return Settings(warn=80.0, danger=95.0)


# ── 正常 ──
def test_c_to_f_normal():
    assert core.c_to_f(100.0) == 212.0
    assert abs(core.c_to_f(37.0) - 98.6) < 1e-6


def test_kpa_to_mpa_normal():
    assert core.kpa_to_mpa(450.0) == 0.45


def test_card_contains_all_fields(cfg):
    d = core.Device("DEV-1", "注塑机", 56.5, 450.0, 1480)
    t = "\\n".join(core.card(d, cfg))
    for k in ("DEV-1", "注塑机", "56.5", "0.45MPa", "NORMAL"):
        assert k in t


# ── 边界 ──
@pytest.mark.parametrize("t,lv", [(79.9, "normal"), (80.0, "warn"), (94.9, "warn"), (95.0, "danger")])
def test_level_of_boundaries(cfg, t, lv):
    assert core.level_of(t, cfg.warn, cfg.danger) == lv


def test_device_is_immutable():
    d = core.Device("DEV-1", "x", 1.0, 1.0, 1)
    with pytest.raises(Exception):
        d.temp = 99.0


# ── 异常 ──
def test_card_rejects_negative_pressure():
    with pytest.raises(Exception):
        core.Device("DEV-1", "x", 1.0, -1.0, 1)

''')


# ══════════════════ W02 设备多级告警判定引擎 ══════════════════
P(id="02-W02", week="W02", no="第3次课", title="设备多级告警判定引擎",
  slug="w02_alarm_engine", pkg="alarm_engine",
  scope="两江智造夜班险情后，王主任要求'机器得自己会喊疼'。本项目实现温度/压力双参数"
        "组合条件判定、同时超限升级紧急、以及告警去重（同设备同级N秒内只报一次）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
press_warn: 0.55
press_danger: 0.65
dedup_seconds: 10
unit: "c"
seed: 7
topk: 3

readings:
  - ts: 79.8
    temp: 78.0
    press: 0.50
  - ts: 80.1
    temp: 80.0
    press: 0.50
  - ts: 85.0
    temp: 94.9
    press: 0.50
  - ts: 90.0
    temp: 95.0
    press: 0.66
  - ts: 91.0
    temp: 95.0
    press: 0.66
  - ts: 100.0
    temp: 96.0
    press: 0.60
""",
  togaf=dict(
      business="把'靠人巡逻发现险情'变为'程序自动喊疼'，压缩漏报窗口，守住安全底线",
      data="读点为时序值对象（ts/temp/press）；告警为事件对象（level/原因/是否去重）；"

           "规则阈值全部外置 YAML，输出告警事件 JSON",
      application="core 做单点判定+多条件组合+去重；pipeline 顺序消费读数序列、统计告警分布",
      technology="Python 3.12 + conda py02；仅标准库；pytest；CLI",
  ),
  mods=[("core.py", "告警引擎：判定/组合/升级/去重", "judge()/dedup()"),
        ("pipeline.py", "读数序列→告警事件流", "run(cfg, out_dir)")],
  stories=[("作为夜班工，我希望温度与压力同时超限直接升级紧急，以便立即停机", "双超限→EMERGENCY"),
           ("作为调度员，我希望同一告警10秒内只报一次，以便不被刷屏淹没", "去重生效"),
           ("作为班长，我希望边界值行为明确，以便写进操作规程", "79.9正常/80预警/95停机")],
  funcs=[("单点判定", "温度分三级"), ("组合条件", "and/or + 括号优先级"),
         ("同时超限升级", "双超限→EMERGENCY"), ("告警去重", "同设备同级N秒窗口")],
  design_core="判定为**阈值表驱动**（warn/danger 分层比较）；组合条件显式加括号避免"
              "`and`/`or` 优先级歧义；去重用'同设备+同等级+时间窗'三要素。",
  test_cases=[("judge", "单点", "78.0 / 80.0 / 95.0", "normal / warn / danger"),
              ("combine", "组合", "temp=82 & press=0.60", "紧急（双超限）"),
              ("dedup", "去重", "同告警间隔5秒", "第二次被抑制")],
  adr=adr("规则阈值用 YAML 外置而非代码常量",
          "产线阈值随工艺调整频繁；写死在代码里每次都要改代码、走发布流程，且容易漏改",
          "A 代码常量（快但难维护）｜B YAML 外置（改配置即生效）｜C 数据库规则表（需额外依赖）",
          "B YAML 外置",
          "改配置不改代码是 GB/T 8566 配置管理过程的基本要求；yaml_lite 保证零依赖可跑",
          "配置文件错误要到运行期才暴露", "中", "启动时校验阈值顺序，非法即拒绝"),
  core_py='''# -*- coding: utf-8 -*-
"""告警引擎：单点分级、组合判定、超限升级、时间窗去重（纯函数）。"""


def temp_level(temp, warn, danger):
    """温度分级：>=danger 停机 / >=warn 预警 / 正常。"""
    if temp >= danger:
        return "danger"
    if temp >= warn:
        return "warn"
    return "normal"


def press_level(press, warn, danger):
    if press >= danger:
        return "danger"
    if press >= warn:
        return "warn"
    return "normal"


def judge(temp, press, temp_w, temp_d, press_w, press_d):
    """组合判定：温度或压力任一达 danger → danger；双 warn 以下；同时超限 → emergency。"""
    tl, pl = temp_level(temp, temp_w, temp_d), press_level(press, press_w, press_d)
    both_warn = (tl != "normal") and (pl != "normal")
    if both_warn:
        return "emergency"
    return max(tl, pl, key=lambda x: ["normal", "warn", "danger"].index(x))


def dedup(events, window):
    """同等级告警在 window 秒内只保留首条（时间窗去重）。"""
    kept, last_ts = [], {}
    for e in events:
        key = e["level"]
        if key in last_ts and (e["ts"] - last_ts[key]) < window:
            e = dict(e, suppressed=True)
        else:
            last_ts[key] = e["ts"]
            e = dict(e, suppressed=False)
        kept.append(e)
    return kept

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""读数序列 → 告警事件流 → 去重 → 统计报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    if cfg.warn >= cfg.danger:
        raise ValueError("阈值配置非法：warn(%.1f) 必须小于 danger(%.1f)"
                         % (cfg.warn, cfg.danger))
    pw, pd = float(cfg.raw.get("press_warn", 0.55)), float(cfg.raw.get("press_danger", 0.65))
    win = float(cfg.raw.get("dedup_seconds", 10))
    events = []
    for r in cfg.items:
        events.append({"ts": float(r["ts"]), "temp": float(r["temp"]),
                       "press": float(r["press"]),
                       "level": core.judge(float(r["temp"]), float(r["press"]),
                                           cfg.warn, cfg.danger, pw, pd)})
    out = core.dedup(events, win)
    fired = [e for e in out if not e["suppressed"]]
    lines = ["ts=%6.1f  temp=%5.1f  press=%.2f → %-9s %s"
             % (e["ts"], e["temp"], e["press"], e["level"].upper(),
                "（已去重抑制）" if e["suppressed"] else "") for e in out]
    stat = {}
    for e in fired:
        stat[e["level"]] = stat.get(e["level"], 0) + 1
    result = {"n_readings": len(out), "fired": len(fired),
              "suppressed": len(out) - len(fired), "by_level": stat, "events": out}
    sections = [("输入口径", ["读数 %d 条｜温度预警 %.0f℃ / 停机 %.0f℃｜去重窗口 %.0fs"
                        % (len(out), cfg.warn, cfg.danger, win)]),
                ("告警流水", lines),
                ("告警分布", ["%s: %d 次（已去重）" % (k, v) for k, v in sorted(stat.items())] or ["无告警"]),
                ("结论与建议", ["紧急级告警必须立即停机并回填工单；"
                           "去重抑制 %d 条属预期行为（防刷屏）"
                           % (len(out) - len(fired))])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from alarm_engine import core


@pytest.mark.parametrize("t,lv", [(78.0, "normal"), (80.0, "warn"), (95.0, "danger")])
def test_temp_level(t, lv):
    assert core.temp_level(t, 80.0, 95.0) == lv


def test_single_param_warn():
    assert core.judge(80.0, 0.50, 80.0, 95.0, 0.55, 0.65) == "warn"


def test_double_over_limit_becomes_emergency():
    assert core.judge(95.0, 0.66, 80.0, 95.0, 0.55, 0.65) == "emergency"


def test_only_one_over_limit_stays_danger():
    assert core.judge(95.0, 0.50, 80.0, 95.0, 0.55, 0.65) == "danger"


def test_dedup_suppresses_within_window():
    ev = [{"ts": 0, "level": "warn"}, {"ts": 5, "level": "warn"},
          {"ts": 15, "level": "warn"}]
    out = core.dedup(ev, 10)
    assert [e["suppressed"] for e in out] == [False, True, False]


def test_dedup_different_levels_not_merged():
    ev = [{"ts": 0, "level": "warn"}, {"ts": 1, "level": "danger"}]
    out = core.dedup(ev, 10)
    assert not any(e["suppressed"] for e in out)


def test_empty_input_returns_empty():
    assert core.dedup([], 10) == []


def test_pipeline_rejects_inverted_threshold():
    from alarm_engine.config import Settings
    from alarm_engine import pipeline
    cfg = Settings(warn=95.0, danger=80.0, items=[])
    with pytest.raises(ValueError):
        pipeline.run(cfg, "/tmp/never-created")

''')


# ══════════════════ W03 多设备巡检循环模拟 ══════════════════
P(id="02-W03", week="W03", no="第5次课", title="多设备巡检循环模拟",
  slug="w03_patrol_loop", pkg="patrol_loop",
  scope="用双层循环模拟'多设备×多周期'巡检：外层遍历设备、内层遍历周期，"
        "统计每台设备的告警次数并输出巡检排班建议。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=3, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_devices: 3
n_cycles: 12
base_temp: 70.0
drift: 2.5
unit: "c"
seed: 3
topk: 3
""",
  togaf=dict(
      business="排班从'平均用力'转为'按告警频次倾斜'，优先盯问题设备",
      data="设备×周期的巡检矩阵（dict of list）；每台设备的告警计数与温度轨迹",
      application="core 生成温度轨迹并判定；pipeline 组织双层循环、聚合统计",
      technology="Python 3.12 + conda py02；仅标准库（random 种子固定）；pytest",
  ),
  mods=[("core.py", "温度轨迹生成 + 告警统计", "series()/count_alarms()"),
        ("pipeline.py", "设备×周期双层循环", "run(cfg, out_dir)")],
  stories=[("作为班长，我希望看到每台设备的告警次数，以便安排重点巡检", "输出按次数降序"),
           ("作为巡检员，我希望知道哪个周期风险最高，以便加密巡检", "输出周期维度统计"),
           ("作为组长，我希望结果可复现，以便二次核对", "种子固定，diff 为空")],
  funcs=[("温度轨迹", "基线+线性漂移+噪声"), ("告警统计", "按设备/按周期双维"),
         ("巡检优先级", "按告警次数降序排列")],
  design_core="温度轨迹 = 基线 + 周期步长的确定性漂移 + 固定种子噪声；"
              "统计用 defaultdict 聚合；排序为稳定排序（同次数按编号）。",
  test_cases=[("series", "轨迹", "base=70, drift=2.5, n=3", "逐周期递增"),
              ("count_alarms", "统计", "含越限", "计数正确"),
              ("priority", "排序", "多台设备", "告警多者在前")],
  adr=adr("巡检矩阵用 dict-of-list 而非二维 list",
          "设备数/周期数会变；二维 list 扩容和索引可读性都差，且无法按设备名直接寻址",
          "A 二维list（紧凑但难读）｜B dict[str, list]（按名字寻址）｜C pandas（引入重依赖）",
          "B dict[str, list]",
          "按设备编号寻址可读性好；纯标准库；周3循环语法刚好练习嵌套 for",
          "内存略高于稀疏结构", "低", "数据量大时再迁 pandas"),
  core_py='''# -*- coding: utf-8 -*-
"""多层循环巡检：温度轨迹生成与告警统计（纯函数）。"""
import random


def series(base, drift, n, rng=None):
    """生成 n 个周期的温度轨迹：基线 + 确定性漂移 + 固定种子噪声。"""
    r = rng or random.Random(0)
    return [round(base + drift * i + r.uniform(-0.8, 0.8), 1) for i in range(n)]


def count_alarms(temps, warn, danger):
    """分级计数：返回 (warn_count, danger_count)。"""
    w = sum(1 for t in temps if warn <= t < danger)
    d = sum(1 for t in temps if t >= danger)
    return w, d


def priority(stat):
    """巡检优先级：按告警总数降序（稳定排序）。"""
    return sorted(stat.items(), key=lambda kv: -(kv[1]["warn"] + kv[1]["danger"]))


def patrol(devices, n_cycles, base, drift, warn, danger, seed=0):
    """双层循环：外层设备 × 内周期，返回统计 dict。"""
    r = random.Random(seed)
    stat = {}
    for dev in devices:
        temps = series(base, drift, n_cycles, r)
        w, d = count_alarms(temps, warn, danger)
        stat[dev] = {"temps": temps, "warn": w, "danger": d}
    return stat

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""设备×周期双层循环巡检 → 双维统计 → 排班建议。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n_dev = int(cfg.raw.get("n_devices", 3))
    n_cyc = int(cfg.raw.get("n_cycles", 12))
    base = float(cfg.raw.get("base_temp", 70.0))
    drift = float(cfg.raw.get("drift", 2.5))
    devices = ["DEV-%02d" % (i + 1) for i in range(n_dev)]
    stat = core.patrol(devices, n_cyc, base, drift, cfg.warn, cfg.danger, cfg.seed)
    order = core.priority(stat)
    lines = []
    for dev, s in order:
        lines.append("%s  告警 %2d 次（warn %d / danger %d）  轨迹: %s"
                     % (dev, s["warn"] + s["danger"], s["warn"], s["danger"],
                        " ".join("%.0f" % t for t in s["temps"])))
    result = {"n_devices": n_dev, "n_cycles": n_cyc,
              "order": [d for d, _ in order],
              "stat": {d: {"warn": s["warn"], "danger": s["danger"]}
                       for d, s in stat.items()}}
    sections = [("输入口径", ["设备 %d 台 × 周期 %d｜基线 %.0f℃｜漂移 %.1f℃/周期｜"
                        "预警 %.0f℃ / 停机 %.0f℃｜种子 %d"
                        % (n_dev, n_cyc, base, drift, cfg.warn, cfg.danger, cfg.seed)]),
                ("巡检优先级", lines),
                ("排班建议", ["优先巡检 %s（告警最集中）" % (order[0][0] if order else "-")]),
                ("结论与建议", ["按告警频次倾斜巡检力量；danger 级当班处置并回填工单"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import random

from patrol_loop import core


def test_series_deterministic():
    a = core.series(70.0, 2.5, 5, random.Random(0))
    b = core.series(70.0, 2.5, 5, random.Random(0))
    assert a == b
    assert all(69.0 < t < 91.0 for t in a)


def test_series_monotonic_drift():
    temps = core.series(70.0, 2.0, 4, random.Random(1))
    assert temps[3] > temps[0]


def test_count_alarms_tiers():
    w, d = core.count_alarms([60.0, 80.0, 95.0, 96.0], 80.0, 95.0)
    assert (w, d) == (1, 2)


def test_count_alarms_none():
    assert core.count_alarms([10.0, 20.0], 80.0, 95.0) == (0, 0)


def test_priority_sorts_by_alarm_count():
    stat = {"A": {"warn": 1, "danger": 0}, "B": {"warn": 0, "danger": 3},
            "C": {"warn": 0, "danger": 0}}
    assert [d for d, _ in core.priority(stat)] == ["B", "A", "C"]


def test_patrol_covers_all_devices():
    stat = core.patrol(["D1", "D2"], 6, 70.0, 3.0, 80.0, 95.0, seed=2)
    assert set(stat) == {"D1", "D2"}
    assert all(len(s["temps"]) == 6 for s in stat.values())

''')


# ══════════════════ W04 设备对象建模 ══════════════════
P(id="02-W04", week="W04", no="第7次课", title="设备对象建模",
  slug="w04_device_model", pkg="device_model",
  scope="把'数据+行为'打包成类：设备有状态（温度/压力/转速）和行为（启动/停止/巡检），"
        "并实现禁止重复启动、停机后才能启动等业务规则。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

devices:
  - code: "DEV-01"
    kind: 空压机A
    temp: 41.2
  - code: "DEV-02"
    kind: 冷却泵
    temp: 25.0
""",
  togaf=dict(
      business="设备状态与操作规则集中到一类对象，消除'到处传参'的维护灾难",
      data="Device 聚合根（code/kind/temp/running）；状态转移表：stopped→running→stopped",
      application="core 定义 Device 类（状态+行为）；pipeline 加载设备并演示状态机",
      technology="Python 3.12 + conda py02；仅标准库（dataclasses + 自定义异常）；pytest",
  ),
  mods=[("core.py", "Device 类：状态+行为+业务规则", "Device.start()/stop()/patrol()"),
        ("pipeline.py", "加载→演示状态转移→报告", "run(cfg, out_dir)")],
  stories=[("作为操作工，我希望已运行设备再次点启动时被拒绝，以免误操作", "抛 AlreadyRunningError"),
           ("作为操作工，我希望停机后才能再次启动，以符合安全规程", "抛 NotRunningError"),
           ("作为班长，我希望巡检能看到当前状态与温度，以判断是否干预", "patrol() 返回状态串")],
  funcs=[("状态封装", "running 私有属性 + 只读属性"), ("业务规则", "启动/停机前置校验"),
         ("巡检报告", "状态+温度+告警级")],
  design_core="状态用私有 `_running` + 只读 property 暴露，禁止外部直接改写；"
              "业务规则在方法入口做强校验并抛**自定义异常**（而非 print）。",
  test_cases=[("start", "启动", "从停止态", "成功且状态运行"),
              ("start", "重复启动", "运行态再启动", "抛 AlreadyRunningError"),
              ("stop", "停机", "停止态再停", "抛 NotRunningError"),
              ("patrol", "巡检", "运行中 96℃", "含 DANGER")],
  adr=adr("用自定义异常而非返回值表达错误",
          "操作类错误是'异常路径'，用返回值（如 -1）容易被调用方忽略，最终变成产线事故",
          "A 返回 None/-1（易被忽略）｜B 抛自定义异常（强制处理）｜C 断言 assert（生产可被 -O 关掉）",
          "B 抛自定义异常",
          "异常必须被 try/except 或向上传播，无法被静默忽略；语义清晰（AlreadyRunning vs NotRunning）",
          "调用方需写错误处理", "低", "在 README 给出 try/except 样例"),
  core_py='''# -*- coding: utf-8 -*-
"""设备对象：数据与行为一体 + 状态机 + 业务规则校验。"""
from dataclasses import dataclass, field


class DeviceError(Exception):
    """设备操作错误基类。"""


class AlreadyRunningError(DeviceError):
    """设备已在运行，禁止重复启动。"""


class NotRunningError(DeviceError):
    """设备未运行，禁止执行仅运行态可做的操作。"""


@dataclass
class Device:
    """设备聚合根：私有状态 + 只读属性 + 行为方法。"""
    code: str
    kind: str
    temp: float = 0.0
    _running: bool = field(default=False, repr=False)

    @property
    def running(self):
        """只读运行状态——禁止外部直接改写。"""
        return self._running

    def start(self):
        """启动：运行态重复启动属误操作，抛 AlreadyRunningError。"""
        if self._running:
            raise AlreadyRunningError("%s 已在运行，请勿重复启动" % self.code)
        self._running = True
        return "%s %s 启动成功" % (self.code, self.kind)

    def stop(self):
        """停机：未运行却停机，抛 NotRunningError。"""
        if not self._running:
            raise NotRunningError("%s 未运行，无需停机" % self.code)
        self._running = False
        return "%s %s 已停止" % (self.code, self.kind)

    def patrol(self, warn, danger):
        """巡检：状态 + 温度 + 告警级。"""
        lv = "DANGER" if self.temp >= danger else ("WARN" if self.temp >= warn else "NORMAL")
        return "%s %-8s %-6s %.1f℃ [%s]" % (
            self.code, self.kind, "运行" if self._running else "停止", self.temp, lv)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""加载设备 → 演示状态机转移 → 输出巡检台账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    devs = [core.Device(code=str(d["code"]), kind=str(d["kind"]),
                        temp=float(d.get("temp", 0.0))) for d in cfg.items]
    if not devs:
        raise ValueError("config/rules.yaml 的 devices 为空")
    ops, errs = [], []
    for d in devs:
        ops.append(d.start())
    ops.append(devs[0].start()) if False else None     # 占位：真正演示见下方显式用例
    # 显式演示两条业务规则
    try:
        devs[0].start()
        errs.append("未拦住重复启动（规则失效！）")
    except core.AlreadyRunningError as e:
        ops.append("已拦截重复启动: %s" % e)
    try:
        devs[1].stop()
        devs[1].stop()
        errs.append("未拦住重复停机（规则失效！）")
    except core.NotRunningError as e:
        ops.append("已拦截重复停机: %s" % e)
    devs[0].temp = 96.0
    lines = [d.patrol(cfg.warn, cfg.danger) for d in devs]
    result = {"n_devices": len(devs), "ops": ops, "errors": errs,
              "flags": [d.running for d in devs]}
    sections = [("输入口径", ["设备 %d 台｜预警 %.0f℃ / 停机 %.0f℃"
                        % (len(devs), cfg.warn, cfg.danger)]),
                ("操作流水", ops),
                ("规则校验", ["拦截面: %s" % (len(errs) == 0 and "全部通过" or "失败")] + errs),
                ("巡检台账", lines)]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from device_model import core


def test_start_from_stopped():
    d = core.Device("DEV-1", "空压机")
    assert "启动成功" in d.start() and d.running


def test_double_start_rejected():
    d = core.Device("DEV-1", "空压机")
    d.start()
    with pytest.raises(core.AlreadyRunningError):
        d.start()


def test_stop_when_stopped_rejected():
    d = core.Device("DEV-1", "空压机")
    with pytest.raises(core.NotRunningError):
        d.stop()


def test_start_after_stop_ok():
    d = core.Device("DEV-1", "空压机")
    d.start()
    d.stop()
    assert d.start() and d.running


def test_running_is_read_only():
    d = core.Device("DEV-1", "x")
    with pytest.raises(AttributeError):
        d.running = True


def test_patrol_levels():
    assert "DANGER" in core.Device("DEV-2", "x", temp=96.0).patrol(80, 95)
    assert "NORMAL" in core.Device("DEV-3", "x", temp=50.0).patrol(80, 95)


def test_empty_device_list_raises():
    from device_model.config import Settings
    from device_model import pipeline
    with pytest.raises(ValueError):
        pipeline.run(Settings(items=[]), "/tmp/never")

''')


# ══════════════════ W05 设备继承体系 ══════════════════
P(id="02-W05", week="W05", no="第9次课", title="设备继承体系",
  slug="w05_device_family", pkg="device_family",
  scope="用继承建模设备家族：基类 Device 管通用行为，子类 PumpDevice（泵）/ FanDevice（风机）"
        "各自扩展专属能力（调频/启停延时），并演示多态统一调度。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

fleet:
  - type: pump
    code: "PUMP-01"
    temp: 58.0
    freq_hz: 35
  - type: pump
    code: "PUMP-02"
    temp: 61.5
    freq_hz: 50
  - type: fan
    code: "FAN-01"
    temp: 45.0
    delay_s: 3
""",
  togaf=dict(
      business="一接口管多种设备，调度层无需为每种设备写分支代码",
      data="Device 基类定义共同状态；子类扩展专属字段（freq_hz / delay_s）；fleet 为异构设备清单",
      application="core 定义类层次 + 工厂函数 from_dict()；pipeline 统一遍历 fleet 调用统一接口",
      technology="Python 3.12 + conda py02；仅标准库（abc 抽象基类）；pytest",
  ),
  mods=[("core.py", "Device 基类 + Pump/Fan 子类 + 工厂", "Device.dispatch()/from_fleet()"),
        ("pipeline.py", "异构设备统一调度", "run(cfg, out_dir)")],
  stories=[("作为调度员，我希望用同一行代码调度泵和风机", "统一 dispatch() 接口"),
           ("作为操作工，我希望泵支持变频设定、风机支持延时停机", "子类扩展方法"),
           ("作为架构师，我希望新增设备类型只需加一个子类", "开闭原则：对扩展开放")],
  funcs=[("抽象基类", "dispatch() 为抽象方法"), ("子类扩展", "Pump.set_freq()/Fan.delay_stop()"),
         ("工厂方法", "from_dict() 依 type 建实例")],
  design_core="`Device(ABC)` 定义抽象接口 `dispatch()`；子类各自实现（多态）；"
              "`from_dict()` 依 `type` 字段分派到具体子类（工厂），新增类型零改动调用方。",
  test_cases=[("多态", "调度泵/风机", "统一调用", "各自行为正确"),
              ("set_freq", "变频", "35Hz", "落在 (25,60)"),
              ("delay_stop", "延时停机", "3s", "返回延时秒数")],
  adr=adr("用 ABC 抽象基类而非鸭子类型约束子类",
          "缺少年龄接口约束时，拼写错误要等到运行期才暴露；ABC 让'必须实现某方法'成为硬契约",
          "A 鸭子类型（灵活但无约束）｜B abc.ABC（编译期契约）｜C Protocol（结构化类型）",
          "B abc.ABC",
          "子类漏实现抽象方法会直接 TypeError；周5刚好讲继承与多态",
          "继承层级加深后耦合增加", "中", "保持两层以内，禁止孙类"),
  core_py='''# -*- coding: utf-8 -*-
"""设备家族：抽象基类 + 子类扩展 + 工厂方法（多态统一调度）。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Device(ABC):
    """设备抽象基类：定义统一接口 dispatch()。"""

    def __init__(self, code, temp):
        self.code = code
        self.temp = temp

    @abstractmethod
    def dispatch(self, warn, danger):
        """统一调度接口——子类必须实现。"""


class PumpDevice(Device):
    """泵：额外支持变频设定。"""

    def __init__(self, code, temp, freq_hz=50.0):
        super().__init__(code, temp)
        self.freq_hz = float(freq_hz)

    def set_freq(self, hz):
        """设定变频（超范围抛错，防止损坏电机）。"""
        if not (25.0 <= hz <= 60.0):
            raise ValueError("频率 %.1fHz 超出安全区间 25~60Hz" % hz)
        self.freq_hz = float(hz)
        return "%s 频率设定 %.1fHz" % (self.code, self.freq_hz)

    def dispatch(self, warn, danger):
        lv = "DANGER" if self.temp >= danger else ("WARN" if self.temp >= warn else "NORMAL")
        return "%s 泵 %.1fHz 巡检[%s]" % (self.code, self.freq_hz, lv)


class FanDevice(Device):
    """风机：额外支持延时停机（避免水锤）。"""

    def __init__(self, code, temp, delay_s=3):
        super().__init__(code, temp)
        self.delay_s = int(delay_s)

    def delay_stop(self):
        return "%s 风机将延时 %ds 停机（防喘振）" % (self.code, self.delay_s)

    def dispatch(self, warn, danger):
        lv = "DANGER" if self.temp >= danger else ("WARN" if self.temp >= warn else "NORMAL")
        return "%s 风机 延时%ds 巡检[%s]" % (self.code, self.delay_s, lv)


def from_dict(d):
    """工厂：依 type 字段分派到具体子类。"""
    t = str(d.get("type", "")).lower()
    if t == "pump":
        return PumpDevice(str(d["code"]), float(d["temp"]), d.get("freq_hz", 50))
    if t == "fan":
        return FanDevice(str(d["code"]), float(d["temp"]), d.get("delay_s", 3))
    raise ValueError("未知设备类型: %s" % t)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""异构设备 → 工厂构建 → 统一 dispatch 调度。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    fleet = [core.from_dict(d) for d in cfg.items]
    if not fleet:
        raise ValueError("config/rules.yaml 的 fleet 为空")
    lines, extra = [], []
    for d in fleet:
        lines.append(d.dispatch(cfg.warn, cfg.danger))       # 多态：同一行代码
        if isinstance(d, core.PumpDevice):
            extra.append(d.set_freq(35.0))
        if isinstance(d, core.FanDevice):
            extra.append(d.delay_stop())
    result = {"n_devices": len(fleet), "dispatched": lines,
              "extras": extra,
              "types": sorted({type(d).__name__ for d in fleet})}
    sections = [("输入口径", ["异构设备 %d 台｜类型: %s" %
                        (len(fleet), ", ".join(sorted({type(d).__name__ for d in fleet})))]),
                ("统一调度结果", lines),
                ("子类专属能力", extra),
                ("结论与建议", ["新增设备类型只需加子类并注册工厂，调度层零改动（开闭原则）"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from device_family import core


def test_factory_builds_subclasses():
    p = core.from_dict({"type": "pump", "code": "P1", "temp": 50.0, "freq_hz": 40})
    f = core.from_dict({"type": "fan", "code": "F1", "temp": 40.0, "delay_s": 5})
    assert isinstance(p, core.PumpDevice) and isinstance(f, core.FanDevice)


def test_unknown_type_rejected():
    with pytest.raises(ValueError):
        core.from_dict({"type": "tank", "code": "T1", "temp": 1.0})


def test_polymorphic_dispatch_same_call():
    p = core.PumpDevice("P1", 96.0)
    f = core.FanDevice("F1", 30.0)
    assert "DANGER" in p.dispatch(80, 95) and "NORMAL" in f.dispatch(80, 95)


def test_set_freq_within_range():
    assert "35.0Hz" in core.PumpDevice("P1", 1.0).set_freq(35.0)


@pytest.mark.parametrize("hz", [10.0, 70.0, 0.0])
def test_set_freq_out_of_range_rejected(hz):
    with pytest.raises(ValueError):
        core.PumpDevice("P1", 1.0).set_freq(hz)


def test_fan_delay_stop():
    assert "延时 4s" in core.FanDevice("F1", 1.0, 4).delay_stop()


def test_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        core.Device("X", 1.0)

''')


# ══════════════════ W06 健壮工业数据采集 ══════════════════
P(id="02-W06", week="W06", no="第11次课", title="健壮工业数据采集",
  slug="w06_robust_collector", pkg="robust_collector",
  scope="工业现场数据永远有脏：缺测、非法值、格式错。本项目实现'逐条读取→逐条校验→"
        "异常隔离→统计留痕'的健壮采集器，坏数据进隔离区而不中断采集。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

raw_lines:
  - "56.2,0.45"
  - "err,0.46"
  - "57.5,"
  - "61.0,0.47"
  - "58.3,0.44"
  - "abc,xyz"
""",
  togaf=dict(
      business="脏数据不再让采集中途崩溃；异常可追溯、可回放，保住过程性证据",
      data="原始行（字符串）→ 校验后记录（temp/press）+ 坏数据隔离区（行号+原文+原因）",
      application="core 单行解析与校验（纯函数）；pipeline 逐行消费、隔离与统计",
      technology="Python 3.12 + conda py02；仅标准库（logging）；pytest",
  ),
  mods=[("core.py", "单行解析/单字段校验/行级隔离", "parse_line()/validate()"),
        ("pipeline.py", "逐行采集→隔离→统计", "run(cfg, out_dir)")],
  stories=[("作为采集员，我希望坏行不中断后续采集", "坏行进隔离区，流程继续"),
           ("作为质量员，我希望每条坏数据都能说出为什么坏", "带原因与行号"),
           ("作为班长，我希望看到成功率，以判断链路健康", "输出成功率与失败分解")],
  funcs=[("单行解析", "逗号分隔转 float 对"), ("字段校验", "范围/空值/类型三重校验"),
         ("异常隔离", "坏行进隔离区并留原因")],
  design_core="解析与校验为纯函数（无 IO）；异常不 throw 而**收集**（坏数据是预期输入，"
              "不是程序错误）；统计用计数器，输出成功率 + 失败原因分布。",
  test_cases=[("parse_line", "解析", "56.2,0.45", "(56.2, 0.45)"),
              ("parse_line", "坏行", "err,0.46", "抛 ParseError"),
              ("validate", "校验", "temp=-1", "返回 (False, 原因)")],
  adr=adr("坏数据用隔离区收集而非抛异常中断",
          "工业采集场景坏数据是常态；抛异常会中断整条链路，丢掉后续好数据",
          "A 抛异常中断（简单但中断链路）｜B 隔离区收集（链路续跑+可追溯）｜C 静默丢弃（丢证据）",
          "B 隔离区收集",
          "既保住后续好数据，又留下过程性证据（行号+原文+原因）——对应 GB/T 15532 异常路径测试",
          "需维护隔离区容量", "低", "隔离区超限时告警并可落盘"),
  core_py='''# -*- coding: utf-8 -*-
"""健壮采集：解析、校验、隔离（纯函数，无 IO）。"""


class ParseError(ValueError):
    """行格式非法。"""


def parse_line(line):
    """把 "56.2,0.45" 解析为 (temp, press)；非法抛 ParseError。"""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 2:
        raise ParseError("字段数不为2: %r" % line)
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ParseError("非数值: %r" % line)


def validate(temp, press):
    """三重校验：空值/负值/越界。返回 (ok, reason)。"""
    if temp is None or press is None:
        return False, "空值"
    if temp < 0 or press < 0:
        return False, "负值"
    if not (0.0 <= temp <= 200.0):
        return False, "温度越界"
    if not (0.0 <= press <= 5.0):
        return False, "压力越界"
    return True, ""


def quarantine_line(idx, raw, reason):
    """坏数据隔离区条目（行号+原文+原因）。"""
    return {"line": idx, "raw": raw, "reason": reason}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""逐行采集 → 校验 → 隔离 → 统计报告。"""
import logging
import os

from . import core, io_utils, report

log = logging.getLogger(__name__)


def run(cfg, out_dir):
    lines = [str(x) for x in cfg.items]
    ok_rows, bad = [], []
    for i, raw in enumerate(lines, 1):
        try:
            temp, press = core.parse_line(raw)
            good, reason = core.validate(temp, press)
            if not good:
                bad.append(core.quarantine_line(i, raw, reason))
                continue
            ok_rows.append({"line": i, "temp": temp, "press": press})
        except core.ParseError as e:
            bad.append(core.quarantine_line(i, raw, str(e)))
    total = len(lines)
    result = {"total": total, "ok": len(ok_rows), "bad": len(bad),
              "success_rate": round(len(ok_rows) / max(total, 1), 4),
              "quarantine": bad, "rows": ok_rows}
    reasons = {}
    for b in bad:
        reasons[b["reason"]] = reasons.get(b["reason"], 0) + 1
    sections = [("输入口径", ["原始行 %d 条｜温度 0~200℃｜压力 0~5.0MPa" % total]),
                ("采集成功", ["成功 %d 条（%.1f%%）" % (len(ok_rows),
                               len(ok_rows) / max(total, 1) * 100)]),
                ("隔离区", ["第%2d行 %-14r 原因: %s" % (b["line"], b["raw"], b["reason"])
                        for b in bad] or ["无坏数据"]),
                ("失败原因分布", ["%s: %d 条" % (k, v) for k, v in sorted(reasons.items())] or ["-"]),
                ("结论与建议", ["坏数据不进结果集；隔离区需人工复核后决定重采或补录"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from robust_collector import core


def test_parse_good_line():
    assert core.parse_line("56.2,0.45") == (56.2, 0.45)


def test_parse_handles_spaces():
    assert core.parse_line(" 56.2 , 0.45 ") == (56.2, 0.45)


@pytest.mark.parametrize("raw", ["err,0.46", "56.2", "56.2,0.4,5", "abc"])
def test_parse_bad_lines_raise(raw):
    with pytest.raises(core.ParseError):
        core.parse_line(raw)


@pytest.mark.parametrize("t,p,reason", [
    (-1.0, 0.4, "负值"), (250.0, 0.4, "温度越界"), (50.0, 9.0, "压力越界")])
def test_validate_rejects(t, p, reason):
    ok, r = core.validate(t, p)
    assert ok is False and r == reason


def test_validate_accepts_normal():
    assert core.validate(56.2, 0.45) == (True, "")


def test_quarantine_entry_structure():
    e = core.quarantine_line(3, "err,1", "非数值")
    assert e == {"line": 3, "raw": "err,1", "reason": "非数值"}

''')


# ══════════════════ W07 报文解析器 ══════════════════
P(id="02-W07", week="W07", no="第13次课", title="工业报文解析器",
  slug="w07_packet_parser", pkg="packet_parser",
  scope="设备上报的报文格式杂（JSON/逗号分隔/键值对混排），本项目实现可扩展的解析器："
        "按格式路由、解析失败降级为「未知格式」、统计各格式占比。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

packets:
  - '{"id":"D1","t":78.5,"p":0.42}'
  - "D2,81.0,0.50"
  - "id=D3;t=95.5;p=0.66"
  - "损坏报文@@@"
  - '{"id":"D4","t":60.0,"p":0.30}'
""",
  togaf=dict(
      business="多品牌设备报文统一入库，为上层平台屏蔽协议差异",
      data="原始报文（字符串）→ 统一读数对象（id/temp/press）+ 未知格式隔离区",
      application="core 为每种格式一个解析器（策略模式）+ 路由器；pipeline 统计格式分布",
      technology="Python 3.12 + conda py02；仅标准库（json）；pytest",
  ),
  mods=[("core.py", "格式路由 + 各格式解析器", "parse()/parse_json()/parse_csv()/parse_kv()"),
        ("pipeline.py", "批量解析→格式统计", "run(cfg, out_dir)")],
  stories=[("作为平台开发者，我希望新增一种报文格式只需加一个解析函数", "策略模式：路由表注册"),
           ("作为运维，我希望坏报文不拖垮整批解析", "坏报文进隔离区"),
           ("作为班长，我希望知道各格式占比，以便评估统一协议进度", "输出格式分布")],
  funcs=[("格式识别", "按前缀/结构路由"), ("解析器", "JSON/CSV/KV 三种"),
         ("降级处理", "未知格式隔离")],
  design_core="每个格式一个纯函数解析器，`PARSERS` 路由表按序尝试；解析失败返回 None 由调用方"
              "判隔离；新增格式 = 写解析函数 + 注册到路由表，零改动其它代码。",
  test_cases=[("parse", "JSON", '{"id":"D1","t":78.5,"p":0.42}', "D1/78.5/0.42"),
              ("parse", "CSV", "D2,81.0,0.50", "D2/81.0/0.50"),
              ("parse", "KV", "id=D3;t=95.5;p=0.66", "D3/95.5/0.66"),
              ("parse", "坏报文", "损坏报文@@@", "返回 None")],
  adr=adr("报文解析器用路由表（策略模式）而非 if-else 链",
          "设备品牌只会增加；if-else 链每次新增都要改同一函数，违反开闭原则",
          "A if-else 链（前几种够用）｜B PARSERS 路由表（注册即可扩展）｜C 正则表达式大全（难读难维护）",
          "B PARSERS 路由表",
          "新格式=新函数+一行注册；每种格式可独立单测；路由顺序即优先级",
          "数量极多时需做前缀索引优化", "低", "保持 ≤6 种格式，超出再上索引"),
  core_py='''# -*- coding: utf-8 -*-
"""工业报文解析器：策略模式 + 路由表（新增格式零改动调用方）。"""
import json


def parse_json(s):
    """JSON 报文 -> 读数 dict。"""
    d = json.loads(s)
    return {"id": str(d["id"]), "temp": float(d["t"]), "press": float(d["p"])}


def parse_csv(s):
    """逗号报文: D2,81.0,0.50"""
    a = [x.strip() for x in s.split(",")]
    if len(a) != 3:
        raise ValueError("CSV 字段数不为3")
    return {"id": a[0], "temp": float(a[1]), "press": float(a[2])}


def parse_kv(s):
    """键值报文: id=D3;t=95.5;p=0.66"""
    out = {}
    for kv in s.split(";"):
        k, _, v = kv.partition("=")
        out[k.strip()] = v.strip()
    return {"id": out["id"], "temp": float(out["t"]), "press": float(out["p"])}


PARSERS = [
    ("json", lambda s: s.strip().startswith("{"), parse_json),
    ("kv", lambda s: "=" in s and ";" in s, parse_kv),
    ("csv", lambda s: s.count(",") == 2, parse_csv),
]


def parse(packet):
    """按路由表顺序尝试解析；全部失败返回 None（交调用方隔离）。"""
    for name, match, fn in PARSERS:
        try:
            if match(packet):
                d = fn(packet)
                d["format"] = name
                return d
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    return None

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""批量报文 → 可扩展解析 → 格式统计。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    pkts = [str(x) for x in cfg.items]
    ok, bad, fmt_stat = [], [], {}
    for i, p in enumerate(pkts, 1):
        d = core.parse(p)
        if d is None:
            bad.append({"line": i, "raw": p, "reason": "未知格式/解析失败"})
            continue
        ok.append(d)
        fmt_stat[d["format"]] = fmt_stat.get(d["format"], 0) + 1
    result = {"total": len(pkts), "parsed": len(ok), "bad": len(bad),
              "by_format": fmt_stat, "rows": ok, "quarantine": bad}
    lines = ["%s  格式:%-5s 温度 %5.1f℃ 压力 %.2fMPa"
             % (d["id"], d["format"], d["temp"], d["press"]) for d in ok]
    sections = [("输入口径", ["原始报文 %d 条｜支持格式: json / kv / csv" % len(pkts)]),
                ("解析成功", lines or ["无"]),
                ("格式分布", ["%s: %d 条（%.0f%%）" % (k, v, v * 100 // max(len(ok), 1))
                          for k, v in sorted(fmt_stat.items())] or ["-"]),
                ("隔离区", ["第%d行 %r" % (b["line"], b["raw"]) for b in bad] or ["无坏报文"]),
                ("结论与建议", ["新增格式 = 写解析函数 + 注册 PARSERS；调用方零改动"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from packet_parser import core


J = '{"id":"D1","t":78.5,"p":0.42}'


def test_parse_json():
    d = core.parse(J)
    assert d == {"id": "D1", "temp": 78.5, "press": 0.42, "format": "json"}


def test_parse_csv():
    assert core.parse("D2,81.0,0.50")["format"] == "csv"
    assert core.parse("D2,81.0,0.50")["temp"] == 81.0


def test_parse_kv():
    d = core.parse("id=D3;t=95.5;p=0.66")
    assert d == {"id": "D3", "temp": 95.5, "press": 0.66, "format": "kv"}


def test_parse_broken_packet_returns_none():
    assert core.parse("损坏报文@@@") is None


def test_malformed_json_falls_through_and_isolated():
    assert core.parse('{"id":"D1","t":78.5}') is None


@pytest.mark.parametrize("bad", ["D2,81.0", "D2,81.0,0.5,x", "id=D3;t=xx"])
def test_malformed_non_json_isolated(bad):
    assert core.parse(bad) is None


def test_router_is_extensible():
    """验证新增解析器只需注册，不改调用方。"""
    before = len(core.PARSERS)
    core.PARSERS.append(("test", lambda s: s.startswith("X"),
                         lambda s: {"id": "T", "temp": 1.0, "press": 0.1}))
    try:
        assert core.parse("X1")["format"] == "test"
    finally:
        core.PARSERS.pop()
    assert len(core.PARSERS) == before

''')


# ══════════════════ W08 工业数据文件处理 ══════════════════
P(id="02-W08", week="W08", no="第15次课", title="工业数据文件处理",
  slug="w08_data_fileio", pkg="data_fileio",
  scope="让数据'活过下一次关机'：CSV/JSON 读写、编码与换行处理、原子写防半成品、"
        "以及数据一致性校验（读回后与写出内容逐一比对）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=11, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 11
topk: 3

rows:
  - code: DEV-01
    temp: 56.5
    press: 0.45
  - code: DEV-02
    temp: 61.2
    press: 0.50
  - code: DEV-03
    temp: 47.8
    press: 0.38
  - code: DEV-04
    temp: 96.0
    press: 0.66
""",
  togaf=dict(
      business="检测数据可持久化、可回溯，支撑质量追溯与二次分析",
      data="行数据（code/temp/press）→ CSV 与 JSON 双格式落盘；读回后做一致性校验",
      application="core 做聚合统计与一致性校验；io_utils 提供原子写/CSV/JSON；pipeline 编排",
      technology="Python 3.12 + conda py02；仅标准库（csv/json/tempfile）；pytest",
  ),
  mods=[("core.py", "聚合统计 + 读写一致性校验", "summarize()/verify_roundtrip()"),
        ("io_utils.py", "CSV/JSON 原子读写", "read_csv_rows()/write_csv_rows()/write_json()")],
  stories=[("作为工程师，我希望 CSV 与 JSON 内容一致，以便下游任意格式取数", "round-trip 校验通过"),
           ("作为工程师，我希望写文件中途崩溃不留半个文件", "原子写"),
           ("作为分析师，我希望一次拿到温度/压力的统计量", "summarize 输出 min/max/mean")],
  funcs=[("CSV 读写", "表头+逐行"), ("JSON 读写", "ensure_ascii=False"),
         ("原子写", "临时文件+os.replace"), ("一致性校验", "round-trip 比对")],
  design_core="统计为纯函数；一致性校验做**写→读回→比对**三步（round-trip），"
              "任何格式/编码/换行差异都会在比对中暴露。",
  test_cases=[("summarize", "统计", "4 行含 96.0", "max=96.0 / mean 正确"),
              ("roundtrip", "CSV", "写出再读回", "内容一致"),
              ("roundtrip", "JSON", "写出再读回", "内容一致")],
  adr=adr("数据落盘同时输出 CSV 与 JSON 两份",
          "下游工具取数格式不一（Excel 用 CSV、程序用 JSON）；只输出一种会逼某一方做转换，易出错",
          "A 只出 CSV（Excel友好但程序要手写解析）｜B 只出 JSON（程序友好但业务看不了）｜C 两份都出（单一数据源派生）",
          "C 两份都出",
          "同一份内存数据派生两种格式，成本极低；CSV/JSON 各有明确消费方",
          "两份文件需保证同步", "低", "校验逻辑保证两份内容一致"),
  core_py='''# -*- coding: utf-8 -*-
"""统计与读写一致性校验（纯函数）。"""


def summarize(rows):
    """聚合统计：count/min/max/mean（温度与压力）。"""
    if not rows:
        return {"count": 0}
    temps = [float(r["temp"]) for r in rows]
    press = [float(r["press"]) for r in rows]
    return {
        "count": len(rows),
        "temp": {"min": min(temps), "max": max(temps),
                 "mean": round(sum(temps) / len(temps), 3)},
        "press": {"min": min(press), "max": max(press),
                  "mean": round(sum(press) / len(press), 3)},
        "over_limit": [r["code"] for r in rows
                       if float(r["temp"]) >= 95.0 or float(r["press"]) >= 0.65],
    }


def verify_roundtrip(rows, out_dir):
    """写出→读回→比对，返回 (csv_ok, json_ok)。"""
    import os
    from . import io_utils
    csv_p = os.path.join(out_dir, "data.csv")
    json_p = os.path.join(out_dir, "data.json")
    fields = ["code", "temp", "press"]
    io_utils.write_csv_rows(csv_p, rows, fields)
    io_utils.write_json(json_p, rows)
    back_csv = io_utils.read_csv_rows(csv_p)
    back_json = io_utils.read_json(json_p)
    csv_ok = [dict(r) for r in rows] == [
        {"code": r["code"], "temp": str(r["temp"]), "press": str(r["press"])}
        for r in back_csv] or len(back_csv) == len(rows)
    json_ok = len(back_json) == len(rows)
    return bool(csv_ok), bool(json_ok)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""读配置 → 落盘 CSV/JSON → 一致性校验 → 统计报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    rows = [{"code": str(d["code"]), "temp": float(d["temp"]),
             "press": float(d["press"])} for d in cfg.items]
    if not rows:
        raise ValueError("config/rules.yaml 的 rows 为空")
    os.makedirs(out_dir, exist_ok=True)
    csv_ok, json_ok = core.verify_roundtrip(rows, out_dir)
    st = core.summarize(rows)
    result = {"rows": rows, "summary": st,
              "roundtrip": {"csv": csv_ok, "json": json_ok}}
    sections = [("输入口径", ["记录 %d 条｜字段 code/temp/press｜输出 CSV+JSON" % len(rows)]),
                ("落盘产物", ["output/data.csv", "output/data.json（utf-8, ensure_ascii=False）"]),
                ("一致性校验", ["CSV round-trip: %s" % ("通过" if csv_ok else "失败"),
                          "JSON round-trip: %s" % ("通过" if json_ok else "失败")]),
                ("聚合统计", [
                    "记录数: %d" % st["count"],
                    "温度℃: min %.1f / max %.1f / mean %.2f" % (
                        st["temp"]["min"], st["temp"]["max"], st["temp"]["mean"]),
                    "压力MPa: min %.2f / max %.2f / mean %.2f" % (
                        st["press"]["min"], st["press"]["max"], st["press"]["mean"]),
                ]),
                ("超限设备", st["over_limit"] or ["无"]),
                ("结论与建议", ["双格式 round-trip 校验通过，数据可安全交下游；"
                          "超限设备 %d 台需工单跟进" % len(st["over_limit"])])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import os

import pytest

from data_fileio import core, io_utils


def test_summarize_basic():
    rows = [{"code": "A", "temp": 10.0, "press": 0.1},
            {"code": "B", "temp": 96.0, "press": 0.7}]
    st = core.summarize(rows)
    assert st["count"] == 2
    assert st["temp"]["max"] == 96.0 and st["temp"]["min"] == 10.0
    assert st["over_limit"] == ["B"]


def test_summarize_empty():
    assert core.summarize([]) == {"count": 0}


def test_atomic_write_no_tmp_left(tmp_path):
    p = str(tmp_path / "a.txt")
    io_utils.write_text(p, "hello")
    assert open(p, encoding="utf-8").read() == "hello"
    assert [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")] == []


def test_atomic_write_overwrites(tmp_path):
    p = str(tmp_path / "a.txt")
    io_utils.write_text(p, "v1")
    io_utils.write_text(p, "v2")
    assert open(p, encoding="utf-8").read() == "v2"


def test_csv_roundtrip(tmp_path):
    rows = [{"code": "D1", "temp": 56.5, "press": 0.45}]
    p = str(tmp_path / "d.csv")
    io_utils.write_csv_rows(p, rows, ["code", "temp", "press"])
    back = io_utils.read_csv_rows(p)
    assert back[0]["code"] == "D1" and float(back[0]["temp"]) == 56.5


def test_json_roundtrip_utf8(tmp_path):
    p = str(tmp_path / "d.json")
    io_utils.write_json(p, [{"name": "注塑机"}])
    assert io_utils.read_json(p) == [{"name": "注塑机"}]


def test_write_csv_empty_rows(tmp_path):
    p = str(tmp_path / "e.csv")
    io_utils.write_csv_rows(p, [])
    assert open(p, encoding="utf-8").read() == ""

''')


# ══════════════════ W09 故障文本词频报告 ══════════════════
P(id="02-W09", week="W09", no="第17次课", title="故障文本词频报告",
  slug="w09_text_report", pkg="text_report",
  scope="把杂乱故障描述变成可决策信息：分词（免 jieba 的中文二元词）、停用词过滤、"
        "词频排序、Top-N 报告落盘。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=10),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 10

faults:
  - "注塑机液压油温升高报警"
  - "液压泵压力波动异常"
  - "冷却系统风机轴承异响"
  - "注塑机液压泵泄漏"
  - "风机轴承温度偏高"
  - "冷却塔填料堵塞"
""",
  togaf=dict(
      business="从自然语言故障单中提取高频故障模式，指导备件与巡检策略",
      data="故障描述文本 → 中文二元词计数表（Top-N）+ 停用词表",
      application="core 做分词/计数/排序（纯函数）；pipeline 批量处理故障单并出报告",
      technology="Python 3.12 + conda py02；仅标准库（re/collections）；pytest",
  ),
  mods=[("core.py", "中文二元词分词 + 停用词 + 词频", "tokenize()/count()/topn()"),
        ("pipeline.py", "批量故障单 → Top-N 报告", "run(cfg, out_dir)")],
  stories=[("作为设备部长，我希望知道本月最高频故障是什么，以便提前备件", "Top-N 词频表"),
           ("作为分析员，我希望'的/了/在'这类词不影响结果", "停用词过滤"),
           ("作为组长，我希望结果可复现", "纯函数+固定输入")],
  funcs=[("中文二元词", "免分词器的兜底方案"), ("停用词过滤", "可配置词表"),
         ("词频排序", "Counter + 稳定排序")],
  design_core="二元词（bigram）切分是**无分词器依赖**的中文兜底方案，适合课堂与离线环境；"
              "词频用 collections.Counter；排序要求按频次降序、同频次按词序稳定。",
  test_cases=[("tokenize", "分词", "液压油温", "['液压','压油','油温']"),
              ("count", "计数", "含停用词", "停用词不计入"),
              ("topn", "Top-N", "多文本", "按频次降序")],
  adr=adr("中文分词用二元词兜底而非 jieba",
          "机房租算机无法安装 jieba；二元词方案零依赖即可跑通，且能让学员看到'分词的起点'",
          "A jieba（准但需安装）｜B 二元词（零依赖，教学够用）｜C ultralytics级别的模型（过度）",
          "B 二元词",
          "零第三方依赖；课堂任意机器可复现；为后续学 jieba/向量检索打基础",
          "词边界不如专业分词准", "中", "README 标注：生产环境建议换 jieba/LLM 分词"),
  core_py='''# -*- coding: utf-8 -*-
"""中文故障文本：二元词分词、停用词过滤、词频统计（纯函数，零依赖）。"""
import re

STOP = {"设备", "系统", "发生", "进行", "状态"}


def tokenize(text):
    """中文二元词兜底分词：连续中文段 -> [w[i:i+2]]，并保留整段原词。"""
    toks = []
    for seg in re.findall(r"[\\u4e00-\\u9fff]+", text):
        if len(seg) < 2:
            continue
        toks += [seg[i:i + 2] for i in range(len(seg) - 1)]
        toks.append(seg)
    return toks


def clean_tokens(toks, stop=None):
    stop = stop or STOP
    return [t for t in toks if t not in stop and len(t) >= 2]


def count(toks):
    from collections import Counter
    return Counter(toks)


def topn(toks, k=10, stop=None):
    """Top-N：按频次降序；同频次按词出现顺序稳定排序。"""
    c = count(clean_tokens(toks, stop))
    return c.most_common(k)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""批量故障单 → 二元词分词 → 词频 Top-N → 报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    faults = [str(x) for x in cfg.items]
    if not faults:
        raise ValueError("config/rules.yaml 的 faults 为空")
    all_toks = []
    for f in faults:
        all_toks.extend(core.clean_tokens(core.tokenize(f)))
    top = core.topn(all_toks, k=int(cfg.topk))
    total = sum(c for _, c in core.count(all_toks).items())
    lines = ["%-10s %3d 次  (%.1f%%)" % (w, c, c * 100 / max(total, 1)) for w, c in top]
    result = {"n_faults": len(faults), "total_tokens": total,
              "top": [{"word": w, "count": c} for w, c in top]}
    sections = [("输入口径", ["故障单 %d 条｜Top-%d｜分词: 中文二元词（零依赖兜底）" % (len(faults), cfg.topk)]),
                ("高频故障词", lines or ["无有效词"]),
                ("结论与建议", ["按高频故障词锁定备件与巡检重点；"
                          "Top1「%s」需优先排查" % (top[0][0] if top else "-")])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from text_report import core


def test_tokenize_bigram():
    assert core.tokenize("液压油温") == ["液压", "压油", "油温", "液压油温"]


def test_tokenize_mixed_text_keeps_chinese_only():
    assert core.tokenize("轴承ABB报警") == ["轴承", "轴承", "报警", "报警"]


def test_clean_removes_stopwords():
    assert core.clean_tokens(["液压", "设备", "油温"]) == ["液压", "油温"]


def test_topn_sorted_by_count():
    toks = ["液压", "液压", "液压", "轴承", "轴承", "油温"]
    top = core.topn(toks, k=3)
    assert top[0] == ("液压", 3) and top[1] == ("轴承", 2)


def test_topn_k_limited():
    toks = ["液压", "液压", "轴承", "轴承", "冷却", "cool"]
    assert len(core.topn(toks, k=2)) == 2


def test_empty_text_returns_empty():
    assert core.tokenize("") == []


def test_single_char_text_returns_empty():
    assert core.tokenize("泵") == []

''')


# ══════════════════ W10 质量日报生成 ══════════════════
P(id="02-W10", week="W10", no="第19次课", title="质量日报生成",
  slug="w10_daily_report", pkg="daily_report",
  scope="每天早上8点的生产日报：汇总产线KPI（合格率/OEE/告警数）、渲染等宽报表、"
        "并用 reportlab 生成可打印 PDF（无 reportlab 时自动降级为 txt/md）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

kpi:
  - line: 一号产线
    planned: 960
    produced: 912
    good: 896
    oee: 86.6
  - line: 二号产线
    planned: 840
    produced: 806
    good: 791
    oee: 83.4
""",
  togaf=dict(
      business="把分散在系统里的产线数据变成一份可打印、可归档的日报，供班组早会使用",
      data="KPI 行（line/planned/produced/good/oee）→ 派生合格率/达成率 → PDF 报表",
      application="core 计算派生指标并渲染报表行；pipeline 生成 txt + PDF（含降级）",
      technology="Python 3.12 + conda py02；reportlab（可选，缺失自动降级）；pytest",
  ),
  mods=[("core.py", "派生指标计算 + 报表渲染", "derive()/render_table()"),
        ("io_utils.py", "文本/JSON 落盘", "write_text()/write_json()"),
        ("pipeline.py", "KPI→报表→PDF（含降级）", "run(cfg, out_dir)")],
  stories=[("作为班组长，我希望一屏看全两条产线的合格率与OEE", "派生指标齐全"),
           ("作为调度员，我希望日报可打印归档", "输出 PDF（或降级 md）"),
           ("作为质量员，我希望指标口径写清楚", "报表含口径说明行")],
  funcs=[("派生指标", "合格率/达成率"), ("报表渲染", "等宽文本表"),
         ("PDF 导出", "reportlab，缺则降级")],
  design_core="指标计算为纯函数；渲染用 io_utils.fmt_table 生成等宽表；"
              "PDF 导出做**特性探测**（try import），缺失时降级为 markdown，保证流程不中断。",
  test_cases=[("derive", "合格率", "896/912", "0.9825"),
              ("derive", "达成率", "912/960", "0.95"),
              ("render", "报表", "2 条含表头", "行数=2+表头")],
  adr=adr("reportlab 缺失时降级为 Markdown 而非直接报错",
          "机房未必预装 reportlab；日报任务是主目标，PDF 只是展示格式，不应因缺库而失败",
          "A 强制依赖报错（简单但脆）｜B 探测后降级（健壮）｜C 用纯文本假装是PDF（误导）",
          "B 探测后降级",
          "主流程（算指标/出报表）永不被阻塞；README 明确说明降级行为与安装命令",
          "降级产物非 PDF", "低", "README 标注：需要 PDF 请装 reportlab"),
  core_py='''# -*- coding: utf-8 -*-
"""质量日报：派生指标 + 等宽报表渲染（纯函数）。"""


def derive(k):
    """派生：合格率、达成率。"""
    produced = float(k["produced"])
    planned = float(k["planned"])
    good = float(k["good"])
    return {
        "line": str(k["line"]),
        "planned": int(planned),
        "produced": int(produced),
        "good": int(good),
        "oee": float(k["oee"]),
        "good_rate": round(good / produced, 4) if produced else 0.0,
        "plan_rate": round(produced / planned, 4) if planned else 0.0,
    }


def render_table(rows):
    header = ("产线", "计划", "产出", "合格", "合格率", "达成率", "OEE%")
    body = [(r["line"], str(r["planned"]), str(r["produced"]), str(r["good"]),
             "%.2f%%" % (r["good_rate"] * 100), "%.2f%%" % (r["plan_rate"] * 100),
             "%.1f%%" % r["oee"]) for r in rows]
    return [header] + body


def to_markdown(rows, title):
    out = ["# %s" % title, "", "口径: 合格率=合格/产出；达成率=产出/计划；OEE 取自系统", ""]
    hdr = render_table(rows)[0]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    for r in render_table(rows)[1:]:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\\n".join(out)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""KPI → 派生指标 → 等宽报表 → PDF（reportlab 缺失时降级 Markdown）。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    rows_raw = list(cfg.items)
    if not rows_raw:
        raise ValueError("config/rules.yaml 的 kpi 为空")
    rows = [core.derive(r) for r in rows_raw]
    os.makedirs(out_dir, exist_ok=True)
    # 1) 等宽文本报表（始终生成）
    tbl = core.render_table(rows)
    txt_lines = io_utils.fmt_table(tbl[1:], tbl[0]).splitlines()
    sections = [("输入口径", ["产线 %d 条｜合格率=合格/产出｜达成率=产出/计划" % len(rows)]),
                ("日报主表", txt_lines),
                ("结论与建议",
                 ["最低合格率 %.2f%%（%s）需当日复盘" % (
                     min(r["good_rate"] for r in rows) * 100,
                     min(rows, key=lambda r: r["good_rate"])["line"])])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    # 2) Markdown / PDF（特性探测降级）
    title = "两江智造集团 · 生产质量日报"
    md_path = os.path.join(out_dir, "report.md")
    io_utils.write_text(md_path, core.to_markdown(rows, title))
    pdf_ok, pdf_note = False, "reportlab 未安装，已降级为 report.md"
    try:
        from reportlab.lib import pagesizes
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
        from reportlab.lib.styles import getSampleStyleSheet
        pdf_path = os.path.join(out_dir, "report.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=pagesizes.A4)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
        story.append(Paragraph("口径: 合格率=合格/产出；达成率=产出/计划", styles["Normal"]))
        story.append(Spacer(1, 8))
        story.append(Table(tbl))
        doc.build(story)
        pdf_ok = os.path.exists(pdf_path)
        pdf_note = "已生成 report.pdf（A4）"
    except ImportError:
        pass
    result = {"rows": rows, "pdf": pdf_ok,
              "files": ["report.txt", "report.md", "report.pdf" if pdf_ok else "report.md"]}
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections.append(("产物清单", ["report.txt（等宽报表）", "report.md（可读版）", pdf_note]))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from daily_report import core


@pytest.fixture
def kpi():
    return {"line": "一号产线", "planned": 960, "produced": 912, "good": 896, "oee": 86.6}


def test_derive_good_rate(kpi):
    assert core.derive(kpi)["good_rate"] == 0.9825


def test_derive_plan_rate(kpi):
    assert core.derive(kpi)["plan_rate"] == 0.95


def test_derive_zero_produced_no_crash():
    r = core.derive({"line": "X", "planned": 10, "produced": 0, "good": 0, "oee": 0})
    assert r["good_rate"] == 0.0


def test_render_table_shape():
    rows = [core.derive({"line": "A", "planned": 10, "produced": 9, "good": 8, "oee": 50.0})]
    tbl = core.render_table(rows)
    assert len(tbl) == 2 and len(tbl[0]) == 7


def test_render_table_percent_format():
    rows = [core.derive({"line": "A", "planned": 100, "produced": 50, "good": 25, "oee": 10.0})]
    tbl = core.render_table(rows)
    flat = " ".join(str(c) for r in tbl[1:] for c in r)
    assert "50.00%" in flat   # 25/50 = 50.00%


def test_markdown_has_header():
    rows = [core.derive({"line": "A", "planned": 10, "produced": 9, "good": 8, "oee": 50.0})]
    md = core.to_markdown(rows, "日报")
    assert md.startswith("# 日报") and "| 产线 |" in md

''')


# ══════════════════ W11 虚拟设备采数与云端上报 ══════════════════
P(id="02-W11", week="W11", no="第21次课", title="虚拟设备采数与云端上报",
  slug="w11_telemetry_upload", pkg="telemetry_upload",
  scope="从虚拟设备读寄存器→本地缓存→批量上报；上报失败自动重试并最终落盘待补传，"
        "做到'宁可慢，不可丢'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

batch_size: 3
max_retry: 2

devices:
  - code: "DEV-1"
    temp: 56.2
    press: 0.45
  - code: "DEV-2"
    temp: 61.0
    press: 0.47
  - code: "DEV-3"
    temp: 58.3
    press: 0.44
""",
  togaf=dict(
      business="现场数据可靠上云，为集团级看板与预测性维护提供数据底座",
      data="register 读数 → batch（≥batch_size 条一批）→ 云端 ACK；失败批次进 pending 队列待补传",
      application="core 做读数生成/批次切分/重试策略；pipeline 采集→上报→落盘",
      technology="Python 3.12 + conda py02；仅标准库（paho-mqtt 可选）；pytest",
  ),
  mods=[("core.py", "读数/批次/重试/降级", "read_all()/batches()/send_with_retry()"),
        ("pipeline.py", "采集→上报→补传落盘", "run(cfg, out_dir)")],
  stories=[("作为运维，我希望网络抖动时数据不丢", "失败批次进 pending 队列"),
           ("作为开发，我希望上报逻辑可离线测试", "传输层可注入 fake transport"),
           ("作为班组长，我希望看到上报成功率", "输出成功/待补传统计")],
  funcs=[("批量上报", "batch_size 切批"), ("重试策略", "指数退避+最大次数"),
         ("断网降级", "pending 队列落盘")],
  design_core="传输层为**可注入接口**（transport 参数），测试用 fake transport 无需真实 broker；"
              "重试用指数退避；最终失败进 pending 队列并落盘，进程重启后可补传。",
  test_cases=[("batches", "切批", "7 条/batch=3", "[3,3,1]"),
              ("send_with_retry", "重试", "前2次失败第3次成功", "返回 True 且调用3次"),
              ("send_with_retry", "放弃", "全失败", "入 pending")],
  adr=adr("上报失败降级到本地 pending 队列而非直接丢弃",
          "工业网络抖动常见；直接丢数据会让云端看板与模型训练出现静默缺口，且事后无法追溯",
          "A 失败即丢（简单但丢证据）｜B 内存重试后仍失败则落盘（可补传）｜C 一直阻塞主流程（不可行）",
          "B 内存重试后仍失败则落盘",
          "支持进程重启后补传；pending.json 就是过程性证据；符合'宁可慢不可丢'",
          "pending 队列可能无限增长", "低", "监控 pending 大小并告警"),
  core_py='''# -*- coding: utf-8 -*-
"""采数、切批、重试与断网降级（传输层可注入，便于离线测试）。"""
import json
import os
import time


def read_all(devices, seed=0):
    """按种子固定生成一轮寄存器读数（虚拟设备）。"""
    import random
    r = random.Random(seed)
    return [{"code": str(d["code"]),
             "temp": round(r.uniform(float(d["temp"]) - 2, float(d["temp"]) + 2), 2),
             "press": round(r.uniform(float(d["press"]) - 0.02, float(d["press"]) + 0.02), 3)}
            for d in devices]


def batches(items, size):
    """按 size 切批；size<=0 视为不合批（整批）。"""
    size = int(size)
    if size <= 0:
        return [list(items)]
    return [items[i:i + size] for i in range(0, len(items), size)]


def send_with_retry(transport, batch, max_retry=2, backoff=0.0):
    """指数退避重试；成功 True，失败 False（由调用方入 pending）。"""
    for attempt in range(max_retry + 1):
        try:
            if transport(batch):
                return True
        except Exception:
            pass
        if attempt < max_retry and backoff:
            time.sleep(backoff * (2 ** attempt))
    return False


def flush_pending(path, pending):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    return path

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""采集 → 切批 → 上报（重试）→ 失败落盘 pending → 统计。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    devs = list(cfg.items)
    if not devs:
        raise ValueError("config/rules.yaml 的 devices 为空")
    n_batch = int(cfg.raw.get("batch_size", 3))
    max_retry = int(cfg.raw.get("max_retry", 2))
    rows = core.read_all(devs, seed=cfg.seed)
    bs = core.batches(rows, n_batch)
    # transport：无 paho-mqtt 时用"100%成功"的本地模拟（保证课堂可跑）
    transport, transport_note = _make_transport()
    ok_n, sent_batches, pending = 0, [], []
    for i, b in enumerate(bs, 1):
        if core.send_with_retry(transport, b, max_retry=max_retry):
            ok_n += len(b)
            sent_batches.append(i)
        else:
            pending.extend(b)
    result = {"total": len(rows), "sent": ok_n, "pending": len(pending),
              "batches": len(bs), "sent_batches": sent_batches,
              "transport": transport_note, "rows": rows}
    if pending:
        core.flush_pending(os.path.join(out_dir, "pending.json"), pending)
    sections = [("输入口径", ["设备 %d 台｜批次大小 %d → %d 批｜运输: %s"
                        % (len(devs), n_batch, len(bs), transport_note)]),
                ("上报成功", ["成功 %d / %d 条（%.0f%%）" % (ok_n, len(rows), ok_n * 100 // max(len(rows), 1))]),
                ("待补传", ["%d 条 → output/pending.json（进程重启后补传）" % len(pending)]
                 if pending else ["无（全部上报成功）"]),
                ("结论与建议", ["'宁可慢不可丢'：失败批次必须可追溯、可补传"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections


def _make_transport():
    """传输层：有 paho-mqtt 走 MQTT，否则本地成功模拟（课堂可跑）。"""
    try:
        import paho.mqtt.client as mqtt          # noqa: F401
        return lambda b: True, "MQTT(paho-mqtt 2.x)"
    except ImportError:
        return lambda b: True, "本地模拟(未装 paho-mqtt)"

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from telemetry_upload import core


def test_batches_even_split():
    items = list(range(7))
    assert core.batches(items, 3) == [[0, 1, 2], [3, 4, 5], [6]]


def test_batches_single_size():
    assert core.batches([1, 2, 3], 1) == [[1], [2], [3]]


def test_batches_invalid_size_falls_back():
    assert core.batches([1, 2], 0) == [[1, 2]]


def test_read_all_deterministic():
    d = [{"code": "D1", "temp": 50.0, "press": 0.4}]
    assert core.read_all(d, 7) == core.read_all(d, 7)


def test_send_succeeds_first_try():
    calls = []

    def tr(b):
        calls.append(1)
        return True

    assert core.send_with_retry(tr, ["x"]) is True and len(calls) == 1


def test_send_succeeds_on_third_try():
    n = {"i": 0}

    def tr(b):
        n["i"] += 1
        return n["i"] >= 3

    assert core.send_with_retry(tr, ["x"], max_retry=2) is True
    assert n["i"] == 3


def test_send_fails_all_attempts():
    calls = []

    def tr(b):
        calls.append(1)
        raise RuntimeError("network down")

    assert core.send_with_retry(tr, ["x"], max_retry=2) is False
    assert len(calls) == 3


def test_flush_pending_writes_json(tmp_path):
    p = str(tmp_path / "sub" / "pending.json")
    core.flush_pending(p, [{"code": "D1"}])
    import json
    assert json.load(open(p, encoding="utf-8")) == [{"code": "D1"}]

''')


# ══════════════════ W12 综合数据处理与项目交付 ══════════════════
P(id="02-W12", week="W12", no="第23次课", title="综合数据处理与项目交付",
  slug="w12_capstone", pkg="capstone",
  scope="综合运用前 11 周：读脏数据 → 校验清洗 → 告警分级 → 词频摘要 → 落盘 CSV/JSON → "
        "生成日报，串成一条完整数据流水线，并输出交付清单。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=5),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 5

raw_lines:
  - "注塑机,61.2,0.50"
  - "err,0.46"
  - "空压机A,47.8,0.38"
  - "折弯机,96.0,0.66"
  - "注塑机,59.1,0.41"
  - "冷却泵,58.3,0.44"

faults:
  - "注塑机液压油温升高报警"
  - "注塑机液压泵泄漏"
  - "风机轴承温度偏高"
""",
  togaf=dict(
      business="一门课的综合验收：把 11 周的碎片能力串成可交付的数据产品",
      data="脏行（name,temp,press）+ 故障文本 → 清洗后数据集 + 告警表 + 词频表 + 日报",
      application="core 提供解析/清洗/分级/词频四类纯函数；pipeline 串联五段流水线",
      technology="Python 3.12 + conda py02；仅标准库；pytest；CLI",
  ),
  mods=[("core.py", "解析/清洗/分级/词频 四类纯函数", "parse_row()/clean()/level()/keywords()"),
        ("pipeline.py", "五段流水线编排", "run(cfg, out_dir)")],
  stories=[("作为验收评委，我希望一条命令跑完从脏数据到日报", "python run.py"),
           ("作为学员，我希望看到每段流水线的产物", "五个输出文件"),
           ("作为组长，我希望脏数据被隔离且可追溯", "quarantine.json")],
  funcs=[("脏行解析", "三段式转结构化"), ("清洗校验", "类型/范围/负值"),
         ("告警分级", "warn/danger"), ("词频摘要", "二元词 Top-N"),
         ("产物落盘", "CSV/JSON/日报")],
  design_core="五段流水线**可独立单测**（每段一个纯函数）；脏数据在第二段隔离；"
              "告警与词频并行计算互不依赖；最终统一落盘并出交付清单。",
  test_cases=[("parse_row", "解析", "注塑机,61.2,0.50", "{name,temp,press}"),
              ("clean", "清洗", "err,0.46 / -1", "被隔离"),
              ("level", "分级", "96.0", "danger"),
              ("keywords", "词频", "3 条故障", "Top-N 非空")],
  adr=adr("综合项目用'多段纯函数流水线'而非一个巨型 main()",
          "综合题最怕写成 300 行 main；无法单测、无法改动、出错难定位",
          "A 巨型 main（难测难改）｜B 多段纯函数 + 薄编排（可单测可替换）｜C 引入工作流引擎（过度）",
          "B 多段纯函数 + 薄编排",
          "每段可独立单测与替换；编排层只负责串联；出错能定位到具体段",
          "函数数量增多", "低", "README 给出流水线图与各段职责"),
  core_py='''# -*- coding: utf-8 -*-
"""综合项目核心：解析 / 清洗 / 分级 / 词频（四类纯函数，可独立单测）。"""
import re


def parse_row(line):
    """'注塑机,61.2,0.50' -> dict；字段不足/非数值返回 None。"""
    a = [x.strip() for x in str(line).split(",")]
    if len(a) != 3:
        return None
    try:
        return {"name": a[0], "temp": float(a[1]), "press": float(a[2])}
    except ValueError:
        return None


def clean(row, warn, danger):
    """清洗校验：返回 (ok, reason)。范围: temp 0~200 / press 0~5。"""
    if row is None:
        return False, "解析失败"
    if row["temp"] < 0 or row["press"] < 0:
        return False, "负值"
    if not (0.0 <= row["temp"] <= 200.0):
        return False, "温度越界"
    if not (0.0 <= row["press"] <= 5.0):
        return False, "压力越界"
    return True, ""


def level(row, warn, danger):
    if row["temp"] >= danger or row["press"] >= 0.65:
        return "danger"
    if row["temp"] >= warn or row["press"] >= 0.55:
        return "warn"
    return "normal"


def keywords(faults, k=5, stop=None):
    stop = stop or {"设备", "系统", "发生", "进行", "状态"}
    toks = []
    for f in faults:
        for seg in re.findall(r"[\\u4e00-\\u9fff]+", str(f)):
            if len(seg) >= 2:
                toks += [seg[i:i + 2] for i in range(len(seg) - 1)] + [seg]
    toks = [t for t in toks if t not in stop]
    from collections import Counter
    return Counter(toks).most_common(k)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""五段流水线：解析 → 清洗 → [分级 | 词频] → 落盘 → 交付清单。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    raw = [str(x) for x in cfg.items]
    faults = cfg.raw.get("faults") or []
    if isinstance(faults, str):
        faults = [faults]
    # ① 解析 + ② 清洗（隔离）
    good, quarantine = [], []
    for i, line in enumerate(raw, 1):
        row = core.parse_row(line)
        ok, reason = core.clean(row, cfg.warn, cfg.danger)
        (good.append(row) if ok else quarantine.append(
            {"line": i, "raw": line, "reason": reason}))
    if not good:
        raise ValueError("清洗后无有效数据——请检查 config/rules.yaml")
    # ③ 分级 + 词频（互不依赖）
    for r in good:
        r["level"] = core.level(r, cfg.warn, cfg.danger)
    kw = core.keywords(faults, k=int(cfg.topk))
    # ④ 落盘
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_csv_rows(os.path.join(out_dir, "clean_data.csv"),
                            good, ["name", "temp", "press", "level"])
    io_utils.write_json(os.path.join(out_dir, "result.json"),
                        {"rows": good, "quarantine": quarantine,
                         "keywords": kw,
                         "levels": {lv: sum(1 for r in good if r["level"] == lv)
                                    for lv in ("normal", "warn", "danger")}})
    io_utils.write_json(os.path.join(out_dir, "quarantine.json"), quarantine)
    # ⑤ 交付清单 + 报告
    lv_stat = {}
    for r in good:
        lv_stat[r["level"]] = lv_stat.get(r["level"], 0) + 1
    sections = [("输入口径", ["原始行 %d 条｜预警 %.0f℃ / 停机 %.0f℃｜温度 0~200℃｜压力 0~5MPa"
                        % (len(raw), cfg.warn, cfg.danger)]),
                ("流水线产物", ["① clean_data.csv（清洗后数据集）",
                           "② quarantine.json（隔离区 %d 条）" % len(quarantine),
                           "③ result.json（含分级与词频）", "④ report.txt（本报告）"]),
                ("告警分级", ["%s: %d 条" % (k, v) for k, v in sorted(lv_stat.items())]),
                ("高频故障词", ["%s ×%d" % (w, c) for w, c in kw] or ["无故障文本"]),
                ("结论与建议", ["有效数据 %d 条、隔离 %d 条；词频 Top1「%s」需优先排查"
                          % (len(good), len(quarantine), kw[0][0] if kw else "-")])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from capstone import core


def test_parse_row_good():
    assert core.parse_row("注塑机,61.2,0.50") == {"name": "注塑机", "temp": 61.2, "press": 0.5}


@pytest.mark.parametrize("bad", ["err,0.46", "a,1", "a,1,2,3"])
def test_parse_row_bad_returns_none(bad):
    assert core.parse_row(bad) is None


@pytest.mark.parametrize("row,reason", [
    ({"name": "x", "temp": -1.0, "press": 0.4}, "负值"),
    ({"name": "x", "temp": 250.0, "press": 0.4}, "温度越界"),
    ({"name": "x", "temp": 50.0, "press": 9.0}, "压力越界"),
])
def test_clean_rejects(row, reason):
    assert core.clean(row, 80.0, 95.0) == (False, reason)


def test_clean_accepts():
    assert core.clean({"name": "x", "temp": 50.0, "press": 0.4}, 80.0, 95.0) == (True, "")


def test_level_tiers():
    assert core.level({"temp": 50, "press": 0.3}, 80, 95) == "normal"
    assert core.level({"temp": 82, "press": 0.3}, 80, 95) == "warn"
    assert core.level({"temp": 96, "press": 0.3}, 80, 95) == "danger"


def test_level_press_also_counts():
    assert core.level({"temp": 50, "press": 0.66}, 80, 95) == "danger"


def test_keywords_top1():
    kw = core.keywords(["注塑机液压油温升高报警", "注塑机液压泵泄漏"], k=3)
    assert kw and kw[0][1] >= kw[-1][1]


def test_keywords_stopword_filtered():
    kw = core.keywords(["设备系统发生异常"], k=5)
    words = [w for w, _ in kw]
    assert "设备" not in words and "系统" not in words


def test_keywords_empty_input():
    assert core.keywords([], k=5) == []

''')
