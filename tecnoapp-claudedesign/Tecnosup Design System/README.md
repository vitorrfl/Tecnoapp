# Tecnosup Design System

## Product Overview

**Tecnosup · Soluções Digitais** is a Brazilian Windows desktop optimization app — **TecnoApp** — built with Python 3.11+ and PySide6 (Qt6). It targets Windows 10/11 users (Portuguese-speaking) who want a single, trustworthy tool to clean junk, optimize performance, repair system issues, and boost gaming.

The product is a single executable desktop app (1100×720px, min 900×620px). Its visual identity is **dark neon cyber** — near-black backgrounds, cyan and purple neon accents, monospace terminal readouts, and glowing UI elements.

### Modules / Features
- **Limpeza** — Safe junk cleaning (temp files, DNS cache, recycle bin, etc.)
- **Otimização** — Persistent system tweaks (power plan, disk, telemetry)
- **Reparos** — Windows repair tools (SFC/DISM, network reset, Windows Update, Store, printer)
- **Especificações** — Live hardware metrics dashboard (CPU, RAM, disks, processes)
- **Modo Gamer** — 17 reversible performance tweaks across CPU, GPU, system and network

### Sources
- **GitHub repo**: https://github.com/vitorrfl/Tecnoapp (branch `main`)
- **Local codebase**: `app/` (mounted via File System Access API — same content)
  - `app/app3.py` — Main app, all screens and widgets (3356 lines)
  - `app/ui/widgets.py` — Design token classes (Palette, Spacing) + reusable Qt components
  - `app/gamer/` — Gamer mode engine and 17 tweaks
  - `app/assets/logo.png` — Brand logo

---

## Content Fundamentals

### Language & Tone
- All copy is **Brazilian Portuguese**. No English in user-facing strings.
- Tone is **direct, technical, and confident** — not marketing-fluffy.
- The product talks *to* the user plainly: "Limpeza segura com ferramentas nativas do Windows"
- Module labels are **ALL CAPS**: LIMPEZA, OTIMIZAÇÃO, REPAROS, MODO GAMER
- Section headers use the pattern `── SAFE (always recommended)` with em-dashes
- Status bar uses a terminal-style `> ` prefix: `> Última limpeza: 28/04/2026 às 14:32 — ✓ 2.1 GB liberados`
- Numeric metric labels show the number large, unit small and muted: `48.2 GB`
- Warnings use `⚠ ` prefix inline in body text
- Version strings use middle dot: `v 1.0 · Tecnosup`

### Casing Conventions
- Navigation labels: UPPERCASE (`LIMPEZA`, `MODO GAMER`)
- Body descriptions: Sentence case
- Chip labels: Title case with lowercase description
- Buttons: UPPERCASE for primary CTAs, title case for secondary

### Emoji Usage
- **Minimal.** Only `⚠` and `✓` appear as functional indicators in the terminal log
- No decorative emoji anywhere in the UI
- Unicode `·` (middle dot) used as separator

### Examples
- `"Limpeza segura com ferramentas nativas do Windows"` — module subtitle
- `"Não é possível recuperar arquivos após esvaziar."` — warning copy, direct
- `"INICIAR LIMPEZA"` — primary CTA, uppercase, no punctuation
- `"Configurar o que é limpo →"` — secondary CTA, title case, arrow suffix

---

## Visual Foundations

### Colors
| Token | Hex | Usage |
|---|---|---|
| BG_BASE | `#030407` | App background, main canvas |
| BG_CARD | `#0a0d14` | Card backgrounds |
| BG_CARD_HOVER | `#0d1220` | Card hover state |
| BORDER_SUBTLE | `#1a2230` | Card borders |
| ACCENT_CYAN | `#0eb3ff` | Primary accent — Limpeza, Otimização, Reparos, buttons |
| ACCENT_PURPLE | `#7000ff` | Modo Gamer accent, gradient pair |
| STATE_ON | `#4caf50` | Active / applied state |
| STATE_WARN | `#ffbd2e` | Warning state, optional settings |
| STATE_OFF | `#888888` | Inactive state |
| STATE_DANGER | `#ff4b4b` | Destructive/danger actions |
| FG_PRIMARY | `#ffffff` | Headlines, primary text |
| FG_BODY | `#ccd2e0` | Body text |
| FG_MUTED | `#888888` | Muted/secondary text |
| FG_SUBTLE | `#444444` | De-emphasized text, decorators |

### Typography
- **Primary font**: Segoe UI (Windows system font — Bold for titles, regular for body)
- **Monospace font**: Consolas (metrics, terminal readouts, status bar, file paths)
- **Icon font**: Segoe MDL2 Assets / Segoe Fluent Icons (Windows built-in glyph font)
- Title size: 22px Bold
- Section label: 11px Bold, letter-spacing 1px, UPPERCASE, ACCENT_CYAN
- Body text: 12px Regular, FG_MUTED
- Monospace readouts: 12px Consolas, FG_BODY
- Metric display: 32px Bold (MetricLabel), with 14pt muted unit
- Status bar: 9px Consolas

