import {
  createContext,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { App, ConfigProvider } from 'antd';
import {
  defaultPaletteId,
  getPalette,
  isPaletteId,
  makeWorkbenchTheme,
  type PaletteId,
} from '@wuji/theme';
import { useLocation, useNavigate } from 'react-router-dom';

const preferenceKey = 'wuji.workbench.palette';

interface AppearanceValue {
  readonly paletteId: PaletteId;
  choosePalette(id: PaletteId): void;
}

interface PaletteSelection {
  readonly id: PaletteId;
  readonly sourceSearch: string | null;
}

const AppearanceContext = createContext<AppearanceValue | null>(null);

function readStoredPalette(): PaletteId {
  try {
    const saved = localStorage.getItem(preferenceKey);
    if (isPaletteId(saved)) return saved;
  } catch {
    // The preference is optional; a blocked storage area must not block the app.
  }
  return defaultPaletteId;
}

function initialSelection(): PaletteSelection {
  const requested = new URLSearchParams(window.location.search).get('theme');
  if (isPaletteId(requested)) return { id: requested, sourceSearch: window.location.search };
  return { id: readStoredPalette(), sourceSearch: null };
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [selection, setSelection] = useState<PaletteSelection>(initialSelection);
  const requested = new URLSearchParams(location.search).get('theme');

  useLayoutEffect(() => {
    if (isPaletteId(requested) && selection.sourceSearch !== location.search) {
      setSelection({ id: requested, sourceSearch: location.search });
    } else if (!isPaletteId(requested) && selection.sourceSearch !== null) {
      setSelection((current) => ({ ...current, sourceSearch: null }));
    }
  }, [location.search, requested, selection.sourceSearch]);

  const palette = getPalette(selection.id);
  const config = useMemo(() => makeWorkbenchTheme(palette), [palette]);

  useLayoutEffect(() => {
    const root = document.documentElement;
    root.dataset.palette = palette.id;
    root.style.colorScheme = palette.mode;
    for (const [name, value] of Object.entries(palette.colors)) {
      root.style.setProperty(`--${name}`, value);
    }
    document.title = `Wuji · ${palette.name}`;
  }, [palette]);

  const value = useMemo<AppearanceValue>(() => ({
    paletteId: palette.id,
    choosePalette(id) {
      // Mark the current URL override as handled until Router commits its removal.
      setSelection({ id, sourceSearch: location.search });
      try {
        localStorage.setItem(preferenceKey, id);
      } catch {
        // The in-memory selection remains usable when persistence is unavailable.
      }

      const search = new URLSearchParams(location.search);
      if (search.has('theme')) {
        search.delete('theme');
        navigate(
          { pathname: location.pathname, search: search.toString(), hash: location.hash },
          { replace: true, defaultShouldRevalidate: false },
        );
      }
    },
  }), [location.hash, location.pathname, location.search, navigate, palette.id]);

  return (
    <AppearanceContext.Provider value={value}>
      <ConfigProvider theme={config}>
        <App className="wuji-antd-app">{children}</App>
      </ConfigProvider>
    </AppearanceContext.Provider>
  );
}

export function useAppearance(): AppearanceValue {
  const context = useContext(AppearanceContext);
  if (!context) throw new Error('AppearanceProvider is missing');
  return context;
}
