# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M4.2 工业智能决策助手（本地模拟LLM + RAG + Agent）—— 学生代码框架
服务端(教师机): python mock_llm_server.py
本框架默认连 127.0.0.1:8000, 按机房实际IP修改 BASE_URL。
"""
import json
import re

import requests

BASE_URL = "http://127.0.0.1:8000"
KB_PATH = "data/knowledge_base.json"


def chat(messages, retries=2, timeout=5):
    """TODO-1: 调用本地LLM(OpenAI兼容), 带重试与降级(容错必做)"""
    for i in range(retries + 1):
        try:
            r = requests.post(f"{BASE_URL}/v1/chat/completions",
                              json={"messages": messages}, timeout=timeout)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except requests.RequestException:
            pass
    return "[降级] 本地服务暂不可用, 已转人工工单通道。"


class KnowledgeBase:
    """TODO-2: 知识库检索(关键词或TF-IDF, 二选一并写入决策矩阵)"""

    def __init__(self, path=KB_PATH):
        with open(path, encoding="utf-8") as f:
            self.kb = json.load(f)
        self.docs = [t for items in self.kb.values() for t in items]

    def retrieve(self, query, topk=2):
        """返回最相关的topk条知识(字符串列表)"""
        # === 你的代码 ===
        raise NotImplementedError


class Tool:
    """工具: 名称+功能函数"""

    def __init__(self, name, func):
        self.name, self.func = name, func

    def run(self, *a):
        return self.func(*a)


class Agent:
    """TODO-3: 两步推理: 判断是否查库 → 调用工具组装Prompt → 生成回答"""

    def __init__(self, kb):
        self.kb = kb
        self.tools = {
            "查询知识库": Tool("查询知识库", kb.retrieve),
            "阈值判定": Tool("阈值判定", lambda v: "超标,须停机检查" if float(v) > 4.5 else "正常范围"),
        }

    def ask(self, question):
        # 步骤1: 是否含数值判定需求(如"振动7.5mm/s")
        m = re.search(r"([\d.]+)\s*mm/s", question)  # noqa: F841
        # 步骤2: 组装messages → chat() → 返回回答与依据
        # === 你的代码 ===
        raise NotImplementedError


PROMPTS = {
    "朴素": "回答问题: {q}",
    "角色设定": "你是资深设备工程师, 按规范回答: {q}",
    "带示例": "示例问: 空压机排气压力低怎么办?\n示例答: 先查气源泄漏…\n现在回答: {q}",
}


def main():
    kb = KnowledgeBase()
    agent = Agent(kb)  # noqa: F841
    questions = [
        "泵振动7.5mm/s怎么处理？",
        "轴承温度82℃要不要停机？",
        "变频器过流报警如何排查？",
        "液压油污染度NAS 10级怎么办？",
        "PLC从站通信中断排查顺序？",
    ]
    # ---- 1) Prompt对比(同一问题三版) ----
    for name, tpl in PROMPTS.items():
        msg = [{"role": "user", "content": tpl.format(q=questions[0])}]
        print(f"[{name}] {chat(msg)[:60]}...\n")
    # TODO-4: RAG对比: 检索结果注入后再问, 记录是否更"有依据"
    # TODO-5: Agent全流程问答记录表(问题/回答/依据)
    # for q in questions: print(q, "->", agent.ask(q))


if __name__ == "__main__":
    main()
