# IELTS Listening Stage

[简体中文](README.md) ｜ **English**

**Live demo**: https://onecantype.github.io/ielts-listening-stage/

A single-file, offline classroom display for IELTS Listening teachers: transcript on the left, questions on the right, with answer blanking, synonym link lines, rich-text notes, a presenter view, and web-like PDF export. The whole app is one `.html` file — double-click to open, no install, no network.

> 一个给雅思听力老师用的离线单文件演示台：左边听力原文、右边题目，标注挖空、同义替换连线、富文本笔记、投影演讲者视图、导出和网页同版式的 PDF。

Built from a teacher's requirements, written by **DeepSeek**. Issues, forks and pull requests are welcome.

![UI mock](docs/screenshot.svg)

## Features

**Transcript & annotations**

- Two panes with a draggable divider; the transcript can be hidden entirely (`T`).
- Five colour-coded annotation types: answer, distractor, signpost, location, custom. Each can be switched between “show text” and “blanked”; click a coloured blank to peek at the word.
- Pick a type in the legend, then select text to annotate. With no type selected, selecting text adds an underline.
- Click a blank for a menu: show/hide, edit this mark, delete this mark.
- Undo/redo is scoped: transcript marks, question annotations and typed answers each have their own history.

**Questions**

- Four question types: gap-fill (notes / tables), multiple choice, multiple answer, matching — including map labelling with a letter grid.
- Only the radio dot / checkbox accepts an answer; clicking the option text won't select it, and that text can still be annotated.
- Gap inputs grow as you type and are saved per question; the “Ans” button reveals the key for that question.
- Click a gap or a question number to jump to the answer sentence in the transcript, with a highlight pulse.
- Question-side highlights, notes and synonym links; a question-notes panel.

**Synonym links**

- Transcript word ↔ question word, drawn as a pink dashed Bézier curve.
- The gloss lives in a bubble on the curve: drag it along the curve, click it to edit or delete.
- Reverse direction supported (start from the question side); `Esc` cancels.

**Notes**

- Word-like rich-text panel: paragraph styles, font size, bold / italic / underline / strike, text and highlight colours, lists, alignment, pasted images.
- Saved per lesson, auto-saved 500 ms after typing; movable, resizable, full-screen.
- The presenter window mirrors the notes and their scroll position.

**Presenter view**

- Opens a second window for the projector, mirroring the teacher's layout in real time.
- The transcript is hidden by default (only the teacher sees it) and can be revealed at any time.
- Font size, split, scroll position, annotations, highlights, notes, links, typed answers and revealed keys stay in sync.

**PDF export**

- **Web layout** (default): two columns, with synonym links and their bubbles preserved; the whole lesson becomes one tall page, closest to the on-screen view.
- **A4 single column**: paginated and paper-friendly.
- Both include coloured marks, highlights, underlines, typed answers, rich-text notes and question annotations.

**Other**

- Three themes (light / dark / high contrast), font size 15–26 px.
- Figures can be uploaded, pasted, replaced or removed; compressed to WebP and kept locally, printed in the PDF.
- Everything auto-saves to `localStorage`; warns before closing with unsaved changes; “save as baseline” snapshots the current state.
- No external links, no network requests; works offline.

## Quick start

```bash
git clone https://github.com/OneCanType/ielts-listening-stage.git
cd ielts-listening-stage
open ielts-listening-stage.html      # macOS; on Windows just double-click
```

Or drag the file into Chrome / Edge. Chrome or Edge 100+ recommended (uses `document.execCommand`, `window.open` + `document.write`, `beforeprint`).

> A local server also works (`python3 -m http.server`) but isn't required — there is no `fetch`.

## Project structure

```
ielts-listening-stage/
├── ielts-listening-stage.html   # the app + self-written demo data (1 unit / 3 lessons / 20 questions)
├── index.html                 # GitHub Pages entry, redirects to the app
├── README.md                  # Chinese README
├── README.en.md               # this file
├── LICENSE
├── NOTICE.md                  # copyright and content notice
├── .gitignore                 # ignores private/, _src/, exported PDFs
├── docs/
│   ├── development-guide.en.md # architecture, state, rendering, interactions, testing, pitfalls
│   ├── data-format.en.md       # JSON schema, question types, annotation offsets, adding lessons
│   ├── 开发规范.md             # Chinese version of the development guide
│   ├── 篇目数据规范.md         # Chinese version of the data format
│   └── screenshot.svg          # UI mock
├── tools/
│   ├── check-data.py          # question-bank validator
│   ├── apply-data.py          # inject any question-bank JSON into the HTML (incl. --demo)
│   ├── demo_data.py           # demo question bank source (text + mark words, offsets computed)
│   ├── make-demo-map.py       # generates the demo map (local webp, not committed)
│   └── demo-map.b64           # base64 of the map (used by the repo)
├── private/                   # real question bank (local only, not in the repo)
└── _src/                      # local backups (local only, not in the repo)
```

