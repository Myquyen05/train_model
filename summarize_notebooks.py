import json, re, glob, os, sys
from pathlib import Path

NOTEBOOK_GLOBS = ["*.ipynb"]  # quét tất cả notebook ở root
OUT = []

def detect_keywords(src):
    text = src.lower()
    keys = []

    # Frameworks / libs
    for k in [
        "pandas", "numpy", "scikit-learn", "sklearn", "statsmodels",
        "tensorflow", "keras", "torch", "pytorch", "xgboost", "lightgbm", "catboost",
        "prophet", "fbprophet", "arima", "sarima", "lstm", "gru", "rnn", "cnn",
        "transformer", "attention", "optuna", "mlflow", "vnstock", "yfinance"
    ]:
        if k in text: keys.append(k)

    # Metrics
    for m in ["accuracy", "precision", "recall", "f1", "roc_auc", "mae", "mse", "rmse", "mape", "r2"]:
        if re.search(rf"\b{m}\b", text): keys.append(f"metric:{m}")

    # Finance/series hints
    for h in ["close", "open", "high", "low", "volume", "technical indicator", "ta.", "talib", "ema", "rsi", "macd", "bollinger"]:
        if h in text: keys.append(h)

    # Train/eval hints
    for h in ["train_test_split", "fit(", "predict(", "evaluate(", "EarlyStopping", "ModelCheckpoint"]:
        if h.lower() in text: keys.append(h.strip("()").lower())

    return sorted(set(keys))

def extract_markdown_and_code(nb_json):
    md, code = [], []
    for cell in nb_json.get("cells", []):
        if cell.get("cell_type") == "markdown":
            md.append("".join(cell.get("source", [])))
        elif cell.get("cell_type") == "code":
            code.append("".join(cell.get("source", [])))
    return "\n\n".join(md).strip(), "\n\n".join(code).strip()

def summarize_notebook(path):
    try:
        nb = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"file": path, "error": str(e)}

    md, code = extract_markdown_and_code(nb)
    keys = detect_keywords(md + "\n" + code)

    # lấy vài dòng đầu & tiêu đề từ markdown
    title_match = re.search(r"^#\s+(.+)$", md, flags=re.M)
    title = title_match.group(1).strip() if title_match else Path(path).stem

    # lấy các section lớn trong markdown
    sections = re.findall(r"^##\s+(.+)$", md, flags=re.M)

    # đếm số cell
    cells = nb.get("cells", [])
    n_md = sum(1 for c in cells if c.get("cell_type") == "markdown")
    n_code = sum(1 for c in cells if c.get("cell_type") == "code")

    # trích import (để đoán libs chính)
    imports = sorted(set(
        re.findall(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", code, flags=re.M)
    ))
    imports = sorted({a or b for a, b in imports if (a or b)})

    return {
        "file": os.path.basename(path),
        "title": title,
        "sections": sections[:10],
        "cells": {"markdown": n_md, "code": n_code, "total": len(cells)},
        "keywords": keys[:50],
        "top_imports": imports[:30],
    }

def main():
    paths = []
    for g in NOTEBOOK_GLOBS:
        paths.extend(glob.glob(g))
    paths = [p for p in paths if not p.endswith("-checkpoint.ipynb")]
    paths.sort()

    summaries = [summarize_notebook(p) for p in paths]
    OUT.append("# REPORT – Tổng hợp notebook\n")
    OUT.append("Báo cáo auto-generated từ nội dung các notebook trong repo. Mục tiêu: liệt kê frameworks, từ khóa mô hình/metrics, và bố cục markdown để phục vụ viết báo cáo chi tiết.\n")

    for s in summaries:
        OUT.append(f"---\n## {s.get('title','(no title)')}  \n`{s.get('file')}`")
        if "error" in s:
            OUT.append(f"-⚠️ Lỗi đọc: `{s['error']}`")
            continue
        OUT.append(f"- Số cell: {s['cells']['total']} (markdown: {s['cells']['markdown']}, code: {s['cells']['code']})")
        if s["sections"]:
            OUT.append("- Mục lớn (##): " + ", ".join(s["sections"]))
        if s["top_imports"]:
            OUT.append("- Top imports: " + ", ".join(s["top_imports"]))
        if s["keywords"]:
            OUT.append("- Keywords phát hiện: " + ", ".join(s["keywords"]))

    Path("REPORT.md").write_text("\n".join(OUT), encoding="utf-8")
    print("✅ Đã tạo REPORT.md")

if __name__ == "__main__":
    main()
