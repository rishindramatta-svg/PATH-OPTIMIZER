# Design-reference audit

All 15 reference files were inventoried and visually inspected during the design pass. This final documentation pass records the implemented compositions and known differences. A fresh pixel-measured browser comparison could not be completed: the available browser automation stopped when it could not verify the active Windows browser URL. The references are 2880 px desktop and 780 px mobile exports; screenshots show intended composition and token values, not necessarily live backend content.

| PNG | Screen shown | Audit / remaining difference |
|---|---|---|
| `design/01 — Login/Register.png` | Login and registration | Form hierarchy, brand color and card treatment match. The reference's social sign-in and policy links are intentionally absent because they are nonfunctional; no missing auth provider is implied. |
| `design/02 — Student Dashboard.png` | Student dashboard | Main next step, mastery, real-data summary and misconception alert are present. Live values vary from the static reference by account and database state. |
| `design/03 — Knowledge Graph Explorer.png` | Knowledge graph | Graph plus selected-concept information and responsive layout are implemented. Graph positions/content can differ as the real concept model is rendered. |
| `design/04 — Practice Session.png` | Practice session | Question/options, confidence input and diagnostic feedback are wired. Question content and timer state are dynamic. |
| `design/05 — Misconception Repair.png` | Misconception repair | Repair panel, evidence context and misconception-derived example/follow-up are implemented. Exact example text differs with the detected misconception. |
| `design/06 — Learning Path.png` | Learning path | Ordered steps and reasoned revision are live; due spaced reviews add a step type beyond the initial reference content. |
| `design/07 — Misconception Tracker.png` | Misconception tracker | Server-backed status/severity filters and evidence detail work. Row count/state varies with a learner's real history. |
| `design/08 — Analytics Dashboard.png` | Analytics | Server-backed period controls and charts use learner data. Empty/new-account charts necessarily have less plotted history than the filled reference. |
| `design/09 — Instructor View.png` | Instructor cohort | Heatmap, course enrollment and scoped cohort data are live. A new course with no enrolled learners displays a smaller/empty cohort than the reference. |
| `design/10 — Admin/Ops Dashboard.png` | Admin/Ops | Operational metrics, real flags and simulator results are present. Exact values differ by run; decorative operational trends are simpler than the reference's fuller time-series display. |
| `design/11 — Edge-case States.png` | Edge-case states | Fast-answer, confidence conflict, offline/reconnecting, malformed input, empty, loading, path-updated toast and retry error states are wired. Some are transient banners/inline variants rather than a pixel-identical state gallery. |
| `design/Mobile — Dashboard.png` | Mobile dashboard | Narrow stacked dashboard and navigation are implemented. The reduced viewport naturally truncates secondary detail below the fold. |
| `design/Mobile — Knowledge Graph.png` | Mobile graph | Responsive graph and concept details are present; graph is more compact than desktop and does not preserve every desktop panel width. |
| `design/Mobile — Practice Session.png` | Mobile practice | Question and confidence flow stacks into a single column; timer/content is dynamic. |
| `design/Mobile — Learning Path.png` | Mobile learning path | Timeline and update feedback stack vertically; exact step heights depend on live path length. |

The token comparison is recorded in [design-system.md](design-system.md). The table lists the known functional/compositional differences, but a fresh final pixel-level audit and screenshot set remain **not verified**. The differences above are mostly live-data states or intentional removal of dead auth controls; no new visual CSS change was made without a valid side-by-side browser capture.
