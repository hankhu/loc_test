#!/usr/bin/env python3
"""
analyze_loc.py
分析 nanogui 和 userver 两个子目录中的 C/C++ 文件行数信息。
使用 cloc 和 scc 两个工具，结果以 CSV 格式保存，并对两者进行比较。
"""

import subprocess
import json
import csv
import os
import sys
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
TARGETS = ["nanogui", "userver"]
C_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
OUTPUT_DIR = BASE_DIR / "loc_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── cloc ──────────────────────────────────────────────────────────────────────

def run_cloc(target_dir: Path) -> list[dict]:
    """运行 cloc，返回逐文件的行数数据（仅 C/C++ 文件）。"""
    cmd = [
        "cloc",
        "--by-file",
        "--skip-uniqueness",
        "--exclude-ext=ipp",
        "--timeout=0",
        "--include-lang=C,C++,C/C++ Header",
        "--json",
        str(target_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[cloc] 错误: {result.stderr}", file=sys.stderr)
        return []

    data = json.loads(result.stdout)
    rows = []
    for filepath, info in data.items():
        # 跳过汇总键
        if filepath in ("header", "SUM"):
            continue
        rows.append(
            {
                "file": str(Path(filepath).relative_to(target_dir)),
                "blank": info.get("blank", 0),
                "comment": info.get("comment", 0),
                "code": info.get("code", 0),
                "total": info.get("blank", 0) + info.get("comment", 0) + info.get("code", 0),
            }
        )
    rows.sort(key=lambda r: r["file"])
    return rows


# ── scc ───────────────────────────────────────────────────────────────────────

def run_scc(target_dir: Path) -> list[dict]:
    """运行 scc，返回逐文件的行数数据（仅 C/C++ 文件）。"""
    cmd = [
        "scc",
        "--by-file",
        "--include-ext", "c,cc,cpp,cxx,h,hh,hpp,hxx",
        "--format", "json",
        str(target_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[scc] 错误: {result.stderr}", file=sys.stderr)
        return []

    data = json.loads(result.stdout)
    rows = []
    for lang_block in data:
        for f in lang_block.get("Files", []):
            filepath = f.get("Location", "")
            rows.append(
                {
                    "file": str(Path(filepath).relative_to(target_dir)),
                    "blank": f.get("Blank", 0),
                    "comment": f.get("Comment", 0),
                    "code": f.get("Code", 0),
                    "total": f.get("Lines", 0),
                }
            )
    rows.sort(key=lambda r: r["file"])
    return rows


# ── CSV 输出 ───────────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "total", "code", "comment", "blank"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  已保存: {path}")


# ── 比较两个工具的结果 ─────────────────────────────────────────────────────────

def compare_results(cloc_rows: list[dict], scc_rows: list[dict], project: str) -> list[dict]:
    """
    对同一项目的 cloc 与 scc 结果做逐文件对比，
    返回差异列表（仅含有差异的字段非零的行）。
    """
    cloc_map = {r["file"]: r for r in cloc_rows}
    scc_map  = {r["file"]: r for r in scc_rows}
    all_files = sorted(set(cloc_map) | set(scc_map))

    diff_rows = []
    for f in all_files:
        c = cloc_map.get(f, {"total": 0, "code": 0, "comment": 0, "blank": 0})
        s = scc_map.get(f,  {"total": 0, "code": 0, "comment": 0, "blank": 0})
        delta_total   = s["total"]   - c["total"]
        delta_code    = s["code"]    - c["code"]
        delta_comment = s["comment"] - c["comment"]
        delta_blank   = s["blank"]   - c["blank"]
        diff_rows.append(
            {
                "file": f,
                "cloc_total": c["total"], "scc_total": s["total"], "delta_total": delta_total,
                "cloc_code":  c["code"],  "scc_code":  s["code"],  "delta_code":  delta_code,
                "cloc_comment": c["comment"], "scc_comment": s["comment"], "delta_comment": delta_comment,
                "cloc_blank":   c["blank"],   "scc_blank":   s["blank"],   "delta_blank":   delta_blank,
            }
        )
    return diff_rows


def save_comparison_csv(diff_rows: list[dict], path: Path):
    fields = [
        "file",
        "cloc_total", "scc_total", "delta_total",
        "cloc_code",  "scc_code",  "delta_code",
        "cloc_comment","scc_comment","delta_comment",
        "cloc_blank",  "scc_blank",  "delta_blank",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(diff_rows)
    print(f"  已保存: {path}")


def print_summary(diff_rows: list[dict], project: str):
    """打印汇总统计。"""
    total_files = len(diff_rows)
    diff_count  = sum(1 for r in diff_rows if r["delta_total"] != 0)
    cloc_total  = sum(r["cloc_total"]   for r in diff_rows)
    scc_total   = sum(r["scc_total"]    for r in diff_rows)
    cloc_code   = sum(r["cloc_code"]    for r in diff_rows)
    scc_code    = sum(r["scc_code"]     for r in diff_rows)
    cloc_cmt    = sum(r["cloc_comment"] for r in diff_rows)
    scc_cmt     = sum(r["scc_comment"]  for r in diff_rows)
    cloc_blank  = sum(r["cloc_blank"]   for r in diff_rows)
    scc_blank   = sum(r["scc_blank"]    for r in diff_rows)

    print(f"\n{'═'*60}")
    print(f"  项目: {project}  |  C/C++ 文件数: {total_files}  |  行数有差异的文件数: {diff_count}")
    print(f"{'─'*60}")
    print(f"  {'指标':<10} {'cloc':>10} {'scc':>10} {'差值(scc-cloc)':>15}")
    print(f"{'─'*60}")
    for label, cv, sv in [
        ("总行数",   cloc_total, scc_total),
        ("代码行",   cloc_code,  scc_code),
        ("注释行",   cloc_cmt,   scc_cmt),
        ("空行",     cloc_blank, scc_blank),
    ]:
        print(f"  {label:<10} {cv:>10,} {sv:>10,} {sv-cv:>+15,}")
    print(f"{'═'*60}\n")


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    for project in TARGETS:
        target_dir = BASE_DIR / project
        if not target_dir.is_dir():
            print(f"[WARN] 目录不存在，跳过: {target_dir}")
            continue

        print(f"\n{'━'*60}")
        print(f"  分析项目: {project}")
        print(f"{'━'*60}")

        # cloc
        print(f"  [cloc] 运行中 ...")
        cloc_rows = run_cloc(target_dir)
        cloc_csv = OUTPUT_DIR / f"{project}_cloc.csv"
        save_csv(cloc_rows, cloc_csv)

        # scc
        print(f"  [scc]  运行中 ...")
        scc_rows = run_scc(target_dir)
        scc_csv = OUTPUT_DIR / f"{project}_scc.csv"
        save_csv(scc_rows, scc_csv)

        # 比较
        diff_rows = compare_results(cloc_rows, scc_rows, project)
        cmp_csv = OUTPUT_DIR / f"{project}_comparison.csv"
        save_comparison_csv(diff_rows, cmp_csv)

        # 打印汇总
        print_summary(diff_rows, project)

    print(f"所有结果已保存至: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
