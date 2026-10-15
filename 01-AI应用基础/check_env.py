# -*- coding: utf-8 -*-
"""《AI应用基础》 环境一键自检（python check_env.py [--deep]）"""
import sys

DEEP = "--deep" in sys.argv


def imp(mod):
    def f():
        import importlib
        m = importlib.import_module(mod)
        return getattr(m, "__version__", "ok")
    return f


def font(path):
    def f():
        import os
        assert os.path.exists(path), "缺少字体: " + path
        return "OK"
    return f


def fileexists(path):
    def f():
        import os
        assert os.path.exists(path), "缺少: " + path
        return ""
    return f


def port(host, p):
    def f():
        import socket
        s = socket.create_connection((host, p), timeout=2)
        s.close()
        return f"port {p} ✓"
    return f


ok = warn = fail = 0


def check(name, need, fn):
    global ok, warn, fail
    try:
        extra = fn() or ""
        print(f"[PASS] {name} {extra}")
        ok += 1
    except Exception as e:
        if need:
            print(f"[FAIL] {name} —— {e}")
            fail += 1
        else:
            print(f"[WARN] {name}（按周可选）—— {e}")
            warn += 1


def _py_ver():
    if sys.version_info >= (3, 12):
        return "v%d.%d" % sys.version_info[:2]
    raise RuntimeError(sys.version.split()[0])


check("Python≥3.12", True, _py_ver)
check("numpy", True, lambda: __import__("importlib").import_module("numpy").__version__)
check("scikit-learn", True, imp("sklearn"))
check("matplotlib", True, imp("matplotlib"))
check("jieba", True, imp("jieba"))
check("requests", True, imp("requests"))
check("torch(CPU)", False, imp("torch"))
check("onnxruntime", False, imp("onnxruntime"))
check("opencv", False, imp("cv2"))
check("notebook", False, imp("notebook"))
check("思源字体(思源OFL)", True, font("fonts/ZH_Font.ttf"))
if DEEP:
    check("本地数据data/", True, fileexists("数据与工具/generate_data.py"))
    check("mock服务:8000", False, port("127.0.0.1", 8000))
    check("YOLO权重", False, fileexists("数据与工具/data/weights/yolov8n.onnx"))
print("-" * 46)
print(f"结果: PASS {ok} | WARN {warn} | FAIL {fail}")
print("开课口径: 必需项FAIL=0 即可开课" + ("；--deep已含服务/数据连通" if DEEP else "（--deep 检查服务与数据）"))
# ===== M4系新栈自检（33号轮：mock LLM v2与RAG双解依赖） =====
print("[M4系] LLM服务与向量检索新栈（选做，不装不影响M1-M3）")
for _m in ("litestar", "chromadb"):
    try:
        __import__(_m)
        print(f"[PASS] {_m} 可用（mock_llm_server v2 / rag_chroma_demo）")
    except ImportError:
        print(f"[WARN] {_m} 缺失 → pip install {_m}（M4可用旧版http.server方案替代）")

sys.exit(1 if fail else 0)
