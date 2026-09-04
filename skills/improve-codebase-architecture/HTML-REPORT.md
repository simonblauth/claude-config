# HTML Report Format

The architectural review is rendered as a single self-contained HTML file in the OS temp directory. Tailwind and Mermaid both come from CDNs. Mermaid handles graph-shaped diagrams reliably; hand-built divs and inline SVG handle the more editorial visuals (mass diagrams, cross-sections). Mix the two: don't lean on Mermaid for everything, it'll start to look generic.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="dark" />
    <title>Architecture review for {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({
        startOnLoad: true,
        theme: "dark",
        securityLevel: "loose",
        themeVariables: {
          background: "#0f172a", primaryColor: "#1e293b", primaryBorderColor: "#475569",
          primaryTextColor: "#e2e8f0", secondaryColor: "#334155", tertiaryColor: "#1e293b",
          lineColor: "#64748b", textColor: "#cbd5e1", fontSize: "13px",
          actorBkg: "#1e293b", actorBorder: "#475569", actorTextColor: "#e2e8f0",
          actorLineColor: "#475569", signalColor: "#94a3b8", signalTextColor: "#cbd5e1",
          labelBoxBkgColor: "#1e293b", labelBoxBorderColor: "#475569", labelTextColor: "#e2e8f0",
          loopTextColor: "#cbd5e1", noteBkgColor: "#422006", noteTextColor: "#fde68a",
          noteBorderColor: "#a16207", sequenceNumberColor: "#0f172a",
        },
      });
    </script>
    <style>
      /* small custom layer for things Tailwind doesn't cover cleanly:
         dashed seam lines, schematic labels, the deep-module mass. */
      .seam { stroke-dasharray: 5 4; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
      .lbl { font-size: 10px; letter-spacing: .12em; text-transform: uppercase; }
      .deepbox {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 2px solid #34d399;
        box-shadow: 0 0 0 1px rgba(52,211,153,.12), 0 8px 28px -12px rgba(52,211,153,.35);
      }
      /* diagonal red hatch, laid over a box that leaks */
      .hatch { background-image: repeating-linear-gradient(45deg, rgba(248,113,113,.28) 0 4px, transparent 4px 8px); }
      .mermaid { font-size: 13px; }
      .mermaid svg { max-width: 100%; height: auto; }
      ::selection { background: #34d399; color: #052e1a; }
    </style>
  </head>
  <body class="bg-slate-950 text-slate-200 font-sans antialiased">
    <main class="max-w-5xl mx-auto px-6 py-14 space-y-14">
      <header>...</header>
      <section id="candidates" class="space-y-12">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Palette

Dark only: no light variant, and nothing that assumes a white page. Slate carries every surface, emerald is the single accent, red means leakage, amber means warning. These reports get read late at night.

| Role | Classes |
| --- | --- |
| Page | `bg-slate-950 text-slate-200` |
| Card, and each pane of a before/after pair | `bg-slate-900` on `border-slate-800` |
| Box inside a diagram | `bg-slate-800/60` on `border-slate-700` |
| Heading | `font-serif text-slate-50` |
| Prose | `text-slate-300`; `.lbl` labels and inline asides `text-slate-500` |
| Accent | `text-emerald-300` for accent text and links, `text-emerald-400` for glyphs, `border-emerald-500` for a left rule beside a conclusion, `.deepbox` for the deep-module mass |
| Leakage | `border-red-500/50 bg-red-500/10 text-red-200`, `.hatch` over the box that leaks, arrowheads `#f87171` |
| Warning, ADR callout | `border-amber-500/30 bg-amber-500/10 text-amber-100/80` |

Coloured surfaces are tints, never solids: `bg-<hue>-500/10` over slate stains the page instead of introducing a second background. Badges take the same trio one step brighter, `bg-<hue>-500/15 text-<hue>-300 border-<hue>-500/30`; the neutral badge is `bg-slate-800 text-slate-400 border-slate-700`.

Divide a card's before/after with a `gap-px` grid on `bg-slate-800`, panes `bg-slate-900`: the divider is the grid gap, not a border.

## Header

Repo name, date, and a compact legend: solid box = module, dashed line = seam, red arrow = leakage, emerald-ringed box = deep module. No introduction paragraph. Straight into the candidates.

## Candidate card

The diagrams carry the weight. Prose is sparse, plain, and uses the glossary terms (from the `/codebase-design` skill) without ceremony.

Each candidate is one `<article>`:

- **Title**: short, names the deepening (e.g. "Collapse the Order intake pipeline").
- **Badge row**: recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = neutral), plus a tag for the dependency category (`in-process`, `local-substitutable`, `ports & adapters`, `mock`).
- **Files**: monospaced list, `font-mono text-sm`.
- **Before / After diagram**: the centrepiece. Two columns, side by side. See patterns below.
- **Problem**: one sentence. What hurts.
- **Solution**: one sentence. What changes.
- **Wins**: bullets, ≤6 words each. e.g. "Tests hit one interface", "Pricing logic stops leaking", "Delete 4 shallow wrappers".
- **ADR callout** (if applicable): one line in an amber-tinted box.

No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits the candidate. Mix them. Don't make every diagram look the same. Variety is part of the point.

### Mermaid graph (the workhorse for dependencies / call flow)

Use a Mermaid `flowchart` or `graph` when the point is "X calls Y calls Z, and look at the mess." Wrap it in a Tailwind-styled card so it doesn't feel parachuted in. Style with classDef to colour leakage edges red and the deep module emerald. Sequence diagrams work well for "before: 6 round-trips; after: 1."

```html
<div class="rounded-lg border border-slate-800 bg-slate-900 p-4">
  <pre class="mermaid">
    flowchart LR
      A[OrderHandler] --> B[OrderValidator]
      B --> C[OrderRepo]
      C -.leak.-> D[PricingClient]
      classDef leak stroke:#f87171,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

### Hand-built boxes-and-arrows (when Mermaid's layout fights you)

Modules as `<div>`s with borders and labels. Arrows as inline SVG `<line>` or `<path>` elements positioned absolutely over a relative container. Reach for this when you want the "after" diagram to feel like one `.deepbox` mass with greyed-out internals, since Mermaid won't render that with the right weight.

### Cross-section (good for layered shallowness)

Stack horizontal bands (`h-12 border-l-4`) to show layers a call passes through. Before: 6 thin layers each doing nothing. After: 1 thick band labelled with the consolidated responsibility.

### Mass diagram (good for "interface as wide as implementation")

Two rectangles per module: one for interface surface area, one for implementation. Before: interface rectangle is nearly as tall as the implementation rectangle (shallow). After: interface rectangle is short, implementation rectangle is tall (deep).

### Call-graph collapse

Before: a tree of function calls rendered as nested boxes. After: the same tree collapsed into one box, with the now-internal calls shown faded inside it.

## Style guidance

- Lean editorial, not corporate-dashboard. Generous whitespace.
- Keep diagrams ~320px tall so before/after sits comfortably side by side without scrolling.
- Label modules inside diagrams with `.lbl`, so they read as schematic, not as UI.
- The only scripts are the Tailwind CDN and the Mermaid ESM import. The report is otherwise static: no app code, no interactivity beyond Mermaid's own rendering.

## Top recommendation section

One larger card. Candidate name, one sentence on why, anchor link to its card. That's it.

## Tone

Plain English, concise, but the architectural nouns and verbs come straight from the `/codebase-design` skill. Concision is not an excuse to drift.

**Use exactly:** module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.

**Never substitute:** component, service, unit (for module) · API, signature (for interface) · boundary (for seam) · layer, wrapper (for module, when you mean module).

**Phrasings that fit the style:**

- "Order intake module is shallow: interface nearly matches the implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: HTTP in prod, in-memory in tests."

**Wins bullets** name the gain in glossary terms: *"locality: bugs concentrate in one module"*, *"leverage: one interface, N call sites"*, *"interface shrinks; implementation absorbs the wrappers"*. Don't write *"easier to maintain"* or *"cleaner code"*, because those terms aren't in the glossary and don't earn their place.

No hedging, no throat-clearing, no "it's worth noting that…". If a sentence could be a bullet, make it a bullet. If a bullet could be cut, cut it. If a term isn't in the `/codebase-design` glossary, reach for one that is before inventing a new one.
