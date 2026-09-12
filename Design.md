# MergeMind — Design System & Theme Specifications

> **Design Language**: Dark Sci-Fi Neumorphism & Glassmorphism  
> **Brand Identity**: Precise, Developer-Native, AST-Aware, Verified & Autonomous  
> **Target Audience**: Software Engineers, DevOps, Open-Source Maintainers

---

## 1. Design Philosophy & Aesthetic Core

MergeMind is an AI-powered semantic merge driver that understands abstract syntax trees (ASTs) rather than treating code as raw strings. The visual language mirrors this technical identity:

1. **Dark Sci-Fi Neumorphism**: Instead of bright, flat surfaces, the interface utilizes deep obsidian, charcoal, and dark slate tones (`#07090e` to `#121722`) shaped by soft dual-tone lighting—subtle top-left highlights and deep bottom-right drop shadows.
2. **Deterministic & Verifiable Trust**: Clean typography, crisp borders, and dedicated status indicators (Docker green, Semgrep shield, amber conflict tags) convey safety, transparency, and deterministic verification.
3. **Cyberpunk & Ambient Glows**: Strategic cyan/sky light leaks (`#38bdf8` / `#7dd3fc`) illuminate primary actions, active states, and AI reasoning panels without overwhelming developer readability.
4. **Human-in-the-Loop Clarity**: 4-way diff layouts separate **BASE**, **LOCAL**, **REMOTE**, and **AI-MERGED** with distinct color-coding so engineers never have to guess who changed what.

---

## 2. Color Palette & Token System

### 2.1 Surface & Background Tokens

| Token Name | Hex / Value | Tailwind / CSS Class | Usage |
|---|---|---|---|
| **Canvas Background** | `#07090e` | `bg-[#07090e]` / `dark.bg` | Root HTML/body background canvas |
| **App Surface** | `#0e121a` | `bg-[#0e121a]` / `dark.surface` | Default panel and card surface |
| **Surface Raised** | `#121722` | `bg-[#121722]` / `dark.surfaceRaised` | Elevated floating cards, modals, popovers |
| **Surface Sunken** | `#090c13` | `bg-[#090c13]` / `dark.surfaceSunken` | Recessed containers, input wells, code blocks |
| **Surface Deep Recessed** | `#070a10` | `bg-[#070a10]` | Multi-panel code diff gutter and IDE editors |
| **Navbar Backdrop** | `#07090e` (70% opacity) | `bg-[#07090e]/70 backdrop-blur-md` | Floating glassmorphic header |

### 2.2 Brand & Accent Tokens

| Token Name | Hex / Value | CSS / Tailwind Class | Role |
|---|---|---|---|
| **Brand Primary Cyan** | `#38bdf8` | `text-sky-400` / `bg-sky-400` | Primary brand accent, active tabs, pulse nodes |
| **Brand Sky Blue** | `#7dd3fc` | `text-sky-300` / `bg-sky-300` | Highlights, badges, hero text gradients |
| **Brand Ice Blue** | `#bae6fd` | `text-sky-200` | Subtitle highlights, selected code states |
| **Brand Deep Gradient** | `#182338` ➔ `#111724` | `neu-glow-btn` | Primary CTA glowing gradient background |
| **Ambient Glow Alpha** | `rgba(56, 189, 248, 0.15)` | `brand.glow` | Ambient blurred backdrops and focus rings |

### 2.3 Semantic & Status Tokens

| Role | Color | Hex / Tailwind | Semantic Usage |
|---|---|---|---|
| **Verified / Success** | Emerald | `#34d399` (`emerald-400`), `emerald-500/10` | Docker sandbox passed, tests green, commit merged |
| **Conflict / Warning** | Amber | `#fbbf24` (`amber-400`), `amber-500/10` | Merge conflicts detected, AST ambiguity, warnings |
| **Error / Security Flag** | Rose | `#f43f5e` (`rose-400`), `rose-500/10` | Semgrep CVE detected, test assertion failure, rejected |
| **Base Branch** | Slate | `#94a3b8` (`slate-400`), `#0a0d15` | Common ancestor commit / base diff pane |
| **Local Branch** | Sky Cyan | `#38bdf8` (`sky-400`), `sky-950/20` | Our feature branch diff pane |
| **Remote Branch** | Purple / Violet | `#c084fc` (`purple-400`), `purple-950/20` | Incoming upstream / target branch diff pane |
| **AI Proposed Merge** | Cyan Star | `#7dd3fc` (`sky-300`), `ring-sky-400/30` | LangGraph proposed unified resolution |

### 2.4 Text & Monospace Tones