### Backgrounds
- Base background is near-black `#030407`
- A **dot-grid PNG** (`assets/bg_grid.png`) overlays the content area for subtle texture
- No full-bleed photography; no gradients on backgrounds
- Sidebar has `rgba(3, 4, 7, 245)` with `rgba(14, 179, 255, 0.1)` right border

### Layout & Spacing
- Sidebar: fixed 220px, content area fills remaining
- Content padding: 32px horizontal, 24px vertical
- Card padding: 20px uniform (CARD_PADDING)
- Card border-radius: 12px
- Button border-radius: 8px
- Progress bars: 4px radius, 8px height
- Chip height: 24px, radius 12px (fully rounded pill)
- Section spacing: 14px between cards, 12px within cards

### Cards
- Background: `#0a0d14`
- Border: 1px solid `#1a2230`
- Border-radius: 12px
- HeroCard: same as Card + 3px colored stripe at top (rounded on top corners)
- No drop shadows on regular cards
- Hover state: BG_CARD_HOVER (`#0d1220`)

### Buttons
- **Primary (ActionBtn)**: bg `#0eb3ff`, text black, bold, hover → white
- **Menu (MenuBtn)**: transparent bg, border `rgba(14,179,255,0.25)`, hover → cyan bg tint + cyan border + cyan text
- **Gamer Nav**: gradient left→right cyan→purple, white text
- **Exit (ExitBtn)**: transparent, red border + text, hover → solid red
- **Secondary (link-style)**: transparent bg, cyan border, cyan text, small

### Neon Glow
Buttons and key labels use a `QGraphicsDropShadowEffect` neon glow:
- Cyan glow: blur 16px, color `#0eb3ff`, offset (0,0)
- Purple glow: blur 16px, color `#7000ff`, offset (0,0)

### Animations & Motion
- No CSS transitions or entrance animations
- Toggle switch uses `paintEvent` for smooth on/off (custom drawn)
- Dot-animation for loading states: cycling `·`, `··`, `···` every 180ms via QTimer
- No bounces, springs, or easing — functional feedback only

### Toggle Switch
Custom-drawn pill toggle:
- Off: bg `#1a1f2b`, border `#333333`, knob `#888888`
- On: bg `#0eb3ff`, border `#0eb3ff`, knob white
- Size: 46×22px, knob 16×16px

### Scrollbars
- Width: 6px
- Track: `#111`
- Handle: `#0eb3ff`
- Border-radius: 3px

### Corner Radii Summary
| Element | Radius |
|---|---|
| Cards / HeroCards | 12px |
| Buttons | 8px |
| Chips / Pills | 12px (fully rounded) |
| Progress bars | 4px |
| Scroll handles | 3px |
| Clean item rows | 6px |

---

## Iconography

The app uses **Segoe MDL2 Assets** and **Segoe Fluent Icons** (Windows built-in glyph fonts) for all navigation and action icons. These are rendered via Qt's `_menu_icon()` helper which draws the Unicode glyph onto a QPixmap at the specified color.

- Icons are **single-color glyphs** matching the text color (white by default, cyan on active/hover)
- No standalone SVG icon files are used
- No PNG icon sheets
- No third-party icon libraries (Lucide, Material, etc.)
- Since Segoe MDL2/Fluent is Windows-only, web equivalents should use a CDN-hosted icon set with matching stroke style (e.g. Lucide Icons — thin stroke, outlined)

The logo (`assets/logo.png`) is the only image asset in the brand:
- Bold all-caps "TECNOSUP" wordmark in white with cyan neon glow halo
- "SOLUÇÕES DIGITAIS" subtitle in cyan, tracked wide
- Used in sidebar at 180px wide, centered

---

## File Index

```
README.md                       — This file
SKILL.md                        — Agent skill descriptor
colors_and_type.css             — CSS design tokens (colors, type, spacing)
assets/
  logo.png                      — Tecnosup wordmark + tagline
  bg_grid.png                   — Dot grid background texture
preview/
  colors-base.html              — Base color palette swatches
  colors-semantic.html          — Semantic/state color swatches
  type-scale.html               — Typography scale specimens
  type-mono.html                — Monospace / terminal type
  spacing-tokens.html           — Spacing, radius, border tokens
  components-buttons.html       — Button variants
  components-cards.html         — Card and HeroCard specimens
  components-chips.html         — Chip / badge states
  components-toggle.html        — Toggle switch + progress bar
  components-sidebar.html       — Sidebar navigation specimen
  brand-logo.html               — Logo presentation
ui_kits/
  tecnoapp/
    README.md                   — UI kit overview
    index.html                  — Interactive TecnoApp prototype
    Layout.jsx                  — App shell (sidebar + content area)
    Sidebar.jsx                 — Sidebar navigation
    HomeScreen.jsx              — Dashboard screen
    LimpezaScreen.jsx           — Clean module screen
    GamerScreen.jsx             — Gamer mode screen
    SpecsScreen.jsx             — Hardware specs screen
    Tokens.jsx                  — Shared design tokens
```
