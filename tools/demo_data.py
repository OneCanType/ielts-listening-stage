#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示题库（自编，无版权问题）：1 个单元 / 3 节 / 20 题。

覆盖四种题型 + 地图题 + 表格填空 + 多选，用来展示引擎的全部能力；
标注坐标按词查找算出来，不手写。

用法：
    python3 tools/apply-data.py --demo          # 注入到主文件
    python3 tools/demo-data.py > /tmp/demo.json # 只看数据
"""

import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, "demo-map.webp")

META = "示例数据 · 自编文本（非真题）"

# ---------------------------------------------------------------- 第一节
S1_TEXT = [
    ("LIBRARIAN", "Good morning. Student services. How can I help?"),
    ("MIA", "Hi. I'd like to book a study room for tomorrow, please."),
    ("LIBRARIAN", "Of course. Can I take your name?"),
    ("MIA", "It's Mia Chen. That's C-H-E-N."),
    ("LIBRARIAN", "Thanks. And your student number?"),
    ("MIA", "It's S4182."),
    ("LIBRARIAN", "Right. We have two rooms free. Room B12 has a whiteboard, and room C7 has a projector."),
    ("MIA", "I'll take B12, please. How long can I keep it?"),
    ("LIBRARIAN", "Up to three hours. After that you need to book again."),
    ("MIA", "That's fine. I only need two hours."),
    ("LIBRARIAN", "Okay. One more thing: you can't bring food into the room, but drinks are fine."),
    ("MIA", "Good to know. Do I need to bring anything?"),
    ("LIBRARIAN", "Just your student card. We'll send the confirmation by email."),
]
S1_MARKS = [
    (1, "study room", "locate", None),
    (3, "Chen", "answer", 1),
    (5, "S4182", "answer", 2),
    (6, "B12", "answer", 3),
    (7, "B12", "answer", 3),
    (6, "whiteboard", "answer", 6),
    (6, "projector", "distract", 6),
    (8, "three hours", "answer", 4),
    (8, "After that", "logic", None),
    (9, "two hours", "answer", 7),
    (10, "food", "answer", 5),
    (10, "drinks", "distract", 5),
    (12, "student card", "answer", 8),
    (12, "email", "locate", None),
]
S1 = {
    "id": "D1-1001",
    "code": "1001",
    "part": 1,
    "meta": META,
    "title": "Booking a study room",
    "groups": [
        {
            "kind": "gap",
            "from": 1,
            "to": 5,
            "title": "Questions 1-5",
            "instr": "Complete the notes below. Write ONE WORD AND/OR A NUMBER for each answer.",
            "layout": [
                {"type": "h", "text": "Study room booking"},
                {"type": "line", "text": "Name: {{1}}"},
                {"type": "line", "text": "Student number: {{2}}"},
                {"type": "line", "text": "Room: {{3}}"},
                {"type": "line", "text": "Maximum booking: {{4}} hours"},
                {"type": "line", "text": "Not allowed in the room: {{5}}"},
                {"type": "table", "caption": "Library services", "head": ["Service", "Where"],
                 "rows": [["printing", "ground floor"], ["IT help", "room C7"], ["book returns", "main desk"]]},
            ],
            "answers": {
                "1": {"a": ["Chen"], "raw": "Chen"},
                "2": {"a": ["S4182"], "raw": "S4182"},
                "3": {"a": ["B12"], "raw": "B12"},
                "4": {"a": ["three", "3"], "raw": "three"},
                "5": {"a": ["food"], "raw": "food"},
            },
        },
        {
            "kind": "choice",
            "from": 6,
            "to": 8,
            "title": "Questions 6-8",
            "instr": "Choose the correct letter, A, B or C.",
            "items": [
                {"n": 6, "q": "What does Room B12 have?",
                 "opts": ["a whiteboard", "a projector", "a printer"], "a": "A"},
                {"n": 7, "q": "How long does Mia book the room for?",
                 "opts": ["one hour", "two hours", "three hours"], "a": "B"},
                {"n": 8, "q": "What must Mia bring?",
                 "opts": ["her student card", "a laptop", "a printed form"], "a": "A"},
            ],
        },
    ],
}

# ---------------------------------------------------------------- 第二节
S2_TEXT = [
    ("MANAGER", "Welcome to the Riverside Fitness Centre. Let me explain how membership works."),
    ("MANAGER", "The gym and the swimming pool are included in your monthly fee."),
    ("MANAGER", "The sauna is also included, but you need to book it at reception."),
    ("MANAGER", "Classes such as yoga and spinning cost extra — you pay five pounds per class."),
    ("MANAGER", "The studio is free for all members before nine a.m. on weekdays."),
    ("MANAGER", "Unfortunately, the tennis courts are closed for repairs until next month."),
    ("MANAGER", "When you join, you'll get a short induction with a trainer."),
    ("MANAGER", "Please remember to bring your membership card every time — we can't let you in without it."),
    ("MANAGER", "Lockers are available, but you need to bring your own padlock."),
]
S2_MARKS = [
    (1, "gym", "answer", 9),
    (1, "included", "logic", None),
    (2, "sauna", "answer", 10),
    (3, "yoga", "answer", 11),
    (3, "five pounds", "distract", 11),
    (4, "studio", "answer", 13),
    (4, "free", "answer", 13),
    (5, "tennis courts", "answer", 14),
    (5, "closed", "answer", 14),
    (7, "membership card", "answer", None),
]
S2 = {
    "id": "D1-1002",
    "code": "1002",
    "part": 2,
    "meta": META,
    "title": "Riverside Fitness Centre",
    "groups": [
        {
            "kind": "multi",
            "from": 9,
            "to": 10,
            "title": "Questions 9 and 10",
            "instr": "Choose TWO letters, A-E. Which TWO things are included in the monthly fee?",
            "pick": 2,
            "opts": ["yoga classes", "the gym", "the sauna", "spinning classes", "the tennis courts"],
            "a": ["B", "C"],
        },
        {
            "kind": "match",
            "from": 11,
            "to": 14,
            "title": "Questions 11-14",
            "instr": "What is said about each of the following? Choose FOUR answers from the box.",
            "options": [
                {"k": "A", "t": "included in the monthly fee"},
                {"k": "B", "t": "costs extra"},
                {"k": "C", "t": "not available at the moment"},
            ],
            "items": [
                {"n": 11, "q": "yoga classes", "a": "B"},
                {"n": 12, "q": "the sauna", "a": "A"},
                {"n": 13, "q": "the studio before 9 a.m.", "a": "A"},
                {"n": 14, "q": "the tennis courts", "a": "C"},
            ],
        },
    ],
}

# ---------------------------------------------------------------- 第三节
S3_TEXT = [
    ("GUIDE", "Welcome to Greenway Park. Let's start at the main entrance, at the bottom of the map."),
    ("GUIDE", "Walk straight ahead and you'll come to the fountain in the middle of the square."),
    ("GUIDE", "The café is to the left of the fountain, next to the lake."),
    ("GUIDE", "Behind the café, on the north side, you'll find the playground."),
    ("GUIDE", "If you cross the bridge over the lake, you'll reach the rose garden."),
    ("GUIDE", "The car park is on the right-hand side of the park, near the east gate."),
    ("GUIDE", "Finally, the statue stands between the fountain and the east gate."),
]
S3_MARKS = [
    (0, "main entrance", "locate", None),
    (1, "fountain", "answer", 15),
    (2, "café", "answer", 16),
    (3, "playground", "answer", 17),
    (4, "rose garden", "answer", 18),
    (5, "car park", "answer", 19),
    (6, "statue", "answer", 20),
    (6, "Finally", "logic", None),
]
S3 = {
    "id": "D1-1003",
    "code": "1003",
    "part": 2,
    "meta": META,
    "title": "A walk around Greenway Park",
    "groups": [],
}


def _figure():
    if os.path.exists(MAP):
        raw = open(MAP, "rb").read()
    else:
        # 仓库里只提交 base64 文本（demo-map.b64），二进制由 make-demo-map.py 本地生成
        b64 = os.path.join(HERE, "demo-map.b64")
        if not os.path.exists(b64):
            raise SystemExit("缺少 demo-map.webp / demo-map.b64，先运行 python3 tools/make-demo-map.py")
        raw = base64.b64decode(open(b64, "r", encoding="ascii").read().strip())
    return "data:image/webp;base64," + base64.b64encode(raw).decode()


def _transcript(text, marks):
    out = [{"spk": spk, "text": s} for spk, s in text]
    for pi, phrase, cat, q in marks:
        s = out[pi]["text"].find(phrase)
        if s < 0:
            raise SystemExit("第 %d 段找不到 %r" % (pi, phrase))
        e = s + len(phrase)
        t = out[pi]["text"]
        if s > 0 and t[s - 1].isalnum():
            raise SystemExit("%r 起点切在单词中间" % phrase)
        if e < len(t) and t[e].isalnum():
            raise SystemExit("%r 终点切在单词中间" % phrase)
        out[pi].setdefault("marks", []).append(
            {"s": s, "e": e, "cat": cat, "q": q, "note": ""}
        )
    return out


def build():
    s1 = dict(S1, transcript=_transcript(S1_TEXT, S1_MARKS))
    s2 = dict(S2, transcript=_transcript(S2_TEXT, S2_MARKS))
    s3 = dict(S3, transcript=_transcript(S3_TEXT, S3_MARKS))
    s3["groups"] = [{
        "kind": "match",
        "from": 15,
        "to": 20,
        "title": "Questions 15-20",
        "instr": "Label the map below. Write the correct letter, A-F, next to Questions 15-20.",
        "figure": _figure(),
        "items": [
            {"n": 15, "q": "fountain", "a": "C"},
            {"n": 16, "q": "café", "a": "A"},
            {"n": 17, "q": "playground", "a": "F"},
            {"n": 18, "q": "rose garden", "a": "B"},
            {"n": 19, "q": "car park", "a": "E"},
            {"n": 20, "q": "statue", "a": "D"},
        ],
    }]
    return {"lessons": [{"id": "D1", "title": "示例单元（自编）", "sections": [s1, s2, s3]}]}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