| Role | Hex | Tailwind Class | Contrast / Context |
|---|---|---|---|
| **Heading / Primary Text** | `#ffffff` / `#f8fafc` | `text-white` / `text-slate-50` | Main headlines, modal titles, active labels |
| **Body Text** | `#e2e8f0` | `text-slate-200` | Standard body copy, instructions |
| **Muted Text** | `#94a3b8` | `text-slate-400` | Descriptions, secondary metadata, subtext |
| **Dimmed Text** | `#64748b` | `text-slate-500` | Footers, disabled states, subtle metadata |
| **Code Default** | `#cbd5e1` | `text-slate-300 font-mono` | Syntax tokens, terminal strings |

---

## 3. Dark Neumorphism & Shadow Engine

Dark Neumorphism relies on precise light angles and low-opacity specular highlights. All shadows assume a light source positioned at **top-left (-X, -Y)**:

```css
/* Tailwind Config Box-Shadow Definitions */
boxShadow: {
  'neu-flat':      '5px 5px 12px rgba(0, 0, 0, 0.6), -3px -3px 8px rgba(255, 255, 255, 0.03)',
  'neu-raised':    '8px 8px 18px rgba(0, 0, 0, 0.7), -4px -4px 12px rgba(255, 255, 255, 0.04)',
  'neu-sunken':    'inset 4px 4px 8px rgba(0, 0, 0, 0.75), inset -2px -2px 6px rgba(255, 255, 255, 0.04)',
  'neu-sunken-sm': 'inset 2px 2px 5px rgba(0, 0, 0, 0.7), inset -1px -1px 3px rgba(255, 255, 255, 0.03)',
  'neu-button':    '4px 4px 10px rgba(0, 0, 0, 0.6), -2px -2px 6px rgba(255, 255, 255, 0.04)',
  'neu-glow':      '0 0 25px rgba(125, 211, 252, 0.22), 4px 4px 12px rgba(0, 0, 0, 0.6)'
}
```

### 3.1 CSS Utility Classes (`index.css`)

- **`.neu-panel`**: Standard container card. Base surface `#0e121a` with 1px border (`rgba(255,255,255,0.05)`).
- **`.neu-panel-hover`**: Interactive card. On hover: shifts up `translateY(-3px)`, darkens drop-shadow, highlights border to `rgba(125, 211, 252, 0.22)`.
- **`.neu-recessed`**: Inset wells for inputs, terminal views, icon enclosures, and badge wells.
- **`.neu-button`**: Standard interactive button with tactile click response (`:active` switches from drop shadow to sunken inset shadow).
- **`.neu-glow-btn`**: Hero CTA button with cyan radiance (`0 0 24px rgba(125, 211, 252, 0.18)`), subtle border, and lift on hover.
- **`.neu-nav-active`**: Sunken inset slot indicating current tab/section in the navigation pill.

---

## 4. Typography Hierarchy

MergeMind pairs **Inter** for clean UI readability with **JetBrains Mono** for all code, diffs, git hashes, and terminal logs.

