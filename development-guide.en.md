# Development Guide

[中文](开发规范.md) ｜ **English**

> For engineers or AI continuing this project. After reading it you should be able to add a question type, add an annotation category, change interactions or change the PDF export without breaking existing behaviour.
>
> Companion docs: [Question-Bank Data Format](data-format.en.md) · [README](../README.en.md)

**Contents**: [1 Constraints](#1-scope-and-hard-constraints) · [2 Runtime](#2-runtime-and-stack) · [3 Data flow](#3-data-flow-one-way-full-re-render) · [4 State](#4-state-model-t) · [5 Persistence](#5-persistence) · [6 Annotations](#6-annotation-system-core) · [7 Questions](#7-question-rendering) · [8 Notes](#8-rich-text-notes) · [9 Presenter](#9-presenter-view) · [10 PDF export](#10-pdf-export) · [11 Styles](#11-styles-and-design-standards) · [12 Conventions](#12-code-conventions) · [13 Task map](#13-common-tasks) · [14 Testing](#14-testing-and-acceptance) · [15 Pitfalls](#15-known-pitfalls) · [16 Performance](#16-performance-and-capacity) · [17 Out of scope](#17-explicitly-out-of-scope) · [18 Glossary](#18-glossary) · [Appendix A](#appendix-a-feature-behaviour)

---

## 1. Scope and hard constraints

**In one sentence**: a classroom projector tool for IELTS listening teachers — transcript on the left, questions on the right, all annotations / answers / notes stored locally, exported to PDF when needed.

These 8 rules are **hard constraints**. Check them before changing code:

| # | Constraint | Why |
| --- | --- | --- |
| 1 | **Single file**: all styles, data and logic in one `.html` | Teachers must be able to double-click it, send it in WeChat, put it on a USB stick |
| 2 | **Zero external dependencies**: no CDN, webfont, framework or remote image | Must work when the classroom network is down; offline archive |
| 3 | **No network**: no `fetch` / `XMLHttpRequest` / analytics | Student data and lesson content never leave the machine |
| 4 | **State in `localStorage`**, ~5 MB | There is no backend |
| 5 | **Presenter is read-only**: no teacher-only actions (save / answer / clear) in the projected window | Students can see it |
| 6 | **Re-render must not interrupt typing**: inputs and notes keep focus and caret | The teacher is typing in class |
| 7 | **Colour is semantic**: a category has the same colour in the main window, the projector and the PDF (PDF uses light backgrounds) | Students learn the colour code |
| 8 | **Destructive actions are reversible**: deleting marks / clearing notes can be undone or asks twice | Mistakes in class are expensive |

Adding a dependency, splitting files or adding a backend overturns the product shape — confirm with the owner first.

---

## 2. Runtime and stack

- Target: Chrome / Edge 100+ (Safari mostly works; `document.execCommand` and print pagination differ slightly).
- Deliberately non-modern APIs — do not “upgrade” them casually:
  - `document.execCommand`: rich-text bold / colour / font size (`contenteditable` has no standard equivalent).
  - `window.open('', '_blank')` + `document.write`: the presenter window and the print page are **same-origin new documents**, driven through `opener`.
  - `window.print()` + `@page`: PDF export.
  - `localStorage`: the only persistence layer.
- Images: `canvas.toDataURL('image/webp', 0.92)`, fallback JPEG 0.9, white background.
- No build step, no npm, no TypeScript. Node is only used by `tools/` and local tests.

### 2.1 File layout (order matters)

```
ielts-listening-stage.html
├── <style>            ① global styles + theme tokens + component styles + print aids
├── <body>             ② DOM skeleton: topbar / trPane / dragbar / qPane / overlays / notes / menus
├── <script id="data"> ③ question-bank JSON (pure data, not executed)
└── <script>           ④ main logic (~5,000 lines, in the section order below)
```

Main-logic sections (search the comment banners):

```
data → state T → storage → transcript rendering → question rendering → figures → header / strip / counts
→ jump-to-answer → question annotations → undo → save / init / clear → rich-text notes
→ font / theme / split → exit → PDF export → links → presenter → boot
```

> The data block must be `id="data"` and must precede the main script: `JSON.parse(document.getElementById('data').textContent)`.

---

## 3. Data flow: one-way, full re-render

```
  #data (JSON)
      │ parsed once at boot
      ▼
  SECTIONS[] ──► sec() = SECTIONS[T.idx]
      │
      │ all mutable state lives in T
      ▼
  T (answers / custom / qhl / notes / figs / proj …)
      │ after a change: persist() + local or full render
      ▼
  innerHTML of #trBody / #qPane   ← rebuilt as a whole every time
```

Three rules:

1. **Never treat the DOM as the data source.** Input values go back to `T.answers` via `setVal()`; the DOM is only a projection.
2. **Render functions must be idempotent.** `renderTranscript()` / `renderQuestions()` can be called at any time with the same result.
3. **Always delegate events.** `innerHTML` is rebuilt, so per-element `onclick` disappears; current code binds to stable containers (`document`, `#qPane`, `#trBody`).

### 3.1 Globals

| Name | Purpose |
| --- | --- |
| `DATA` / `LESSONS` / `SECTIONS` | Raw data, units, flattened lessons (`_li/_si` record ownership) |
| `T` | The only mutable state, see §4 |
| `DEFAULTS[secId]` | Default marks from `flattenMarks(sec)` — read-only |
| `markUndo / markRedo` | Per-`secId` undo stacks for transcript marks |
| `ansUndo / ansRedo` | Per-`secId` undo stacks for answers + question annotations |
| `lastEditArea` | `'tr' | 'q'`, decides which side Ctrl+Z affects |
| `projWin` | Presenter window reference, `null` when closed |
| `DATA_VER` | Default-annotation version, see §5.2 |

`sec()`, `key(n)` and `esc()` are the three most used helpers.

---

## 4. State model (`T`)

```js
T = {
  idx,            // current lesson index
  answers: { "B1-1441|3": "trees" },   // key = `${secId}|${question}`
  flags: {},      // legacy “flagged questions”, unused by the current UI
  custom: { "B1-1441": [mark…] },      // hand edits; falls back to DEFAULTS
  qhl:    { "B1-1441": [qrec…] },      // question-side highlights / notes / links
  baseline: null, // { ver, marks:{secId:[…]}, qhl:{secId:[…]} } from “save as baseline”
  showCats: { answer:false, distract:false, logic:false, locate:false, help:false }, // true = show text, false = blank
  fs: 23,         // root font size in px, 15–26
  theme: 'dark',  // light | dark | contrast
  submitted: {},  // legacy
  uiVersion: 3,   // UI migration version
  proj: { tr:false, split:52 },        // presenter: show transcript, left pane %
  figs: { "B1-1441|1": "data:image/webp;base64,…" }, // figure override; '' = explicitly removed
  notes: { "B1-1441": "<p>…</p>" },    // rich-text HTML
  notesUI: { w,h,x,y,full } | null,    // notes panel geometry
  dataVer: '2026-10-24b',              // compared with DATA_VER
  exLayout: 'web' | 'a4'               // default PDF layout
}
```

### 4.1 DOM mapping

| State | Where it shows |
| --- | --- |
| `idx` | Lesson strip highlight, `renderHeader()` |
| `answers` | `.gap-in` value, `.sel` on dots, answered state in the number strip |
| `custom` | `<mark class="mk …">` / `.blank` inside `#trBody` |
| `qhl` | `<mark class="q-mk …">` inside `#qPane`, question-notes list |
| `showCats` | `.off` on legend chips; blank vs text |
| `fs` | `document.documentElement --fs` |
| `theme` | `<html data-theme>` |
| `proj` | `body.tr-off`, `--proj-trw` in the presenter |
| `figs` | `img` inside question groups |
| `notes` | Rich-text panel content |

### 4.2 Dirty flags

- `dirtyMarks` / `dirtyQ`: there are changes not yet “saved to this page”.
- Call `markDirtyMarks()` / `markDirtyQ()` after edits; the banner appears in the top bar and above the transcript.
- `beforeunload` and the Exit button use these flags (`updateDirtyUI()`).
- Note: `persist()` **auto-saves locally**; “dirty” only means “the user hasn't explicitly pressed Save”. Do not mix them up.

---

## 5. Persistence

```js
localStorage[LS] = JSON.stringify({
  idx, answers, flags, custom, qhl, baseline, showCats, fs, theme, submitted,
  uiVersion, proj, figs, notes, notesUI, dataVer, exLayout
})
```

> `LS` is a constant in the main script: the public demo uses `ielts-listening-sim-demo`, the full question bank uses `ielts-listening-sim-v1` (`tools/apply-data.py --ls` changes it). The two data sets never touch each other.

- There is exactly one writer: `persist()`. **Every change to `T` must end with it.**
- At boot the saved object is applied once with `Object.assign(T, saved)`, then defaults fill the gaps.
- Quota: about 5 MB per origin. `persist()` catches `QuotaExceededError`, shows “export a PDF first” once (`storageWarned`) and keeps going.
- Figures dominate the quota: one WebP is usually 40–120 KB (×1.33 after base64). Estimate before adding many.

### 5.1 Public build vs full build

`ielts-listening-stage.html` in the repo root uses the **self-written demo** (`tools/demo_data.py`) and is safe to publish. The real bank lives in `private/` (git-ignored); generate a full HTML for teaching:

```bash
# Demo (public)
python3 tools/apply-data.py --demo --ls ielts-listening-sim-demo --ver demo-2026-10-24

# Full (private, write to private/)
python3 tools/apply-data.py private/ielts-full-data.json \
  --out private/ielts-listening-stage.full.html \
  --ls ielts-listening-sim-v1 --ver 2026-10-24b
```

The injector only replaces the contents of `<script id="data">` (and optionally `LS` / `DATA_VER`); it does not touch other code.

### 5.2 Version migration

| Field | Effect |
| --- | --- |
| `uiVersion` | UI behaviour migration (e.g. old default “show text” → new default blank). Anything other than 3 triggers `mergeHelpDefaults()` |
| `dataVer` | Annotation-bank version. If `T.dataVer !== DATA_VER` at load, `T.custom` and `T.baseline` are cleared, defaults are re-applied and a toast is shown once |
| `baseline.ver` | Only a baseline with `ver === DATA_VER` is used |

After changing default marks (`transcript[].marks`), choose one:

- **Want every client to pick up the new defaults** → bump `DATA_VER`. Cost: local `T.custom` and `T.baseline` are cleared (teachers lose hand edits). Only for large question-bank changes.
- **Fixing one or two typos / offsets without losing hand edits** → leave `DATA_VER` alone, accepting that browsers which already edited that lesson keep the old snapshot.

Rule of thumb: is this change worth asking every teacher to redo their annotations?

---

## 6. Annotation system (core)

### 6.1 Categories and priority

| cat | Label | Meaning | Main-window colour | `CAT_PRI` |
| --- | --- | --- | --- | --- |
| `note` | Note | Comment, never blanked | purple | -1 |
| `link` | Synonym | Link endpoint | pink | -0.5 |
| `answer` | Answer | Answer word / sentence | green | 0 |
| `logic` | Signpost | Contrast / cause / correction | blue | 1 |
| `distract` | Distractor | Wrong options, corrected-away content | red | 2 |
| `locate` | Location | Question keywords, time markers | yellow | 3 |
| `help` | Custom | Definitions, examples, spelling hints | cyan | 4 |
| `underline` | Underline | Line only, no fill | violet line | 4.5 |

Priority decides **which mark wins on overlap**: lower is stronger (`note` highest, `underline` lowest). `answer` overlapping `link` shows `link` on purpose — the link must stay visible.

### 6.2 Transcript mark

```js
{
  id: 'd-12-0' | 'm-…' | 'lk-…' | 'help-…', // defaults d-p-i; hand edits m-/lk-/help-
  p: 12,          // transcript paragraph index
  s: 135, e: 142, // character offsets inside the paragraph, [s, e)
  cat: 'answer',  // see above
  q: 5 | null,    // related question (optional, used in tooltips)
  note: '',       // comment (for link marks this is the bubble text)
  // link only:
  qk: 'q-15', qs: 4, qe: 10, qa: 'statue',
  bt: 0.5         // bubble progress along the curve, 0–1; absent if never dragged
}
```

**Offset rules (must follow)**

- Offsets are **JS string indices (UTF-16 code units)**, not “the nth character”. Emoji / rare glyphs can take two code units.
- They must cover a **whole word**: never split letters, digits, `-`, `'` or `’`. A blank that reveals half a word confuses students.
- Preserve case and curly quotes; never normalise.
- Full check: `python3 tools/check-data.py` (§11 of the data doc).

### 6.3 Transcript rendering

`renderTranscript()` → `paintPara(pi, text, marks)`:

1. Collect all `s/e` plus `0` and `text.length` as cut points, sort into `cuts`.
2. Each `[a,b)` is a segment; find every mark covering it.
3. No coverage → output the text.
4. Covered → take the `top` mark with the smallest `CAT_PRI`:
   - `top.cat === 'answer'` and `T.showCats.answer === false` → output `.blank` (coloured blank block, `data-ids` records the covering ids);
   - otherwise output `<mark class="mk {cat}" data-p data-s data-e data-ids>`.
5. `data-ids` is a comma-separated list of every covering id; the context menu uses it to resolve clicks.

> `note` always renders as a purple highlight; it is never blanked.

**Show / blank**: legend chips change `T.showCats[cat]`. Toggling a single blank only changes **the DOM** (`open` / `blank` on `el.classList`); to change data use “edit this mark” → change category or delete.

**Clicking a coloured word / blank**: `openMkMenu(el)` opens `#mkMenu`
- Title: `category · Qn · N layers`
- Buttons: `Show text / Blank` (blanks only), `Edit this mark…`, `Delete this mark`
- Delete: `pushMarkUndo()` → filter from `T.custom[s.id]` → `persist()` → re-render → `drawLinks()`.

### 6.4 Question-side records `qhl`

```js
{ id:'lk-…'|'q-…', key:'q-15', start:4, end:10,
  type:'hl'|'note'|'link', note:'', quote:'statue' }
```

`key` identifies a question text block and must match the `data-qk` written at render time:

| key | Block | Created by |
| --- | --- | --- |
| `gt-<from>` | Group title | `renderGapGroup` / `renderChoiceGroup` / … |
| `gi-<from>` | Group instructions | `instrBlock()` |
| `q-<n>` | Choice stem / matching item text | `renderChoiceGroup` / `renderMatchGroup` |
| `opt-<n>-<K>` | Choice option | `renderChoiceGroup` |
| `mopt-<from>-<K>` | Multi-answer option | `renderMultiGroup` |
| `gh-<from>-<idx>` | Gap sub-heading (`type:'h'`) | `renderGapGroup` |
| `gl-<from>-<idx>` | Gap line (`type:'line'`) | `renderGapGroup` |
| `gt-<from>-<ri>-<ci>` | Table cell | `renderGapGroup` |
| `gc-<from>-<idx>` | Table caption | `renderGapGroup` |

> The `gt-` prefix is used for both group titles (2 parts) and table cells (4 parts); the part count keeps them apart.
> `start/end` are offsets in the **rendered text**: `{{n}}` placeholders in gap lines are skipped (`fillGaps` advances `pos` without them), i.e. positions in the plain text students see, excluding inputs. Blocks without placeholders (stems / options / instructions) behave like raw text.
> Render with `paintQSeg(text, base, qrecs(key))` in that coordinate system.

### 6.5 Synonym links (two endpoints)

A link is stored **twice**, with the same `id`:

```js
// T.custom[secId]
{ id:'lk-abc', cat:'link', p:17, s:135, e:139, q:null, note:'订房',
  qk:'q-1', qs:0, qe:6, qa:'Adelphi', bt:0.5 }
// T.qhl[secId]
{ id:'lk-abc', key:'q-1', start:0, end:6, type:'link', note:'订房', quote:'Adelphi' }
```

- Create: `startLinkPick(sel)` → select in the question pane → `openLinkBubbleForDraft()` → `saveLinkBubble()` writes both records.
- Reverse: select the question text, click `⟷ Link` → `linkFromQ` → select the transcript word.
- Edit gloss: `saveLinkBubble()` updates both `m.note` and `r.note`.
- Delete: `deleteLinkBubbleMark()` removes both.
- When the transcript side is undone, `rebuildLinkQhl(s)` rebuilds question-side link records from `T.custom`; teacher-made highlights / notes on questions are preserved (never overwrite the whole `qhl`).
- Drawing: `drawLinks()` measures both endpoints with `getBoundingClientRect()`, draws a cubic Bézier with `x1 = right edge of the transcript mark`, `x2 = left edge of the question mark`. The bubble default sits in the gutter between panes (curve position at the right edge of `#trPane`); its position is stored as `bt`.
- Redraw on scroll / resize / re-render; current code uses a capturing `document` scroll listener plus `requestAnimationFrame(drawLinks)`.

### 6.6 Undo / redo

| Stack | Snapshot | Trigger |
| --- | --- | --- |
| `markUndo[secId]` | deep copy of `{ marks, qhl }` | any transcript mark change, link creation, bubble drag |
| `ansUndo[secId]` | deep copy of `{ answers, qhl }` | answering, question annotations, clearing answers |

- `pushMarkUndo()` / `pushAnsUndo(n, coalesce)` push **before** the change.
- `ansUndo` coalesces: continuous typing on the same question within 900 ms creates one snapshot (`lastAnsEdit`).
- Ctrl+Z / Ctrl+Y dispatch to `undoMarks()` or `undoAnswers()` based on `lastEditArea`.
- Undoing the transcript never rolls back question highlights / notes — that is what `rebuildLinkQhl` is for.

---

## 7. Question rendering

### 7.1 DOM contract for the four `kind`s

| kind | Wrapper | Key classes / attributes | Answer control |
| --- | --- | --- | --- |
| `gap` | `.q-group[data-kind=gap]` | `.gap-line` / `.gap-table` / `.gap-h`, `data-qk` + `data-gap="1"` | `.gap-cell > input.gap-in[data-q]` |
| `choice` | `.q-group[data-kind=choice]` | `.q[data-q]`, `.q-text[data-qk=q-n]`, `.opt[data-val]` | `.dot[data-pick="1"]` only |
| `multi` | `.q-group[data-kind=multi][data-pick]` | `.opt.multi[data-val]`, `.opt-text[data-qk=mopt-*]`, `.multi-head` (n/N) | `.box[data-pick="1"]` |
| `match` | `.q-group[data-kind=match]` | normal: `.q.match-q[data-q]`, `.slot[data-slot]`, `.opt-card[data-opt]` / `.letter-opt`; map: `.map-group`, `.mg-table`, `.mg-dot[data-map-pick]` | click `.slot` then an option card (or drag); dots on maps |

**Only dots / boxes answer**. The `#qPane` click handler first checks `e.target.closest('[data-pick]')`; clicks on text are treated as text selection and never change an answer. New question types must follow this.

Matching also supports “select slot, then click option”: clicking `.slot` sets `activeSlot` (and clears it if filled); clicking an option card fills that slot and advances to the next empty one. Clicks outside dots / boxes / slots are only for selection.

### 7.2 Gap placeholders

- `{{n}}` in stems / tables / lines marks question n's gap.
- `fillGaps(text, key)` splits the text into “plain segment + gap + plain segment”; plain segments go through `paintQSeg`, gaps become `gapInput(n)`.
- Gap positions affect `qhl` offsets: `paintQSeg`'s `base` is the length of the **raw text walked so far** (including the 5 characters of `{{n}}`), so annotation offsets are in raw-text coordinates.
- Width: `gapWidth(v)` estimates from length; typing updates `input.style.width` without re-rendering.

### 7.3 Answers and reveal

- `answerInfo(n)` returns the answer text per kind:
  - `gap`: `g.answers[n]`; `a[]` is the acceptable list, `raw` is the display form;
  - `choice` / `match`: `items[].a` plus option text;
  - `multi`: `g.a` letters mapped by `from + i`.
- `isRevealed(n)` controls the green key; the “Ans” button only toggles a DOM class. State is in memory (not persisted; everything collapses on reload).
- The `.q-tools` bar has exactly three entries: save, question notes, clear all notes. `clearAnswers()` / `undoAnswers()` still exist but have no UI entry today.

### 7.4 Jump to answer

`jumpToAnswer(n)` falls back through four strategies:

1. A mark in `#trBody mark[data-ids]` carrying that question's `q`;
2. Exact coordinates `mark.mk[data-p][data-s][data-e]`;
3. A `.blank` with the same coordinates;
4. The paragraph `.tr-para[data-p]` of the first `T.custom` mark for that question.

Then `scrollIntoView({behavior:'smooth', block:'center'})`, a hard jump after 300 ms, and a yellow `jumpPulse` outline. Entry points: gap clicks, question numbers, the number strip, and `.mg-dot` on maps.

### 7.5 Figures

- `figKeyOf(g, s) = secId + '|' + g.from`.
- Priority: if the key **exists** in `T.figs` (including an empty string) use it; otherwise use `g.figure`. Empty string = the teacher explicitly removed it.
- `shrinkImageFile(file, maxW=1500)`: scale so the longest edge is 1500, white background, WebP 0.92.
- Entry points: drag / paste / click-to-upload / replace / remove / zoom. Always `persist()` afterwards.
- `needFigure(g)` decides whether a group needs an image: existing figure, or `label the map/plan/diagram` in the instructions.

---

## 8. Rich-text notes

- Storage: `T.notes[secId]` is **an HTML string**, restored with `innerHTML`; saved when the panel closes.
- Saving: 500 ms debounce after typing (`rtSaveSoon()`); forced by `rtBeforeSwitch()` on lesson change and `rtSaveNow()` before export.
- Toolbar: `document.execCommand`. Two traps:
  1. Font size needs `styleWithCSS=false` + `execCommand('fontSize', false, '7')`, then convert `<font size=7>` into `<span style="font-size:Npx">`;
  2. Colour / highlight need `styleWithCSS=true`.
- Selection: clicking the toolbar loses it; cache the `Range` with `rtRememberSel()` and restore with `rtRestoreSel()`.
- Paste: sanitise to allowed tags (`p/br/b/strong/i/em/u/s/ul/ol/li/blockquote/pre/span[style]`), drop scripts, classes and remote images (or inline them as base64 when needed).
- Panel geometry / full screen live in `T.notesUI`; when toggling full screen **write state before toggling the class**, otherwise you read stale values.
- Keyboard: while the editor has focus, return early for everything except `Esc` and `Ctrl/Cmd+S`, so `T` and arrow shortcuts never fire while typing.

Two lightweight question-side annotations exist as well:
- `qhl` records with `type:'note'` (the Note button in `#qHlToolbar`) feed `questionNoteList()` and the `#notesPanelQ` panel;
- `qhl` records with `type:'hl'` are highlights; multiple layers stack, a darker colour means 2+ layers.

---

## 9. Presenter view

### 9.1 Structure

`openProjection()`:

1. `window.open('', '_blank')`, then try `placeProjectionOnOtherScreen()` to move it to the second display;
2. `w.document.write(projDocHTML())` — **not an iframe**, a full new document;
3. the main window keeps `projWin`; the new window calls back through `window.opener.__projXxx()`.

`projDocHTML()` copies every `<style>` from the main document, so new styles sync automatically; the presenter body gets `class="proj"` and overrides layout with `.proj-main/.proj-tr/.proj-drag/.proj-q`.

### 9.2 Sync protocol (methods exposed on the opener)

| Method | Purpose |
| --- | --- |
| `__projToggleTr()` | Show / hide the transcript in the presenter |
| `__projFont(delta)` | Change font size (updates `T.fs`, calls `applyFont()`) |
| `__projSetSplit(pct)` | Divider drag → left pane width |
| `__projSaveSplit()` | Persist after dragging |
| `__projScrollFrom(which, ratio)` | Presenter scrolled → main window follows proportionally |
| `__projRedraw()` | Redraw links / note positions in the presenter |

Main → presenter: `syncProjection()` rewrites `#projQ` / `#projTr`, applies font size and theme, and syncs notes and links.

### 9.3 Three pitfalls

1. **Background windows throttle `requestAnimationFrame`**, so scroll sync stutters when the presenter is unfocused. Sync directly inside the scroll handler; do not rely on rAF.
2. **Bidirectional scroll echo**: use `projScrollGuard` / `__syncLock` with a 160 ms window; while applying a remote scroll, do not send it back.
3. **Notes panel geometry**: the two windows differ in size; map positions as **screen-relative percentages** (`projPlaceBox`), never copy pixels.

---

## 10. PDF export

Two builders share `printTranscript` / `printQuestions`:

| Function | Layout | Notes |
| --- | --- | --- |
| `buildWebPrintHTML(o)` | Web layout (default) | 44% transcript / 12% gutter / 44% questions, one very tall page, draws links and bubbles |
| `buildPrintHTML(o)` | A4 single column | Paginated, paper-friendly, no links |

Options: `{ transcript, questions, notes, answers }` (`answers` = also print the answer key; typed student answers are always printed).

### 10.1 Key implementation of the web layout

1. **Endpoint markers**: `printTranscript` adds `data-lk="id1 id2"` to segments (all links covering that segment); `printQSeg` does the same and adds `.p-qlink`.
   > Never rely on “the top-priority mark is a link”, otherwise endpoints disappear when a note / underline covers them.
2. **The print document carries its own layout script**, `__pLayout()`:
   - measure the right-most rect of `#pwLeft [data-lk~=id]` and the left-most rect of `#pwRight …`;
   - draw a cubic Bézier with horizontal control offsets `dx = max(26, |x2-x1| * 0.42)`;
   - place bubbles at `m.bt` or at the gutter centre; shift up on collision, clamp between the top of the columns and the page bottom;
   - finally set `@page{size:210mm <measured height>mm;margin:0}` to make the lesson one tall page.
3. **`<script>` inside the print HTML must be written as `\x3Cscript` / `\x3C/script`**, otherwise it terminates the main document's script block.
4. **`#pBubbles` must be `width:100%`**. An absolutely positioned container with width 0 gives children no available width, so Chinese bubbles wrap one character per line.
5. **No `box-shadow` on bubbles** — Chrome rasterises it into a grey block in the PDF.
6. **Speaker labels `.p-spk` must be `inline-block`**; `display:block` adds a line per paragraph and makes the page 100 mm+ taller.
7. Recompute page height on `load`, `beforeprint` and when called by the opener, so images decoded late do not clip the page.

### 10.2 Checklist when adding exported content

- [ ] Both builders updated? (otherwise the two layouts diverge)
- [ ] No literal `</script>` in the new HTML fragment?
- [ ] Colours use `print-color-adjust: exact`?
- [ ] Content that must not split uses `break-inside: avoid`?
- [ ] Is the A4 page count still reasonable? (verify with §14.3)

---

## 11. Styles and design standards

### 11.1 Design tokens

| Token | Light | Dark | High contrast |
| --- | --- | --- | --- |
| `--bg` | `#eef0f3` | `#211e1d` | `#000` |
| `--panel` | `#fff` | `#2a2624` | `#000` |
| `--ink` | `#171a1f` | `#ede6dd` | `#ffe600` |
| `--ink-2` | `#5b636d` | `#b8aea3` | `#ffe600` |
| `--accent` | `#1a4fd6` | `#d8b26a` | `#ffe600` |
| `--line` | `#dfe3e8` | `#463f39` | `#4a4400` |
| `--m-answer` | `#1f8a5f` | `#7fd3a8` | `#7dff9e` |
| `--m-distract` | `#c0392b` | `#f08a7c` | `#ff8a80` |
| `--m-link` | `#db2777` | `#f472b6` | `#ff79c6` |
| `--m-underline` | `#7c3aed` | `#a78bfa` | `#d8b4fe` |

- **One font-size entry point**: `--fs` (15–26). Every size uses `calc(var(--fs) * ratio)`:
  - top bar `.55–.8`, body `1`, secondary `.44–.62`;
  - panel titles `.75–.9`; link bubbles `.62`.
- Radii: buttons 7 px, cards 10–14 px, marks 2–3 px, bubbles 9 px.
- Shadows: `--shadow` (soft in light, heavier in dark, none in high contrast).
- Transitions: `.15s`, colours / borders / shadows only — no positional animation (projectors stutter).

### 11.2 Layout

- Top bar 56 px; `.main` is a horizontal flex; `#trPane` defaults to 52% (`T.proj.split`); `#dragbar` is 8 px.
- When the transcript is hidden, `.tr-hidden` fills the left pane instead of `display:none` (keeps the split width).
- Speaker column width `--spk-w` is measured by `fitSpeakerCol()` from the longest label (70–160 px); `.tr-spk` uses `nowrap`. Recomputed on rename / font change / lesson change so `LIBRARIAN` / `PRESENTER` never wrap.
- Presenter: `.proj-tr` uses `--proj-trw`; `body.tr-off` hides it.
- Narrow screens (<1100 px) are not supported; this is a desktop / projector tool.

### 11.3 Interaction and accessibility

- Every icon button has a `title`; state uses `aria-pressed` / `aria-checked`.
- Clickable targets are at least 30×30; only dots / boxes answer.
- `Esc` closes overlays / exits annotation arming; `kbd` styling is shared.
- Toasts disappear after 2.2 s; only one at a time.
- UI language is Chinese; short sentences, no jargon.

### 11.4 Print styles

- Print pages are always light (dark theme is not carried into the PDF).
- Colour marks require `print-color-adjust: exact`.
- `@page` width is fixed at 210 mm; the web layout's height is dynamic.
- Tables use `border-collapse` and `0.22mm` rules; `1px` looks fuzzy in PDF.

---

## 12. Code conventions

| Convention | Rule |
| --- | --- |
| Escaping | Every string inserted into HTML goes through `esc()` (main) or `pEsc()` (print); never concatenate raw strings |
| Naming | `renderXxx`, `refreshXxx`, `openXxx/closeXxx`, `xxxOf` |
| Events | Delegate on stable containers; use `pointerdown/move/up` for drag (also works on touch) |
| State | Change `T`, then `persist()`, then render — never the other way round |
| Deep copy | Snapshots / baselines use `clone(obj)` (JSON deep copy; data must be serialisable) |
| Comments | Chinese; explain “why”, especially compatibility workarounds |
| Dependencies | Do not add; discuss first if truly needed |
| Formatting | 2-space indent, single quotes, trailing semicolons, lines ≤ ~120 characters |

**Forbidden**

- Binding events to rendered nodes (they die on the next `innerHTML`).
- Mutating `DEFAULTS` (it seeds new annotations; changing it pollutes untouched lessons).
- Putting DOM nodes, functions or cycles into `T` (`persist` will fail).
- Comments inside `#data` (must be valid JSON).
- A bare `<script>` inside the print-HTML template string.

---

## 13. Common tasks

| Goal | Where | Don't forget |
| --- | --- | --- |
| Add a question type | `renderQuestions` kind dispatch + new `renderXxxGroup` + `answerInfo` + both PDF builders | Data format, `qOrder`, jump-to-answer, presenter (reuses the same render) |
| Add an annotation category | `CAT_LABEL` / `CAT_PRI` / `.mk-xxx` CSS / `renderLegend` / `#markTools` / `pri` in `printTranscript` + print CSS | Legend counts, `markTitle`, menu title |
| Change blanking logic | `showCats` branch in `paintPara` | Legend, `#mkMenu` show-text, `printTranscript` |
| Add an export option | `buildPrintHTML` + `buildWebPrintHTML` | Dialog options, README, print CSS |
| Change presenter layout | `.proj-*` CSS in `projDocHTML` | `projPlaceBox` percentages, scroll sync |
| Change themes | `:root` / `[data-theme=…]` variables | Print colours, link colour, bubble colour |
| Add a top-bar button | `<header class="topbar">` + event section | Must not appear in the presenter |
| Add a setting | `T` default + `persist` whitelist + boot restore | §4 |
| Swap the question bank | `tools/apply-data.py <json>` (or `--demo`) | `DATA_VER`, `check-data.py`, `codeMeta` display |

---

## 14. Testing and acceptance

### 14.1 Manual regression checklist (run the relevant items after every change)

1. The file opens with no errors; the default lesson renders; switching lessons syncs transcript / questions / counts.
2. Show / hide transcript, `T`, divider drag, A−/A+ — nothing jumps.
3. Each of the five annotation types: select to mark, toggle whole category, click a blank to show text / delete.
4. Choice: clicking text does not select; clicking the dot selects and clicking again clears; option text can be annotated.
5. Multi: cannot select more than `pick`; letters are correct.
6. Matching / map: letter boxes select; clicking dots / numbers jumps to the answer sentence.
7. Links: forward, reverse, cancel, edit gloss, drag bubble, delete; both ends disappear together.
8. Undo / redo: transcript edits only roll back transcript; answers only roll back answers; link undo syncs the question side.
9. Notes: open / drag / resize / full screen / auto-save on lesson change / survives reload; pasting formatted text does not break.
10. Presenter: transcript hidden by default; teacher toggles sync; two-way scroll does not jitter; annotations / notes / links / answers sync.
11. Figures: upload survives reload; replace / remove works; PDF includes the figure.
12. Export: web layout is one page with links and bubbles; A4 paginates correctly; both include typed answers and notes.
13. Reload: all state restored; `beforeunload` blocks when there are unsaved changes.
14. Switch through all 30 lessons with no red console errors.

### 14.2 Minimal automation (headless Edge + CDP)

```js
// node test.mjs — requires Chrome/Edge and node 18+
import { spawn } from 'node:child_process';
const edge = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
const url = 'file://' + process.cwd() + '/ielts-listening-stage.html';
const proc = spawn(edge, ['--headless=new', '--remote-debugging-port=9333',
  '--user-data-dir=/tmp/prof-test', '--window-size=1440,900', url]);
// Then fetch('http://127.0.0.1:9333/json/list') for webSocketDebuggerUrl,
// and use Runtime.evaluate to call globals (sec / T / renderQuestions…) for assertions.
```

Key functions are global and can be called from `Runtime.evaluate`:

```js
sec().id                                  // current lesson
T.custom[sec().id].length                 // number of hand marks
buildWebPrintHTML({transcript:true,questions:true,notes:true,answers:false}).length
```

### 14.3 PDF checks

```bash
# Generate (after writing buildWebPrintHTML's output to /tmp/print.html)
"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  --headless=new --no-pdf-header-footer --print-to-pdf=/tmp/out.pdf \
  --virtual-time-budget=4000 file:///tmp/print.html

# Page count and size (macOS)
python3 - <<'PY'
import re
d = open('/tmp/out.pdf','rb').read()
print('pages:', re.findall(rb'/Count\s+(\d+)', d)[:1])   # web layout should be 1
PY
sips -g pixelWidth -g pixelHeight /tmp/out.pdf              # 72dpi: 595 = 210mm
```

### 14.4 Question-bank check

```bash
python3 tools/check-data.py ielts-listening-stage.html
```

It checks contiguous numbers, completeness of answers, `{{n}}` alignment, mark boundaries and link endpoints (see the script header).

---

## 15. Known pitfalls

| Symptom | Cause | Fix |
| --- | --- | --- |
| Whole main script dies, blank page | `</script>` inside a template literal | Write `\x3C/script` |
| PDF bubbles wrap one character per line | Absolutely positioned container width 0 | Container `width:100%` |
| Grey block behind PDF bubbles | `box-shadow` rasterised | Remove the shadow in print CSS |
| Presenter scroll does not follow | Background window throttles rAF | Sync in the scroll handler |
| Two-way scroll jitters | Scroll echo | Guard + 160 ms lock |
| Input values lost after re-render | `innerHTML` does not preserve `input.value` | Render `value="…"`, or avoid full re-render |
| Undo rolled back question highlights | Snapshot includes all of `qhl` | Rebuild with `rebuildLinkQhl`, keep teacher records |
| Font size in notes does nothing | `execCommand('fontSize')` only accepts 1–7 | `styleWithCSS=false` + 7, then convert to px |
| Full-screen notes jumps | Read `T.notesUI` before toggle | Write state first |
| Pressing T while typing shows the transcript | Global shortcut does not exclude editor focus | Return early inside the editor |
| New defaults ignored | Old `baseline` in `localStorage` | Bump `DATA_VER` |
| Storage full, changes lost | Too many images (>5 MB) | Compress, prompt to export |
| Print page clipped | Images load after first layout | Recompute on `load` + `beforeprint` |
| Safari paginates oddly | Different `@page` support | Export with Chrome / Edge |

---

## 16. Performance and capacity

- A lesson has 33–69 paragraphs and ~10 questions; a full `innerHTML` rebuild takes <10 ms. **No virtual DOM needed.**
- The real cost is `drawLinks()`: it redraws every curve on scroll. Above ~30 links, consider viewport culling (current code already skips endpoints outside the viewport).
- Figures dominate storage: a 1500 px WebP is ~60–150 KB, ~80–200 KB after base64. 5 MB holds roughly 20–30 images.
- Images inside rich-text notes are the fastest way to fill the quota; prompt users to compress or use text.

---

## 17. Explicitly out of scope

- Audio playback / dictation timeline (text only today).
- Cloud sync, accounts, collaboration (this is a local tool).
- Mobile / tablet layouts (desktop and projector first).
- A question-bank editor UI (edit JSON + run the checker).
- Word / image export.
- Auto-marking (answer reveal is for the teacher; no scoring).

---

## 18. Glossary

| Term | Meaning |
| --- | --- |
| unit | One entry in `lessons[]`, containing several lessons |
| lesson / section | Smallest teaching unit: one transcript + several question groups |
| group | A contiguous question range; one of four kinds |
| mark | A coloured fragment in the transcript (answer / distractor / …) |
| qrec | A question-side record: highlight / note / link |
| blank | The placeholder shown for an answer mark when text is hidden |
| baseline | A full snapshot of marks saved by “save as baseline” |
| gutter | The space between the two columns in the web-layout PDF, where link bubbles sit |

---

## Appendix A: feature behaviour

> Use this to confirm “how a feature actually behaves”. Add a row when adding a feature so docs and implementation stay in sync.

| # | Feature | Entry | Behaviour and limits | State / code |
| --- | --- | --- | --- | --- |
| 1 | Switch unit / lesson | Lesson strip, unit tabs | Saves notes first; resets question scroll; presenter follows immediately | `setSection()` / `renderTabs()` / `renderStrip()` |
| 2 | Show / hide transcript | Top-bar button, `T` | Hidden keeps the left pane width and shows a locked page; presenter has its own toggle | `#trHidden`, `T.proj.tr` |
| 3 | Font size | A− / A+, also in presenter | 15–26 continuous, global `--fs`, presenter syncs | `applyFont()`, `T.fs` |
| 4 | Theme | Top-bar ◐ | light → dark → contrast; presenter follows; **PDF is always light** | `T.theme`, `[data-theme]` |
| 5 | Divider drag | Middle handle | 8 px handle, presenter syncs percentage | `T.proj.split` |
| 6 | Category show / blank | Legend chips | Five independent categories; “show all” toggles all; counts live | `T.showCats`, `renderLegend()` |
| 7 | Select-to-mark | Legend “mark” → category → select | Marks on selection; Esc leaves armed state; out-of-range offsets are clipped | `setMarkArm()` / `applyTranscriptMark()` |
| 8 | Underline | Select with no category | Underline only, never blanked; coexists with other marks | `cat:'underline'` |
| 9 | Per-mark menu | Click coloured blank / word | Show / blank (DOM only), edit, delete | `openMkMenu()` |
| 10 | Edit mark | Menu → edit | Change category / note / delete; re-render and redraw links | `openEditor()` |
| 11 | Delete mark | Menu / editor | Undoable; link deletes both ends | `pushMarkUndo()` |
| 12 | Undo / redo | Legend buttons, Ctrl+Z / Ctrl+Y | Dispatches on `lastEditArea` to two stacks | §6.6 |
| 13 | Gap answer | Type in the input | Grows as you type, saves immediately, no re-render (caret preserved) | `setVal()`, `#qPane input` |
| 14 | Choice answer | Click dot, click again to clear | Text clicks never select; option text can be annotated | `[data-pick]` |
| 15 | Multi answer | Click checkbox | Stops at `pick`; header shows “n/N” | `.box[data-pick]` |
| 16 | Matching answer | Click slot → option / drag | Advances to the next empty slot; filled slot can be cleared | `activeSlot`, `refreshMatch()` |
| 17 | Map answer | Click dot | Shares matching answers; row highlights the choice | `.mg-dot[data-map-pick]` |
| 18 | Reveal answer | “Ans” beside each question | Display only, never writes an answer; PDF option | `revealed` (memory) |
| 19 | Question toolbar | Top of the question pane | Save / question notes (count) / clear all notes | `.q-tools` in `renderQuestions()` |
| 20 | Jump to answer | Gap / number / strip / map dot | Scrolls the transcript and pulses; four fallbacks | `jumpToAnswer()` |
| 21 | Question selection | Select question text | Highlight / Note / Link toolbar; option text supported | `#qHlToolbar`, `qhl` |
| 22 | Question notes panel | “Question notes” | Lists `type:'note'` records; jump / delete | `questionNoteList()` |
| 23 | Create link | “Link” → transcript word → question word | Bubble asks for a gloss (optional); both sides written together | §6.5 |
| 24 | Reverse link | Select question → “⟷ Link” → transcript word | Same result as forward | `linkFromQ` |
| 25 | Link bubble | Shown automatically; click / drag | Sits in the gutter by default; drag along the curve; position stored as `bt` | `placeLinkTag()` |
| 26 | Edit / delete link | Click bubble → save / delete | Both sides updated; undoable | `saveLinkBubble()` |
| 27 | Rich-text notes | Top-bar “笔记” | Per lesson, 500 ms auto-save, movable / full screen | `T.notes` |
| 28 | Note tools | Panel toolbar | Paragraph style, size, B/I/U/S, colour, highlight, lists, align, images | `document.execCommand` |
| 29 | Notes in presenter | Open the notes panel | Read-only copy at the same relative position; scroll synced | `syncProjNotes()` |
| 30 | Figures | Hover / click the figure area | Upload, paste, replace, remove, zoom; WebP stored locally | `applyFigure()`, `T.figs` |
| 31 | Presenter window | Top-bar “投影” | Same layout mirrored; transcript hidden by default; scroll / font / split / marks / notes sync | §9 |
| 32 | Save locally | Top-bar save, Ctrl+S | Writes `localStorage`, clears dirty flags, no dialog | `saveLocal()` |
| 33 | Save as baseline | Top-bar “存为初始” | Writes all lessons' marks + annotations to `baseline`, clears `custom` | `saveAsBaseline()` |
| 34 | Initialise | Top-bar “初始化” | Confirms; restores baseline annotations and clears typed answers; rich-text notes untouched | `initCurrentSection()` / `initAllSections()` |
| 35 | Clear notes | Legend “clear all notes” | This lesson or all; clears Note records + link glosses, leaves colour marks | `clearNotesScope()` |
| 36 | Export PDF | Top-bar “导出PDF” | Two layouts; options remembered; new window calls `print()` | §10 |
| 37 | Exit | Top-bar “退出” | Three choices when dirty: save & exit / exit without saving / cancel | `finishExit()` |
| 38 | Shortcuts | Global | `T`, `Ctrl+S`, `Ctrl+Z`, `Ctrl+Y`, `←/→`, `Esc`; inside the editor only Esc / Ctrl+S | §11.3 / §8 |
