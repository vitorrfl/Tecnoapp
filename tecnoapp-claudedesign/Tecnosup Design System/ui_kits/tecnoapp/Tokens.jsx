// Tecnosup Design Tokens — shared across all UI kit components
// Must be loaded before any other component

const T = {
  // Colors
  bgBase:        '#030407',
  bgCard:        '#0a0d14',
  bgCardHover:   '#0d1220',
  borderSubtle:  '#1a2230',
  cyan:          '#0eb3ff',
  purple:        '#7000ff',
  stateOn:       '#4caf50',
  stateWarn:     '#ffbd2e',
  stateOff:      '#888888',
  stateDanger:   '#ff4b4b',
  fgPrimary:     '#ffffff',
  fgBody:        '#ccd2e0',
  fgMuted:       '#888888',
  fgSubtle:      '#444444',

  // Fonts
  fontBody: "'Segoe UI', 'Rajdhani', system-ui, sans-serif",
  fontMono: "'Consolas', 'Share Tech Mono', monospace",

  // Radii
  radiusCard:   12,
  radiusBtn:    8,
  radiusPill:   50,
  radiusSm:     4,
  radiusMd:     6,

  // Spacing
  cardPad:  20,
  cardGap:  12,
  screenH:  24,
  screenV:  32,
};

// Reusable styled-object helpers
const TS = {
  card: {
    background: '#0a0d14',
    border: '1px solid #1a2230',
    borderRadius: 12,
    padding: 20,
  },
  sectionLabel: {
    color: '#0eb3ff',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  bodyText: {
    color: '#888',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    fontSize: 11,
    lineHeight: 1.6,
  },
  monoText: {
    fontFamily: "'Consolas', 'Share Tech Mono', monospace",
    color: '#888',
    fontSize: 11,
  },
  btnPrimary: {
    background: '#0eb3ff',
    color: '#000',
    fontWeight: 700,
    border: 'none',
    borderRadius: 8,
    padding: '10px 0',
    fontSize: 14,
    cursor: 'pointer',
    width: '100%',
    boxShadow: '0 0 14px rgba(14,179,255,0.4)',
  },
};

// Lucide icon component — uses the UMD bundle loaded in index.html
function Icon({ name, size = 16, color = 'currentColor', strokeWidth = 1.5, style = {} }) {
  if (!window.lucide || !window.lucide[name]) {
    return <span style={{ width: size, height: size, display: 'inline-block', ...style }} />;
  }
  const iconDef = window.lucide[name];
  // lucide UMD format: [tagName, defaultAttrs, childrenArray]
  const children = iconDef[2] || [];
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: 'inline-block', flexShrink: 0, ...style }}
    >
      {children.map(([tag, attrs], i) => React.createElement(tag, { key: i, ...attrs }))}
    </svg>
  );
}

Object.assign(window, { T, TS, Icon });