```html
<!-- Google Fonts CDN -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

### 4.1 Type Scale

| Level | Size | Weight | Tracking / Leading | Font Family | Example |
|---|---|---|---|---|---|
| **Display / Hero** | `3.75rem - 5.75rem` (60–92px) | ExtraBold (800) | `tracking-tight leading-[1.05]` | Inter | Hero "MergeMind" title |
| **H1 Section Title** | `2.25rem - 3rem` (36–48px) | ExtraBold (800) | `tracking-tight leading-tight` | Inter | "Connect your GitHub", "You Stay in Control." |
| **H2 Feature Title** | `1.25rem - 1.5rem` (20–24px) | Bold (700) | `tracking-tight leading-snug` | Inter | Card titles, modal headers |
| **H3 Subhead** | `1.0rem - 1.125rem` (16–18px) | SemiBold (600) | `tracking-normal` | Inter | Sub-feature headers, panel titles |
| **Eyebrow Pill** | `0.75rem` (12px) | SemiBold (600) | `tracking-wider uppercase` | JetBrains Mono | `GET STARTED`, `AGENTIC AI • TOOLING` |
| **Body Large** | `1.125rem` (18px) | Regular (400) | `leading-relaxed` | Inter | Hero descriptions, intro paragraphs |
| **Body Normal** | `0.875rem - 1.0rem` (14–16px) | Regular (400) | `leading-relaxed` | Inter | Card descriptions, reasoning paragraphs |
| **Code / Diff Text** | `0.6875rem - 0.75rem` (11–12px) | Regular / Med (400/500) | `leading-relaxed font-mono` | JetBrains Mono | 4-way diff viewer, terminal emulator |
| **Micro Caption** | `0.6875rem` (11px) | Medium (500) | `tracking-wide font-mono` | JetBrains Mono | Footer copyright, metadata stamps |

---

## 5. Iconography & Brand Assets

### 5.1 Icon System
All icons utilize **`lucide-react`** with:
- Standard stroke width: `stroke-[1.8]` or `stroke-[2.0]`
- Sizing:
  - Micro icons (in buttons / badges): `w-3.5 h-3.5` or `w-4 h-4`
  - Feature card icons: `w-6 h-6`
  - Modal / Flow icons: `w-5 h-5`
- Treatment: Placed inside **circular recessed wells** (`neu-recessed rounded-full`) with a soft backdrop radial glow (`bg-sky-400/5 blur-sm`).

### 5.2 MergeMind Logo Geometry
The brand mark represents the intersection of code AST branches merging into an atomic neural knot:
- **Loop 1**: Ellipse rotated at `-28°` (`rx="14" ry="9"`) styled with gradient `url(#ringGrad1)` (`#e0f2fe` ➔ `#bae6fd` ➔ `#38bdf8`).
- **Loop 2**: Ellipse rotated at `+32°` (`rx="14" ry="9"`) styled with gradient `url(#ringGrad2)` (`#ffffff` ➔ `#7dd3fc`).
- **Nucleus**: Core glowing point (`cx="20" cy="20" r="1.5"`) with `drop-shadow-[0_0_6px_#38bdf8]`.

### 5.3 3D Particle Cloud Visual
- Rendered via HTML5 Canvas using vector particle physics.
- Features dynamic nodes interconnected by distance-threshold lines, responding subtly to mouse movement.
- Represents AST nodes and semantic relationships resolving in real time.

---

## 6. UI Components & Layout Patterns

### 6.1 Buttons
1. **Glow CTA Button (`neu-glow-btn`)**:
   - Background: `linear-gradient(135deg, #182338 0%, #111724 100%)`
   - Border: `1px solid rgba(125, 211, 252, 0.35)`
   - Hover: Border brightens to `rgba(186, 230, 253, 0.55)`, shadow radius expands to `32px`.
2. **Neumorphic Standard Button (`neu-button`)**:
   - Background: `#111622`
   - Border: `1px solid rgba(255, 255, 255, 0.06)`
   - Active: Sunken inset shadow `inset 2px 2px 5px rgba(0,0,0,0.7)`.
3. **Ghost / Action Pills**:
   - Small rounded-xl buttons for diff actions (`Accept`, `Edit`, `Reject`).

### 6.2 4-Way Diff Review Window
The centerpiece of the human-in-the-loop developer review:
- **Window Frame**: macOS-style traffic lights (Rose `#f43f5e`, Amber `#fbbf24`, Emerald `#10b981`), file name, and verification status badges (`Docker: 8/8 tests passed`, `Semgrep: 0 issues`).
- **4 Grid Columns**:
  1. `BASE (Ancestor)`: Slate muted background, shows common ancestor code.
  2. `LOCAL (Our Branch)`: Subtle cyan-tinted background (`bg-sky-950/10`), shows local feature changes.
  3. `REMOTE (Their Branch)`: Subtle purple-tinted background (`bg-purple-950/10`), shows remote incoming changes.
  4. `AI-MERGED (Hero Proposal)`: Elevated with `ring-1 ring-sky-400/30`, badge `Verified`, shows resolved code.
- **Reasoning Bar**: Bottom drawer displaying LangGraph Merge Agent reasoning in natural developer terminology.

### 6.3 Badges & Status Pills
- **Pulse Badge**: Small dot with `animate-pulse` (`bg-sky-400`, `bg-emerald-400`, or `bg-amber-400`) coupled with uppercase monospace label.
- **Verification Tag**: Pill with `bg-emerald-500/10 border-emerald-500/20 text-emerald-400` with `CheckCircle2` icon.

---

## 7. Motion & Interaction Standards

| Interaction | Duration | Easing | Style |
|---|---|---|---|
| **Hover Elevation** | `300ms` | `cubic-bezier(0.16, 1, 0.3, 1)` | `translateY(-2px to -3px)` + shadow expansion |
| **Button Click / Active** | `150ms` | `ease-out` | Shadow flips from drop-shadow to inset sunken |
| **Modal Entry** | `200ms` | `ease-out` | `fade-in`, background blur `backdrop-blur-md` |
| **Ambient Glow Pulse** | `2000ms - 3000ms` | `ease-in-out infinite` | Opacity oscillation between `0.6` and `1.0` |
| **Smooth Navigation Scroll** | `850ms` lock | `smooth` | Offset -80px to accommodate floating navbar |

---

## 8. Frontend Engineering Rules

1. **Dark Mode Only**: MergeMind does not use a bright/light theme; all layouts default to `color-scheme: dark`.
2. **Deterministic Layouts**: Prevent layout shifts during code preview or terminal loading by using min-heights (`min-h-[190px]`, etc.).
3. **No Raw Provider Branding**: Model and provider references in UI should focus on local privacy, AST verification, and autonomous sandboxes.
4. **Accessible Contrast**: Ensure all code diffs maintain at least WCAG AA contrast ratio against their sunken container backgrounds.
