#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把一份题库 JSON 注入到课件 HTML 的 <script id="data"> 里。

用途：
  1. 公开仓库默认用自编示例数据（--demo）；
  2. 本地恢复真实题库（传入 private/ielts-full-data.json）。

用法：
    python3 tools/apply-data.py --demo
    python3 tools/apply-data.py private/ielts-full-data.json
    python3 tools/apply-data.py private/ielts-full-data.json --out private/ielts-listening-stage.full.html \\
        --ls ielts-listening-stage-v1 --ver 2026-10-24b

参数：
    --demo            使用 tools/demo_data.py 里的自编示例（1 单元 / 3 节 / 20 题）
    --html PATH       要改的 HTML（默认 ./ielts-listening-stage.html）
    --out PATH        输出文件（默认覆盖 --html）
    --ls KEY          同时把 localStorage 的 key 改成 KEY（不同题库建议分开）
    --ver VER         同时把 DATA_VER 改成 VER
    --no-backup       覆盖前不备份（默认备份到 _src/）
"""

import argparse
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DATA_RE = re.compile(r'(<script\s+id="data"[^>]*>)(.*?)(</script>)', re.S)


def load_source(args):
    if args.demo:
        import demo_data
        return demo_data.build(), "demo_data.py"
    path = args.source
    if not path:
        raise SystemExit("请给一个 JSON 路径，或加 --demo")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def stats(data):
    lessons = data.get("lessons") or []
    sections = [s for l in lessons for s in (l.get("sections") or [])]
    q = 0
    for s in sections:
        for g in s.get("groups") or []:
            try:
                q += max(0, int(g.get("to", 0)) - int(g.get("from", 0)) + 1)
            except (TypeError, ValueError):
                pass
    return len(lessons), len(sections), q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="题库 JSON")
    ap.add_argument("--demo", action="store_true", help="使用自编示例数据")
    ap.add_argument("--html", default=os.path.join(ROOT, "ielts-listening-stage.html"))
    ap.add_argument("--out", default="")
    ap.add_argument("--ls", default="")
    ap.add_argument("--ver", default="")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    data, src = load_source(args)
    if not isinstance(data, dict) or not isinstance(data.get("lessons"), list):
        raise SystemExit("数据格式不对：顶层要有 lessons 数组")
    if not data["lessons"]:
        raise SystemExit("lessons 为空")

    html_path = os.path.abspath(args.html)
    out_path = os.path.abspath(args.out or html_path)
    if not os.path.exists(html_path):
        raise SystemExit("找不到 HTML：%s" % html_path)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    if not DATA_RE.search(html):
        raise SystemExit('找不到 <script id="data">')

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if "</script" in blob.lower():
        raise SystemExit("题库文本里出现了 </script>，请先转义")
    html = DATA_RE.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)

    if args.ls:
        html, n = re.subn(r"const LS = '[^']*';", "const LS = '%s';" % args.ls, html, count=1)
        if n != 1:
            raise SystemExit("替换 LS 失败")
    if args.ver:
        html, n = re.subn(r"const DATA_VER = '[^']*';", "const DATA_VER = '%s';" % args.ver, html, count=1)
        if n != 1:
            raise SystemExit("替换 DATA_VER 失败")

    if not args.no_backup and out_path == html_path:
        bak_dir = os.path.join(ROOT, "_src")
        os.makedirs(bak_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = os.path.splitext(os.path.basename(html_path))[0]
        bak = os.path.join(bak_dir, "%s.注入前-%s.html" % (base, stamp))
        shutil.copy2(html_path, bak)
        print("已备份：%s" % bak)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    nl, ns, nq = stats(data)
    print("数据来源：%s" % src)
    print("已写入：%s（%.0f KB）" % (out_path, os.path.getsize(out_path) / 1024))
    print("内容：%d 个单元 / %d 节 / %d 题" % (nl, ns, nq))
    rel = os.path.relpath(out_path, ROOT)
    shown = rel if not rel.startswith("..") else out_path
    print("建议接着跑：python3 tools/check-data.py %s" % shown)


if __name__ == "__main__":
    sys.exit(main())
