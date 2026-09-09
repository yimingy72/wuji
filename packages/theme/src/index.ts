import type { ThemeConfig } from 'antd';

export const paletteIds = ['silver', 'glacier', 'celadon', 'slate', 'graphite'] as const;
export type PaletteId = (typeof paletteIds)[number];
export const defaultPaletteId: PaletteId = 'silver';

export type PaletteMode = 'light' | 'dark';

export interface PaletteColors {
  readonly canvas: string;
  readonly surface: string;
  readonly raised: string;
  readonly rail: string;
  readonly queue: string;
  readonly node: string;
  readonly line: string;
  readonly border: string;
  readonly text: string;
  readonly muted: string;
  readonly placeholder: string;
  readonly accent: string;
  readonly 'accent-hover': string;
  readonly primary: string;
  readonly 'on-primary': string;
  readonly selected: string;
  readonly 'selected-hover': string;
  readonly 'selected-border': string;
  readonly success: string;
  readonly 'success-bg': string;
  readonly 'success-border': string;
  readonly warning: string;
  readonly 'warning-bg': string;
  readonly 'warning-border': string;
  readonly error: string;
  readonly 'code-text': string;
  readonly 'code-bg': string;
}

export interface WorkbenchPalette {
  readonly id: PaletteId;
  readonly name: string;
  readonly mode: PaletteMode;
  readonly colors: PaletteColors;
}

export interface WorkbenchTheme {
  readonly palette: WorkbenchPalette;
  readonly antd: ThemeConfig;
}

export interface WorkbenchThemeModule {
  readonly palettes: readonly WorkbenchPalette[];
  getPalette(id: PaletteId): WorkbenchPalette;
  makeWorkbenchTheme(palette: WorkbenchPalette): ThemeConfig;
}

export function isPaletteId(value: unknown): value is PaletteId {
  return typeof value === 'string' && (paletteIds as readonly string[]).includes(value);
}
