import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

const oklch = (lightness: number, chroma: number, hue: number) => `oklch(${lightness} ${chroma} ${hue})`;

const graphiteColors = {
  canvas: oklch(.16, .009, 250), surface: oklch(.195, .011, 250), raised: oklch(.235, .013, 250),
  rail: oklch(.145, .009, 250), queue: oklch(.18, .01, 250), node: oklch(.205, .012, 250),
  line: oklch(.29, .013, 250), border: oklch(.54, .018, 250),
  text: oklch(.94, .006, 250), muted: oklch(.76, .014, 250), placeholder: oklch(.72, .015, 250),
  accent: oklch(.78, .115, 210), 'accent-hover': oklch(.89, .07, 210), primary: oklch(.73, .13, 210), 'on-primary': oklch(.16, .009, 250),
  selected: oklch(.225, .025, 220), 'selected-hover': oklch(.25, .032, 220), 'selected-border': oklch(.43, .055, 220),
  success: oklch(.8, .11, 165), 'success-bg': oklch(.25, .025, 165), 'success-border': oklch(.36, .03, 165),
  warning: oklch(.84, .095, 80), 'warning-bg': oklch(.26, .028, 80), 'warning-border': oklch(.39, .04, 80),
  error: oklch(.78, .12, 25), 'code-text': oklch(.83, .016, 250), 'code-bg': oklch(.17, .009, 250),
};

type PaletteColors = typeof graphiteColors;
export type PaletteId = 'silver' | 'glacier' | 'celadon' | 'slate' | 'graphite';
type Palette = { id: PaletteId; name: string; mode: 'light' | 'dark'; colors: PaletteColors };

function lightPalette(id: PaletteId, name: string, hue: number, canvasLightness: number, tint: number, accentChroma: number): Palette {
  return {
    id, name, mode: 'light', colors: {
      canvas: oklch(canvasLightness, tint, hue), surface: oklch(.995, .002, hue), raised: oklch(1, 0, hue),
      rail: oklch(canvasLightness - .035, tint * 1.5, hue), queue: oklch(.975, tint * .55, hue), node: oklch(.982, tint * .45, hue),
      line: oklch(.85, .018, hue), border: oklch(.64, .025, hue),
      text: oklch(.265, .024, hue), muted: oklch(.43, .025, hue), placeholder: oklch(.46, .024, hue),
      accent: oklch(.46, accentChroma, hue), 'accent-hover': oklch(.37, accentChroma, hue), primary: oklch(.46, accentChroma, hue), 'on-primary': oklch(1, 0, hue),
      selected: oklch(.935, .026, hue), 'selected-hover': oklch(.905, .038, hue), 'selected-border': oklch(.67, .075, hue),
      success: oklch(.43, .09, 165), 'success-bg': oklch(.957, .019, 165), 'success-border': oklch(.79, .04, 165),
      warning: oklch(.46, .09, 65), 'warning-bg': oklch(.964, .034, 85), 'warning-border': oklch(.77, .065, 80),
      error: oklch(.47, .16, 25), 'code-text': oklch(.34, .025, hue), 'code-bg': oklch(canvasLightness + .01, tint * .8, hue),
    },
  };
}

export const palettes: readonly Palette[] = [
  lightPalette('silver', '雾银', 230, .965, .006, .1),
  lightPalette('glacier', '冰蓝', 255, .93, .025, .17),
  lightPalette('celadon', '青瓷', 180, .95, .022, .085),
  {
    id: 'slate', name: '亮石墨', mode: 'dark', colors: {
      canvas: oklch(.285, .022, 250), surface: oklch(.335, .024, 250), raised: oklch(.39, .024, 250),
      rail: oklch(.26, .025, 250), queue: oklch(.31, .023, 250), node: oklch(.355, .024, 250),
      line: oklch(.47, .025, 250), border: oklch(.68, .025, 250),
      text: oklch(.98, .003, 250), muted: oklch(.85, .018, 250), placeholder: oklch(.84, .016, 250),
      accent: oklch(.86, .095, 215), 'accent-hover': oklch(.94, .055, 215), primary: oklch(.86, .095, 215), 'on-primary': oklch(.22, .025, 250),
      selected: oklch(.375, .049, 230), 'selected-hover': oklch(.405, .05, 230), 'selected-border': oklch(.64, .07, 230),
      success: oklch(.86, .095, 165), 'success-bg': oklch(.37, .035, 165), 'success-border': oklch(.56, .055, 165),
      warning: oklch(.9, .09, 80), 'warning-bg': oklch(.37, .035, 80), 'warning-border': oklch(.61, .065, 80),
      error: oklch(.87, .09, 25), 'code-text': oklch(.9, .014, 250), 'code-bg': oklch(.3, .022, 250),
    },
  },
  { id: 'graphite', name: '原石墨', mode: 'dark', colors: graphiteColors },
];

export function isPaletteId(value: unknown): value is PaletteId {
  return typeof value === 'string' && palettes.some(palette => palette.id === value);
}

export function getPalette(id: PaletteId) {
  return palettes.find(palette => palette.id === id)!;
}

// Ant Design's palette generator accepts sRGB; keep OKLCH as the design source.
function antdColor(value: string): string {
  const context = document.createElement('canvas').getContext('2d');
  if (!context || !CSS.supports('color', value)) throw new Error('Browser does not support the prototype color model');
  context.fillStyle = value;
  context.fillRect(0, 0, 1, 1);
  const pixel = context.getImageData(0, 0, 1, 1).data;
  return `rgb(${pixel[0]}, ${pixel[1]}, ${pixel[2]})`;
}

export function makeWorkbenchTheme(palette: Palette): ThemeConfig {
  const c = palette.colors;
  return {
    algorithm: palette.mode === 'light' ? theme.defaultAlgorithm : theme.darkAlgorithm,
    token: {
      colorPrimary: antdColor(c.primary), colorInfo: antdColor(c.primary),
      colorSuccess: antdColor(c.success), colorWarning: antdColor(c.warning), colorError: antdColor(c.error),
      colorBgBase: antdColor(c.canvas), colorBgContainer: antdColor(c.surface), colorBgElevated: antdColor(c.raised),
      colorText: antdColor(c.text), colorTextSecondary: antdColor(c.muted), colorTextTertiary: antdColor(c.muted),
      colorTextPlaceholder: antdColor(c.placeholder), colorBorder: antdColor(c.border), colorBorderSecondary: antdColor(c.line),
      colorLink: antdColor(c.accent), colorLinkHover: antdColor(c['accent-hover']),
      controlHeight: 34, fontSize: 13, borderRadius: 5,
      fontFamily: '"Inter Variable", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif',
      fontFamilyCode: '"IBM Plex Mono", "SFMono-Regular", Consolas, monospace',
    },
    components: {
      Button: { primaryColor: antdColor(c['on-primary']), primaryShadow: 'none', defaultShadow: 'none', dangerShadow: 'none' },
      Tabs: { horizontalMargin: '0 0 18px 0', titleFontSize: 13, horizontalItemGutter: 24, itemSelectedColor: antdColor(c.accent), itemHoverColor: antdColor(c['accent-hover']), inkBarColor: antdColor(c.accent) },
      Input: { activeShadow: 'none' },
    },
  };
}