## How teachers use it

1. Pick a lesson at the top → click “Show transcript”.
2. In the legend, choose an annotation type (answer / distractor / signpost / location / custom / link), then select text in the transcript.
3. For synonym links: click “Link”, select a transcript word, then select the matching question word, and type a gloss in the bubble.
4. Click a question number or a gap to jump to the answer sentence; “Ans” reveals the key.
5. To show the transcript to students, open “Presenter”, move the window to the second screen, and toggle “Show transcript” there.
6. After class: “Export PDF” → Web layout → “Save as PDF” in the print dialog.

## Data & privacy

- Answers, annotations, notes and figures live in the browser's `localStorage`; nothing is uploaded.
- The demo build uses `ielts-listening-sim-demo`; the full question bank uses `ielts-listening-sim-v1` (`apply-data.py --ls` can change it). The two never mix.
- A different browser or a cleared cache means different data. Export a PDF or save a baseline to keep it.
- `localStorage` is roughly 5 MB; figures are compressed to WebP (max 1500 px, quality 0.92), but many images can still fill it — the app will warn you to export.

## Public demo vs full version

This repo uses the “public code, private data” approach:

| File | Data | Purpose |
| --- | --- | --- |
| `ielts-listening-stage.html` (repo root) | **self-written demo**: 1 unit / 3 lessons / 20 questions | public repo, GitHub Pages, demos |
| `private/ielts-listening-stage.full.html` | real question bank (30 lessons / 264 questions) | for teaching, **never committed** |
| `private/ielts-full-data.json` | real question bank as JSON | backup / regenerate the full build |

`private/` is git-ignored; copy that folder when changing machines.

```bash
# Re-inject the demo after editing tools/demo_data.py
python3 tools/apply-data.py --demo --ls ielts-listening-sim-demo --ver demo-2026-10-24

# Rebuild the full version (write to private/, never to the repo root)
python3 tools/apply-data.py private/ielts-full-data.json \
  --out private/ielts-listening-stage.full.html \
  --ls ielts-listening-sim-v1 --ver 2026-10-24b
```

## Updating the repo

The repo is hosted on GitHub; commit and push as usual:

```bash
git add .
git commit -m "update demo / docs"
git push
```

**Live demo (GitHub Pages)**: Settings → Pages → Source `Deploy from a branch`, branch `main`, folder `/ (root)`. Then visit `https://onecantype.github.io/ielts-listening-stage/`.

## Development & extension

- To change behaviour, add a question type or an annotation type, read [docs/development-guide.en.md](docs/development-guide.en.md) (Chinese: [开发规范.md](docs/开发规范.md)).
- To add a lesson or swap the question bank, read [docs/data-format.en.md](docs/data-format.en.md) (Chinese: [篇目数据规范.md](docs/篇目数据规范.md)), then run:

```bash
python3 tools/check-data.py ielts-listening-stage.html
```

- To change the demo data, edit `tools/demo_data.py` (text + mark words) and run `python3 tools/apply-data.py --demo`.
- To replace the demo map, edit `tools/make-demo-map.py`, run it, then re-inject the data.

## Copyright

The repo contains **only self-written demo data** (three short dialogues/monologues and one hand-drawn map). The demo text, questions and map were written for this project and contain no Cambridge IELTS material.

The real question bank lives in the local `private/` folder. Please don't commit or publish it. If it was committed by mistake, rewrite the Git history (e.g. `git filter-repo`) to remove it completely.

See [NOTICE.md](NOTICE.md).

## About the author & AI disclosure

I'm not a developer — I'm an IELTS listening teacher. Every line of code here was written by **DeepSeek** from the requirements I described, one by one. My job was to explain what I needed, test it in class, and point out what broke. I can barely read the code itself.

So please keep that in mind:

- If the structure, naming or browser compatibility looks unprofessional, feel free to say so.
- Found a bug or have an idea? Open an issue — I'll describe the symptoms as clearly as I can.
- No reply? Just **fork it and change whatever you need**; no permission needed.
- If it happens to help you, a star is more than enough.

Thanks in advance to everyone who helps maintain it.

## License

The code and the self-written demo data are MIT licensed (see [LICENSE](LICENSE)). IELTS is a registered trademark of the Cambridge University Press & Assessment, the British Council and IDP Education; this project is not affiliated with them. If you inject real exam content locally, that content remains the property of its rights holders and is not covered by this license.
