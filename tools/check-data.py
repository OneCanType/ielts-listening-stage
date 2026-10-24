#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题库校验：检查 ielts-listening-stage.html 里的 <script id="data"> 是否自洽。

用法：
    python3 tools/check-data.py                      # 默认检查同目录上一级的 ielts-listening-stage.html
    python3 tools/check-data.py path/to/file.html    # 指定 HTML
    python3 tools/check-data.py path/to/data.json    # 也可以直接校验纯 JSON

退出码：0 = 没有 error；1 = 有 error。
"""

import json
import os
import re
import sys

WORD = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'\u2019")
CATS = {"answer", "distract", "logic", "locate", "help", "underline", "note", "link"}
IMG_WARN_BYTES = 300 * 1024


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    def err(self, where, msg):
        self.errors.append(f"[error] {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"[warn ] {where}: {msg}")

    def print(self):
        for line in self.errors + self.warnings:
            print(line)
        s = self.stats
        print(
            "\n统计：%d 个单元 / %d 节 / %d 题 / %d 条默认标注"
            % (s.get("lessons", 0), s.get("sections", 0), s.get("questions", 0), s.get("marks", 0))
        )
        print("结果：%d error, %d warning" % (len(self.errors), len(self.warnings)))
        return 0 if not self.errors else 1


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if path.lower().endswith(".json"):
        return json.loads(raw)
    m = re.search(r'<script\s+id="data"[^>]*>(.*?)</script>', raw, re.S)
    if not m:
        raise SystemExit("找不到 <script id=\"data\"> 数据块：%s" % path)
    return json.loads(m.group(1))


def norm(s):
    s = str(s or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def check_marks(rep, where, par, text, qmin, qmax):
    for i, m in enumerate(par.get("marks") or []):
        tag = "%s transcript[%d].marks[%d]" % (where, par.get("_idx", -1), i)
        try:
            s = int(m.get("s"))
            e = int(m.get("e"))
        except (TypeError, ValueError):
            rep.err(tag, "s/e 不是整数")
            continue
        if s < 0 or e > len(text) or s >= e:
            rep.err(tag, "范围越界或为空：s=%d e=%d len=%d" % (s, e, len(text)))
            continue
        if s > 0 and text[s - 1] in WORD:
            rep.err(tag, "起点切在单词中间：%r" % text[max(0, s - 6):s + 6])
        if e < len(text) and text[e] in WORD:
            rep.err(tag, "终点切在单词中间：%r" % text[max(0, e - 6):e + 6])
        cat = m.get("cat", "answer")
        if cat not in CATS:
            rep.err(tag, "未知类别 %r" % cat)
        q = m.get("q")
        if q is not None:
            if not isinstance(q, int) or q < qmin or q > qmax:
                rep.err(tag, "关联题号 %r 不在本节 %d-%d 内" % (q, qmin, qmax))


def check_title(rep, where, g):
    title = g.get("title") or ""
    nums = [int(x) for x in re.findall(r"\d+", title)]
    if not nums:
        return
    if len(nums) == 1:
        if nums[0] != g["from"] or g["from"] != g["to"]:
            rep.err(where, "标题 %r 与题号 %d-%d 不一致" % (title, g["from"], g["to"]))
    elif nums[0] != g["from"] or nums[1] != g["to"]:
        rep.err(where, "标题 %r 与题号 %d-%d 不一致" % (title, g["from"], g["to"]))


def check_gap(rep, where, g, wanted_q):
    placeholders = set()
    for item in g.get("layout") or []:
        if item.get("type") == "table":
            cells = [item.get("caption") or ""] + [c for row in item.get("rows") or [] for c in row]
        else:
            cells = [item.get("text") or ""]
        for c in cells:
            for n in re.findall(r"\{\{\s*(\d+)\s*\}\}", c):
                placeholders.add(int(n))

    answers = g.get("answers") or {}
    keys = set()
    for k, v in answers.items():
        try:
            keys.add(int(k))
        except ValueError:
            rep.err(where, "answers 的键 %r 不是题号" % k)
            continue
        a = v.get("a") if isinstance(v, dict) else None
        if not isinstance(a, list) or not [x for x in a if str(x).strip()]:
            rep.err(where, "第 %s 题没有可接受答案（a 必须是非空数组）" % k)

    for n in sorted(wanted_q - placeholders):
        rep.err(where, "题号 %d 在 layout 里没有 {{%d}} 占位" % (n, n))
    for n in sorted(placeholders - wanted_q):
        rep.err(where, "layout 里的 {{%d}} 超出题号范围" % n)
    for n in sorted(keys - wanted_q):
        rep.err(where, "answers 里的 %d 超出题号范围" % n)
    for n in sorted(wanted_q - keys):
        rep.err(where, "第 %d 题没有答案" % n)


def check_choice(rep, where, g, wanted_q):
    items = g.get("items") or []
    if len(items) != len(wanted_q):
        rep.err(where, "items 数量 %d ≠ 题号数 %d" % (len(items), len(wanted_q)))
    for it in items:
        n = it.get("n")
        if n not in wanted_q:
            rep.err(where, "item 题号 %r 不在范围内" % n)
        opts = it.get("opts") or []
        if len(opts) < 2:
            rep.err(where, "Q%s 选项少于 2 个" % n)
        a = it.get("a") or ""
        if len(a) != 1 or not ("A" <= a <= chr(64 + max(1, len(opts)))):
            rep.err(where, "Q%s 的答案 %r 不在 A-%s 内" % (n, a, chr(64 + max(1, len(opts)))))
        if not str(it.get("q") or "").strip():
            rep.err(where, "Q%s 题干为空" % n)


def check_multi(rep, where, g, wanted_q):
    pick = int(g.get("pick") or 2)
    opts = g.get("opts") or []
    a = g.get("a") or []
    if pick < 2:
        rep.err(where, "pick 至少为 2")
    if len(a) != pick:
        rep.err(where, "答案个数 %d ≠ pick %d" % (len(a), pick))
    if len(wanted_q) != pick:
        rep.err(where, "题号数 %d ≠ pick %d" % (len(wanted_q), pick))
    hi = chr(64 + max(1, len(opts)))
    for x in a:
        if not ("A" <= str(x) <= hi):
            rep.err(where, "答案 %r 不在 A-%s 内" % (x, hi))


def check_match(rep, where, g, wanted_q):
    items = g.get("items") or []
    if len(items) != len(wanted_q):
        rep.err(where, "items 数量 %d ≠ 题号数 %d" % (len(items), len(wanted_q)))
    keys = {o.get("k") for o in (g.get("options") or [])}
    for it in items:
        n = it.get("n")
        a = str(it.get("a") or "")
        if n not in wanted_q:
            rep.err(where, "item 题号 %r 不在范围内" % n)
        if keys and a not in keys:
            rep.err(where, "Q%s 的答案 %r 不在 %s 内" % (n, a, sorted(keys)))
        if not keys and not re.fullmatch(r"[A-Z]", a):
            rep.err(where, "Q%s 的答案 %r 不是单个字母（地图题）" % (n, a))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ielts-listening-stage.html")
    path = args[0] if args else default
    if not os.path.exists(path):
        raise SystemExit("文件不存在：%s" % path)

    data = load_data(path)
    rep = Report()
    lessons = data.get("lessons") or []
    if not lessons:
        rep.err("data", "lessons 为空")

    seen_lessons = set()
    seen_sections = set()
    total_q = 0
    total_marks = 0

    for li, lesson in enumerate(lessons):
        lid = lesson.get("id")
        lw = "lessons[%d]" % li
        if not lid:
            rep.err(lw, "缺少 id")
        elif lid in seen_lessons:
            rep.err(lw, "lesson id 重复：%s" % lid)
        seen_lessons.add(lid)
        if not str(lesson.get("title") or "").strip():
            rep.warn(lw, "缺少 title")

        for si, sec in enumerate(lesson.get("sections") or []):
            sw = "%s/%s" % (lid, sec.get("id") or "section[%d]" % si)
            sid = sec.get("id")
            if not sid:
                rep.err(sw, "缺少 section id")
            elif sid in seen_sections:
                rep.err(sw, "section id 重复：%s" % sid)
            seen_sections.add(sid)
            for f in ("code", "title", "part", "groups", "transcript"):
                if not sec.get(f) and sec.get(f) != 0:
                    rep.err(sw, "缺少字段 %s" % f)

            groups = sec.get("groups") or []
            ranges = []
            for gi, g in enumerate(groups):
                gw = "%s groups[%d]" % (sw, gi)
                if g.get("kind") not in ("gap", "choice", "multi", "match"):
                    rep.err(gw, "未知 kind：%r" % g.get("kind"))
                    continue
                try:
                    frm, to = int(g["from"]), int(g["to"])
                except (KeyError, TypeError, ValueError):
                    rep.err(gw, "from/to 缺失或不是整数")
                    continue
                if frm > to:
                    rep.err(gw, "from > to (%d > %d)" % (frm, to))
                check_title(rep, gw, g)
                ranges.append((frm, to, gw))

                wanted = set(range(frm, to + 1))
                total_q += len(wanted)
                kind = g.get("kind")
                if kind == "gap":
                    check_gap(rep, gw, g, wanted)
                elif kind == "choice":
                    check_choice(rep, gw, g, wanted)
                elif kind == "multi":
                    check_multi(rep, gw, g, wanted)
                elif kind == "match":
                    check_match(rep, gw, g, wanted)

            # 题号连续 / 不重复
            if ranges:
                nums = []
                for frm, to, gw in ranges:
                    nums.extend(range(frm, to + 1))
                dup = sorted({n for n in nums if nums.count(n) > 1})
                if dup:
                    rep.err(sw, "题号重复：%s" % dup)
                lo, hi = min(nums), max(nums)
                missing = sorted(set(range(lo, hi + 1)) - set(nums))
                if missing:
                    rep.err(sw, "题号断号：%s" % missing)

            # 原文与标注
            transcript = sec.get("transcript") or []
            qmin, qmax = (min((r[0] for r in ranges), default=0), max((r[1] for r in ranges), default=0))
            all_text = []
            for pi, par in enumerate(transcript):
                text = par.get("text") or ""
                if not text.strip():
                    rep.err("%s transcript[%d]" % (sw, pi), "text 为空")
                par["_idx"] = pi
                total_marks += len(par.get("marks") or [])
                check_marks(rep, sw, par, text, qmin, qmax)
                all_text.append(text)

            # 答案是否出现在原文（warning，允许同义替换）
            joined = norm(" ".join(all_text))
            for gi, g in enumerate(groups):
                if g.get("kind") != "gap":
                    continue
                for k, v in (g.get("answers") or {}).items():
                    a = (v or {}).get("a") or []
                    if not a:
                        continue
                    # 纯数字答案通常以英文数字读出（eighty-five / forty-eight），不做文字比对
                    if all(re.fullmatch(r"[£$€\s\d.,]+", str(x)) for x in a):
                        continue
                    if not any(norm(x) and norm(x) in joined for x in a):
                        rep.warn("%s groups[%d] Q%s" % (sw, gi, k),
                                 "答案 %r 在原文中找不到（同义替换可忽略）" % (" / ".join(map(str, a))))

            # 配图
            for gi, g in enumerate(groups):
                fig = g.get("figure")
                if not fig:
                    continue
                if not str(fig).startswith("data:image/"):
                    rep.warn("%s groups[%d]" % (sw, gi), "figure 不是 data URL，导出时可能丢失")
                elif len(fig.encode("utf-8")) > IMG_WARN_BYTES:
                    rep.warn("%s groups[%d]" % (sw, gi),
                             "图片约 %.0fKB，建议压到 300KB 以内" % (len(fig) / 1024))

    rep.stats = {
        "lessons": len(lessons),
        "sections": len(seen_sections),
        "questions": total_q,
        "marks": total_marks,
    }
    return rep.print()


if __name__ == "__main__":
    sys.exit(main())
