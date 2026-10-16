# -*- coding: utf-8 -*-
"""82轮·01-AI应用基础 教师版答案（学生版函数结构 + solutions 逻辑适配）

每个课次给出「学生版同名的完成态函数源码」，用于填充教师版 TODO。
"""
A01 = {
 "m11": {
  "load_data": '''def load_data(path):
    """读取CSV(仅用NumPy): 返回 X(float, N×5), y(int, N,)"""
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, :5], data[:, 5].astype(int)
''',
  "split": '''def split(X, y, test_ratio=0.25, seed=42):
    """分层划分训练/测试集(每类按比例抽)"""
    rng = np.random.RandomState(seed)
    tr, te = [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        k = int(len(idx) * (1 - test_ratio))
        tr.append(idx[:k])
        te.append(idx[k:])
    tr, te = np.concatenate(tr), np.concatenate(te)
    rng.shuffle(tr)
    rng.shuffle(te)
    return X[tr], X[te], y[tr], y[te]
''',
  "main": '''def main():
    X, y = load_data(DATA)
    print("数据形状:", X.shape, "类别分布:", np.bincount(y))

    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (accuracy_score, precision_score,
                                 recall_score, f1_score)

    Xtr, Xte, ytr, yte = split(X, y)

    models = {
        "逻辑回归": LogisticRegression(max_iter=1000),
        "决策树": DecisionTreeClassifier(max_depth=6, random_state=42),
        "随机森林": RandomForestClassifier(n_estimators=100, random_state=42),
    }
    print(f"{'模型':<8}{'准确率':>8}{'精确率':>8}{'召回率':>8}{'F1':>8}")
    best = (None, 0.0)
    for name, model in models.items():
        model.fit(Xtr, ytr)
        p = model.predict(Xte)
        acc = accuracy_score(yte, p)
        pr = precision_score(yte, p, average="macro")
        rc = recall_score(yte, p, average="macro")
        f1 = f1_score(yte, p, average="macro")
        print(f"{name:<8}{acc:>8.3f}{pr:>8.3f}{rc:>8.3f}{f1:>8.3f}")
        if acc > best[1]:
            best = (name, acc)

    pred2 = models[best[0]].predict(Xte[:2])
    print("\\n预测 vs 真实(前2条):",
          [LABELS[i] for i in pred2], "vs", [LABELS[i] for i in yte[:2]])
    print(f"决策结论: 交付模型={best[0]}(acc={best[1]:.3f}); "
          "随机森林可给特征重要度, 逻辑回归可作产线侧轻量基线。")
''',
 },
 "m12": {
  "clean_outliers": '''def clean_outliers(X, y):
    """清洗噪声样本: 对每个特征按3σ截断(记录删除条数)"""
    z = (X - X.mean(0)) / X.std(0)
    mask = (np.abs(z) < 3).all(axis=1)
    print(f"3σ清洗: {len(X)} → {int(mask.sum())} 条（删除 {int((~mask).sum())}）")
    return X[mask], y[mask]
''',
  "build_features": '''def build_features(X):
    """派生特征≥2个: vibration/current, temp*pressure → (N, 5+k)"""
    rpm, temp, press, vib, amp = X.T
    return np.c_[X, vib / np.maximum(amp, 1e-6), temp * press]
''',
 },
 "m31": {
  "measure": '''def measure(path):
    """返回 标注图, [(类型, 尺寸mm)]"""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    results = []
    anno = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for cnt in contours:
        if cv2.contourArea(cnt) < 15:
            continue
        rect = cv2.minAreaRect(cnt)
        w, h = sorted(rect[1])
        if w / max(h, 1) > 3:
            txt = f"scratch {w * PX_TO_MM:.2f}mm"
            results.append(("划痕", round(w * PX_TO_MM, 2)))
        else:
            txt = f"pit {cv2.contourArea(cnt) * PX_TO_MM ** 2:.2f}mm2"
            results.append(("凹坑", round(cv2.contourArea(cnt) * PX_TO_MM ** 2, 2)))
        box = cv2.boxPoints(rect).astype(int)
        cv2.drawContours(anno, [box], 0, (0, 0, 255), 2)
        cv2.putText(anno, txt, (int(box[:, 0].min()), int(box[:, 1].min()) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    return anno, results
''',
 },
 "m41": {
  "cut": '''def cut(t):
    """jieba分词+去停用词, 空格连接"""
    import jieba
    stop = set("的 了 在 是 请 尽快 处理 影响 生产 班中 巡检 发现 已 挂牌 停机".split())
    return " ".join(w for w in jieba.cut(t) if w not in stop and w.strip())
''',
 },
 "m42": {
  "chat": '''def chat(msgs):
    """调用本地LLM(OpenAI兼容), 带重试与降级(容错必做)"""
    import time
    import requests
    BASE = "http://127.0.0.1:8000"
    last = None
    for i in range(3):
        try:
            r = requests.post(f"{BASE}/v1/chat/completions",
                              json={"messages": msgs}, timeout=5)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            last = e
            time.sleep(1 + i)
    return f"[降级] LLM服务不可达，已回退规则通道（{last}）"
''',
 },
}

