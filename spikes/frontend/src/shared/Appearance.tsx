import { createContext, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from 'react';
import { ConfigProvider } from 'antd';
import { getPalette, isPaletteId, makeWorkbenchTheme, type PaletteId } from '@wuji/theme';

const preferenceKey = 'wuji.workbench.palette';
const AppearanceContext = createContext<{ paletteId: PaletteId; setPaletteId: (id: PaletteId) => void } | null>(null);

function initialPalette(): PaletteId {
  const requested = new URLSearchParams(window.location.search).get('theme');
  if (isPaletteId(requested)) return requested;
  try {
    const saved = sessionStorage.getItem(preferenceKey);
    if (isPaletteId(saved)) return saved;
  } catch { /* A blocked storage area must not prevent the workbench from loading. */ }
  return 'silver';
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [paletteId, setPaletteId] = useState<PaletteId>(initialPalette);
  const palette = getPalette(paletteId);
  const config = useMemo(() => makeWorkbenchTheme(palette), [palette]);
  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.palette = palette.id;
    root.style.colorScheme = palette.mode;
    for (const [name, value] of Object.entries(palette.colors)) root.style.setProperty(`--${name}`, value);
    document.title = `Wuji · 本地工作台 · ${palette.name}`;
    // Per-tab preference keeps simultaneously opened comparison versions independent.
    try { sessionStorage.setItem(preferenceKey, palette.id); } catch { /* Optional preference storage. */ }
  }, [palette]);
  return <AppearanceContext.Provider value={{ paletteId, setPaletteId }}><ConfigProvider theme={config}>{children}</ConfigProvider></AppearanceContext.Provider>;
}

export function useAppearance() {
  const context = useContext(AppearanceContext);
  if (!context) throw new Error('AppearanceProvider is missing');
  return context;
}
