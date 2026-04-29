# TecnoApp UI Kit

High-fidelity recreation of the TecnoApp Windows desktop application in HTML/JSX.

## Structure

```
index.html          — Interactive click-through prototype (full app shell)
Tokens.jsx          — Shared design tokens (colors, spacing, typography)
Sidebar.jsx         — Sidebar navigation component
HomeScreen.jsx      — Home / dashboard screen
LimpezaScreen.jsx   — Limpeza (cleaning) module
GamerScreen.jsx     — Modo Gamer screen
SpecsScreen.jsx     — Especificações (hardware specs) screen
```

## Usage

Open `index.html` in a browser. Click the sidebar items to navigate between screens.

## Design Fidelity Notes

- Fonts: `Segoe UI` (Windows system font) with `Rajdhani` fallback via Google Fonts
- Monospace: `Consolas` with `Share Tech Mono` fallback
- Dot-grid background texture from `assets/bg_grid.png`
- All color tokens match `ui/widgets.py` Palette class exactly
- Window dimensions: 1100×720px (min 900×620px)
- Sidebar: 220px fixed
- Interactive: sidebar navigation, toggle switches, clean/gamer mode simulation