# ── 补充：m21 / m22 / m32 ──
A01["m21"] = {
 "TinyCNN": '''class TinyCNN(nn.Module):
    """2卷积+2全连接（完成态）"""

    def __init__(self, num_classes=4):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 8, 3)    # 64→62
        self.pool = nn.MaxPool2d(2, 2)     # 62→31
        self.conv2 = nn.Conv2d(8, 16, 3)   # 31→29 →pool→14
        self.fc1 = nn.Linear(16 * 14 * 14, 64)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.flatten(1)
        return self.fc2(torch.relu(self.fc1(x)))
''',
 "main": '''def main():
    (Xtr, ytr), (Xte, yte) = load_dataset()
    print("形状追踪: 输入", Xtr.shape, "(N,C,H,W)")
    device = "cpu"
    model = TinyCNN().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1.5e-3)
    lossf = nn.CrossEntropyLoss()

    xt, yt = torch.tensor(Xte), torch.tensor(yte)
    xtr, ytr_t = torch.tensor(Xtr), torch.tensor(ytr)
    for epoch in range(6):
        model.train()
        perm = torch.randperm(len(xtr))
        tot = 0.0
        for i in range(0, len(xtr), 32):
            b = perm[i:i + 32]
            opt.zero_grad()
            loss = lossf(model(xtr[b]), ytr_t[b])
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        model.eval()
        with torch.no_grad():
            pred = model(xt).argmax(1)
            acc = (pred == yt).float().mean().item()
        print(f"epoch {epoch + 1} loss={tot / len(xtr):.4f} 测试准确率={acc:.3f}")

    model.eval()
    with torch.no_grad():
        pr = model(xt).argmax(1)
        for k in range(2):
            conf = torch.softmax(model(xt[k:k + 1]), 1).max().item()
            print(f"样本{k}: 预测={CLASSES[pr[k]]} 置信度={conf:.3f}")
    print("形状追踪: (N,1,64,64)→conv1(N,8,62,62)→pool(31)→conv2(N,16,29,29)"
          "→pool(14)→flatten(N,3136)→fc→(N,4)")
''',
}
A01["m22"] = {
 "main": '''def main():
    d = np.load(DATA)
    X, y = d["X"].astype(np.float32), d["y"].astype(np.float32)
    X = X[:, :, None]                    # (N,20)→(N,20,1)
    n = int(len(X) * 0.8)
    Xtr, ytr = torch.tensor(X[:n]), torch.tensor(y[:n])
    Xte, yte = torch.tensor(X[n:]), torch.tensor(y[n:])

    model = RULNet()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lossf = nn.MSELoss()

    for epoch in range(60):
        model.train()
        opt.zero_grad()
        loss = lossf(model(Xtr), ytr)
        loss.backward()
        opt.step()
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                mse = lossf(model(Xte), yte).item()
            print(f"epoch {epoch + 1}  训练loss={loss.item():.4f}  验证MSE={mse:.4f}")

    model.eval()
    with torch.no_grad():
        p = model(Xte)
        mse = lossf(p, yte).item()
        rmse = mse ** 0.5
        mae = (p - yte).abs().mean().item()
    print(f"测试指标: MSE={mse:.4f}  RMSE={rmse:.4f}  MAE={mae:.4f}")
    print(f"业务解读: RMSE={rmse:.2f}（归一化寿命单位）→ 约可提前 {rmse * 30:.1f} 天窗口介入维护。")
''',
}
A01["m32"] = {
 "run_onnx": '''def run_onnx(img_bgr, conf=0.4, imgsz=320):
    """方案B(离线备选): onnxruntime 解析与画框"""
    import onnxruntime as ort
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    x = cv2.resize(img_bgr, (640, 640)).astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None]
    out = sess.run(None, {"images": x})[0][0]        # (84,8400)
    cls = out[4:]
    conf_map = cls.max(0)
    cid = cls.argmax(0)
    keep = conf_map > conf
    boxes = out[:4].T[keep]
    h0, w0 = img_bgr.shape[:2]
    for (cx, cy, w, h) in boxes:
        x1 = int((cx - w / 2) * w0 / 640)
        y1 = int((cy - h / 2) * h0 / 640)
        x2 = int((cx + w / 2) * w0 / 640)
        y2 = int((cy + h / 2) * h0 / 640)
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 0, 255), 2)
    return img_bgr, int(keep.sum())
''',
}
