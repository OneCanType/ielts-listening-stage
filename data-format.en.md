# Question-Bank Data Format

[中文](篇目数据规范.md) ｜ **English**

> This document covers one thing: **how to add, edit or remove a listening lesson**, and what the data structure looks like.
>
> For how the engine works, see the [Development Guide](development-guide.en.md). Every example here can be checked with `python3 tools/check-data.py`.

---

## 1. Where the data lives

The question bank is a single `<script id="data" type="application/json">` block in the middle of the main file, before the main script:

```html
<script id="data" type="application/json">{"lessons":[ … ]}</script>
<script>
  const DATA = JSON.parse(document.getElementById('data').textContent);
  …
</script>
```

- It must be **valid JSON** (no comments, no trailing commas).
- Edit and save, then refresh the page. Or inject it with `python3 tools/apply-data.py my-data.json` (`--demo` restores the built-in demo).
- Data only defines the **default annotations**. Edits made in the UI live in `localStorage` and are never written back to the file.
- The repo root ships the **self-written demo** (public). Keep a real question bank in `private/` and generate a separate HTML for teaching; never commit it.

---

## 2. Top level

```json
{
  "lessons": [
    {
      "id": "B1",
      "title": "第一节 租房住房",
      "sections": [ { …section… } ]
    }
  ]
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `lessons[]` | array | Units; controls the order of the unit tabs |
| `lessons[].id` | string | Unique unit id; prefix of section ids |
| `lessons[].title` | string | Unit title (shown on the tab) |
| `lessons[].sections[]` | array | Lessons in this unit |

---

## 3. Section

```json
{
  "id": "B1-1441",
  "code": "1441",
  "part": 1,
  "title": "Enquiry about booking hotel room for event",
  "groups": [ … ],
  "transcript": [ … ]
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | **Globally unique**, ideally `<lessonId>-<code>`; all local state (answers / marks / notes / figures) is keyed by it |
| `code` | string | yes | Display code. The subtitle parses 3–4 digits as “Cambridge book + Test + Part”; non-numeric codes are shown as-is |
| `meta` | string | no | Overrides the subtitle text, for self-written or non-Cambridge material, e.g. `"示例数据 · 自编对话"` |
| `part` | number | yes | 1–4, display only (Section 1–4) |
| `title` | string | yes | English title, shown in the header and lesson card |
| `groups` | array | yes | Question groups, in ascending question order |
| `transcript` | array | yes | Transcript paragraphs |

### 3.1 Numbering convention (current bank, for reference)

`code` currently means “Cambridge book + Test + Part”:

- `1441` = Book 14 · Test 4 · Part 1 (four digits: 2-digit book + 1-digit test + 1-digit part)
- `1641` = Book 16 · Test 4 · Part 1
- `521` = Book 5 · Test 2 · Part 1

The engine only parses `code` for **display**. For a self-written lesson such as `0001`, add a `meta` field to state the source (see the table above). `id` must still be unique.

---

## 4. Group

Four `kind`s: `gap` / `choice` / `multi` / `match`. Shared fields:

| Field | Type | Notes |
| --- | --- | --- |
| `kind` | string | See below |
| `from` / `to` | number | Inclusive question range; must match the type's rules |
| `title` | string | e.g. `Questions 1-7`, shown above the group |
| `instr` | string | Instructions; can be highlighted / annotated with the `q-` keys |
| `boxTitle` | string | Optional; kept in data but not rendered in the current UI |

**Hard requirements**

1. All groups in a section must cover a **contiguous, non-overlapping** range (can start at 11, but cannot skip 12).
2. The numbers in `title` must match `from/to` (the checker verifies this).
3. Group order is display order.

---

## 5. `gap`: notes / tables

```json
{
  "kind": "gap",
  "from": 1,
  "to": 4,
  "title": "Questions 1-4",
  "instr": "Complete the notes below. Write ONE WORD AND/OR A NUMBER for each answer.",
  "layout": [
    { "type": "h",    "text": "Booking a study room" },
    { "type": "line", "text": "Name: {{1}}" },
    { "type": "line", "text": "Student number: {{2}}" },
    { "type": "line", "text": "Room: {{3}}" },
    { "type": "table", "caption": "Session", "head": ["Day", "Time"],
      "rows": [["Monday", "{{4}} hours"]] }
  ],
  "answers": {
    "1": { "a": ["Chen"], "raw": "Chen" },
    "2": { "a": ["S4182"], "raw": "S4182" },
    "3": { "a": ["B12"], "raw": "B12" },
    "4": { "a": ["two", "2"], "raw": "two" }
  }
}
```

### 5.1 `layout[]` blocks

| type | Fields | Rendering |
| --- | --- | --- |
| `h` | `text` | Sub-heading |
| `line` | `text`, optional `bullet: true` | One line; a leading `● • – -` becomes a bullet automatically |
| `table` | `caption?`, `head[]`, `rows[][]` | Table; `head` may be omitted |

- Gaps are written as `{{n}}`; `n` must be an integer within `from..to`.
- A block may contain several gaps, or none.
- `answers` keys must match `{{n}}` one-to-one. A missing key renders a gap with no answer.

### 5.2 Answer shape

```json
"7": { "a": ["cabins"], "raw": "cabins" }
```

- `a`: **list of acceptable answers** (include case variants, singular/plural, hyphenation). The answer button and the PDF show `a.join(' / ')`.
- `raw`: display string for readability (e.g. `28th;28;` → `28th`). Optional; falls back to `a.join(' / ')`.
- For numbers, include both the digits and the word form in `a` (e.g. `["two", "2"]`).

---

## 6. `choice`: single answer

```json
{
  "kind": "choice",
  "from": 5,
  "to": 6,
  "title": "Questions 5-6",
  "instr": "Choose the correct letter, A, B or C.",
  "items": [
    { "n": 5, "q": "Where is the study room?",
      "opts": ["on the ground floor", "on the first floor", "in the basement"],
      "a": "B" },
    { "n": 6, "q": "What must Mia bring?",
      "opts": ["her student card", "a laptop", "a form"],
      "a": "A" }
  ]
}
```

- `items` count must equal `to - from + 1`; `n` increases by one.
- `opts` has 2–5 entries; letters A/B/C… are generated.
- `a` is a letter within `opts`.
- The stem and every option can be annotated (keys in Development Guide §6.4).

---

## 7. `multi`: multiple answers

```json
{
  "kind": "multi",
  "from": 7,
  "to": 8,
  "title": "Questions 7 and 8",
  "instr": "Choose TWO letters, A-E.",
  "pick": 2,
  "opts": ["get to know colleagues", "learn from mistakes", "ask questions",
           "react to feedback", "enjoy challenges"],
  "a": ["A", "C"]
}
```

- `pick` defaults to 2 and means the group occupies **`pick` question numbers**: `from..from+pick-1`; usually `to = from + pick - 1`.
- `a` length must equal `pick`; letters must exist in `opts`.
- Selection order is recorded as letters; answer order does not matter.

---

## 8. `match`: matching and maps

```json
{
  "kind": "match",
  "from": 9,
  "to": 11,
  "title": "Questions 9-11",
  "instr": "What is said about each facility? Choose THREE answers from the box.",
  "boxTitle": "Availability",
  "options": [
    { "k": "A", "t": "included in the cost" },
    { "k": "B", "t": "available at extra charge" },
    { "k": "C", "t": "not available" }
  ],
  "items": [
    { "n": 9,  "q": "swimming pool", "a": "C" },
    { "n": 10, "q": "gym",           "a": "A" },
    { "n": 11, "q": "tennis courts",  "a": "B" }
  ]
}
```

- With `options`: option cards are shown. If options have only `k` and no `t`, letter buttons are shown.
- `items` count must equal `to - from + 1`; `a` must be in the `options[].k` set (a single uppercase letter if there are no options).
- **Map layout is not detected by missing `options`.** If `instr` contains `label the map` / `label the plan` / `label the diagram`, the map layout is used automatically (see 8.1).

### 8.1 Map questions

A map question = `match` + `figure`, with `Label the map/plan/diagram` in `instr` (the engine switches layout on that phrase):

```json
{
  "kind": "match", "from": 15, "to": 20,
  "title": "Questions 15-20",
  "instr": "Label the map below. Write the correct letter, A–I, next to Questions 15-20.",
  "figure": "data:image/webp;base64,UklGR…",
  "items": [ { "n": 15, "q": "statue", "a": "E" }, … ]
}
```

- Image guidance: **560–900 px wide, WebP, ≤120 KB**; larger images fill up `localStorage`.
- The image must carry letter markers (A, B, C…); answers use the same letters.
- `options` is not required. If present, its `k` values become the dot columns (e.g. A–I).

---

## 9. `transcript`

```json
"transcript": [
  { "spk": "LIBRARIAN",
    "text": "Good morning. How can I help you?",
    "marks": [] },
  { "spk": "MIA",
    "text": "I'd like to book a study room for two hours, please.",
    "marks": [
      { "s": 34, "e": 43, "cat": "answer", "q": 4 },
      { "s": 19, "e": 29, "cat": "locate", "q": 4 }
    ] }
]
```

| Field | Notes |
| --- | --- |
| `spk` | Speaker label: short uppercase name (ANDREW / MIA / NARRATOR). Optional; a monologue can omit it |
| `text` | Verbatim text; keep original punctuation and curly quotes; no manual line breaks |
| `marks` | Default annotations; may be omitted |

### 9.1 `marks[]`

```json
{ "s": 42, "e": 45, "cat": "answer", "q": 4, "note": "" }
```

| Field | Notes |
| --- | --- |
| `s` / `e` | Character offsets inside the paragraph, `[s, e)`; **must cover a whole word or phrase** |
| `cat` | `answer` / `distract` / `logic` / `locate` / `help` / `underline` (defaults usually use the first four) |
| `q` | Related question number; optional |
| `note` | Comment; optional |

**Counting offsets**

- Start at 0; `e` is exclusive.
- Uses JS string indices (UTF-16 code units). For English text this equals “the nth character”; watch out for emoji / rare characters.
- Never cut inside a word: `art` inside `particular` is not a valid boundary.
- Keep case and curly quotes exactly as in the text; do not normalise.

**Annotation advice**

- `answer`: the answer word itself (1–4 words), as short as possible.
- `distract`: other numbers / prices / dates in the same paragraph, corrected-away content.
- `logic`: signpost words and phrases such as however / but / actually / instead / so / because.
- `locate`: where the question keyword lands in the transcript (nouns, place names, times).
- 15–30 marks per lesson is plenty; too many hides the point.

---

## 10. Figures

- Put it on a group: `"figure": "data:image/webp;base64,…"`.
- Replacing / removing an image in the UI stores it in `T.figs["<secId>|<from>"]`, which overrides the data; an empty string means “explicitly removed”.
- Any data URL the browser can display works; WebP is recommended.
- Generating one (macOS):

```bash
python3 - <<'PY'
from PIL import Image
import base64, io
im = Image.open('map.png').convert('RGB')
im.thumbnail((900, 1200))
buf = io.BytesIO(); im.save(buf, 'WEBP', quality=88, method=6)
print('data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode())
PY
```

---

## 11. Adding a lesson: step by step

### 11.1 Prepare

1. Decide **how many questions, which types, which number range**.
2. Split the transcript into one paragraph per speaker; every answer must appear verbatim.
3. Sketch the marks first: which words are answers, distractors, signposts, locations.

### 11.2 Write the JSON

Minimal template (paste into `lessons[].sections` and edit):

```json
{
  "id": "B1-9001",
  "code": "9001",
  "part": 1,
  "title": "Booking a study room",
  "groups": [
    {
      "kind": "gap", "from": 1, "to": 2, "title": "Questions 1-2",
      "instr": "Complete the notes below. Write ONE WORD AND/OR A NUMBER for each answer.",
      "layout": [
        { "type": "h", "text": "Booking" },
        { "type": "line", "text": "Name: {{1}}" },
        { "type": "line", "text": "Room: {{2}}" }
      ],
      "answers": {
        "1": { "a": ["Chen"], "raw": "Chen" },
        "2": { "a": ["B12"], "raw": "B12" }
      }
    },
    {
      "kind": "choice", "from": 3, "to": 3, "title": "Questions 3",
      "instr": "Choose the correct letter, A, B or C.",
      "items": [
        { "n": 3, "q": "How long does Mia book the room for?",
          "opts": ["one hour", "two hours", "three hours"], "a": "B" }
      ]
    }
  ],
  "transcript": [
    { "spk": "LIBRARIAN", "text": "Good morning. How can I help you?" },
    { "spk": "MIA", "text": "I'd like to book a study room for two hours. My name is Mia Chen.",
      "marks": [
        { "s": 34, "e": 43, "cat": "answer", "q": 3 },
        { "s": 56, "e": 64, "cat": "answer", "q": 1 }
      ] },
    { "spk": "LIBRARIAN", "text": "That's right. Room B12, for two hours." }
  ]
}
```

> These offsets are real (`two hours` = 34–43, `Mia Chen` = 56–64); verify them with the script in 11.3.

### 11.3 Compute offsets with a script (recommended)

Never count characters by hand. A throw-away script is safer:

```python
text = "I'd like to book a study room for two hours. My name is Mia Chen."
for word, cat, q in [("two hours", "answer", 3), ("Mia Chen", "answer", 1)]:
    s = text.index(word)
    assert s >= 0
    assert not (s > 0 and text[s-1].isalnum())
    assert not (s + len(word) < len(text) and text[s+len(word)].isalnum())
    print({"s": s, "e": s + len(word), "cat": cat, "q": q})
```

`tools/check-data.py` will verify the boundaries again.

### 11.4 Validate

```bash
python3 tools/check-data.py ielts-listening-stage.html
# or check a plain JSON file
python3 tools/check-data.py my-data.json
```

Must be **0 errors**. Review warnings: they are usually “answer not found in the transcript”, which may mean a missing mark or a different spelling.

### 11.5 Manual acceptance

1. Refresh; the new lesson appears in the picker, title / numbers / counter are correct.
2. Every question accepts an answer; the “Ans” button reveals the key.
3. Clicking each gap / question number jumps to the right sentence.
4. Every annotation type can be applied, blanked and deleted.
5. If there is a figure: it displays, zooms, and appears in the exported PDF.
6. “Export PDF → Web layout”: links (if any) and question layout look right.

---

## 12. Editing and deleting

### 12.1 Changing text or answers

- After editing `text` / `q` / `opts`, **existing offsets may be invalid**; recompute `marks` for that paragraph.
- Re-run the checker after changing `answers`; `a` and `{{n}}` must stay in sync.
- After changing default marks, decide whether to bump `DATA_VER` (Development Guide §5.2): bumping shows the new defaults to everyone but clears local hand edits; not bumping only affects browsers that never edited that lesson.

### 12.2 Deleting a lesson

1. Remove the object from `lessons[].sections`.
2. Local `localStorage` leftovers (`custom` / `qhl` / `answers` / `notes` / `figs`) are not cleaned automatically; they are harmless. To clean up, run in the console:

```js
Object.keys(T.custom).forEach(k => { if (!SECTIONS.some(s => s.id === k)) delete T.custom[k]; });
// same for qhl / answers / notes / figs, then persist()
```

3. `T.idx` is clamped to 0 on startup if it is out of range.

### 12.3 Renumbering

Avoid changing numbers of an existing lesson: `answers` keys are `secId|number`, and `qhl` / `marks.q` also carry numbers. If you must, ask the teacher to “initialise” that lesson afterwards (or bump `DATA_VER`).

---

## 13. What the checker validates

Rules in `tools/check-data.py`:

| Level | Check |
| --- | --- |
| error | empty `lessons` / `sections`; duplicate lesson id or section id; missing `code/title/part/groups/transcript` |
| error | group `from > to`; duplicate or skipped question numbers in a section; `title` numbers inconsistent with `from/to` |
| error | `gap`: `{{n}}` vs `answers` keys; empty answer; `a` not a non-empty array |
| error | `choice`: `items` count ≠ question count; `n` not sequential; fewer than 2 `opts`; `a` out of range |
| error | `multi`: `pick` ≠ `a` length; question count ≠ `pick`; `a` out of range |
| error | `match`: `items` count ≠ question count; `a` not in `options[].k` |
| error | `marks`: `s >= e`, out of range, split inside a word, unknown `cat`, `q` outside the section |
| warning | gap answer not found in the transcript (could be spelling or paraphrase) |
| warning | `figure` is not a data URL; base64 image > 300 KB |

Exit code: `0` = no errors; `1` = errors.

---

## 14. Common mistakes

| Symptom | Cause |
| --- | --- |
| Blank page | Invalid JSON (trailing comma, comment, unescaped quote) |
| Question numbers jump | `from/to` doesn't match `items` count |
| A question has no input | Missing `{{n}}`, or number outside `from..to` |
| “Ans” does nothing | Missing `answers` key, or empty `a` |
| Blank cuts a word in half | `s/e` not on word boundaries |
| Highlight shifted by one | `text` was edited but `marks` were not recomputed |
| New defaults not visible | `DATA_VER` unchanged and an old cache / `T.custom` snapshot exists |
| Map not shown | `figure` is not a data URL, or overridden by an empty `T.figs` entry |
| Links missing in PDF | The question-side `qhl.key` cannot be found at render time (typo) |

---

## 15. Copyright

The copyright of transcripts, questions and map images belongs to the original rights holders (Cambridge University Press & Assessment, Cambridge Assessment English, etc.). The MIT license in this repo covers the code only, not that content.

- For a public repo, use the self-written demo from `tools/demo_data.py`, or content you have the right to use.
- Even for personal teaching, do not redistribute the original texts publicly.
