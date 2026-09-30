# LearnPath reference inventory and design tokens

All 15 supplied PNGs were inspected. Desktop canvases are 2880 px wide; mobile screens are 780 px wide.

## Screen inventory

| Image | Screen |
|---|---|
| `design/01 — Login/Register.png` | Login and registration card, role choice, provider actions |
| `design/02 — Student Dashboard.png` | Student overview, next best step, mastery, study stats, misconception alert |
| `design/03 — Knowledge Graph Explorer.png` | Prerequisite graph with selected concept detail rail |
| `design/04 — Practice Session.png` | Timed question, answer options, confidence slider, diagnostic feedback |
| `design/05 — Misconception Repair.png` | Explanation, worked repair example, targeted check and dependent concepts |
| `design/06 — Learning Path.png` | Ordered curriculum timeline and path revision diff |
| `design/07 — Misconception Tracker.png` | Filterable misconception list and resolution detail |
| `design/08 — Analytics Dashboard.png` | Mastery trend, calibration curve, learning gain, guess-rate metrics |
| `design/09 — Instructor View.png` | Cohort summary, mastery heatmap, misconceptions, at-risk students |
| `design/10 — Admin/Ops Dashboard.png` | Operations metrics, health, flagged sessions and model metrics |
| `design/11 — Edge-case States.png` | Fast-answer nudge, confidence conflict, offline, malformed input, empty, skeleton, toast and error states |
| `design/Mobile — Dashboard.png` | Stacked student dashboard with compact header |
| `design/Mobile — Knowledge Graph.png` | Graph preview, prerequisite node stack and selected concept card |
| `design/Mobile — Practice Session.png` | Single-column timed practice and confidence input |
| `design/Mobile — Learning Path.png` | Compact vertical path and update notice |

The auth and operations images are stored in nested folders (`01 — Login/Register.png` and `10 — Admin/Ops Dashboard.png`).

## Tokens sampled from the PNGs

| Token | Value | Use |
|---|---|---|
| Canvas | `#F8FAFC` | Main page background |
| Surface | `#FFFFFF` | Cards, header, panels |
| Ink | `#0F172A` | Main headings and data |
| Body | `#334155` | Paragraphs and labels |
| Muted | `#94A3B8` | Helper text and captions |
| Border | `#E2E8F0` | Card/input dividers |
| Brand indigo | `#4338CA` | Primary actions and selected navigation |
| Indigo tint | `#EEF2FF` | Focus and recommendation surfaces |
| Mastery teal | `#14B8A6` | Mastered state and positive progress |
| Rose | `#E11D48` | Misconceptions and critical alerts |
| Amber | `#D97706` | Developing state and attention |
| Violet | `#8B5CF6` | Confidence mismatch emphasis |

Typography uses Inter with system sans-serif fallbacks. Layout follows a 4 px spacing scale; reference card padding is generally 20–32 px at CSS scale. Card radius is 20 px, nested panel radius 16 px, controls 12 px, compact tags 7 px, and pill controls fully rounded. Card shadow is restrained (`0 2px 8px rgba(15,23,42,.04)`); elevated overlays use `0 12px 28px rgba(15,23,42,.07)`. Tokens are in `frontend/tailwind.config.cjs` and mirrored as CSS custom properties in `frontend/src/styles.css`.
