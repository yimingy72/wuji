import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { defaultPaletteId } from '@wuji/theme';

function PlatformShell() {
  return (
    <main>
      <h1>Wuji</h1>
      <p>平台工作台</p>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PlatformShell />
  </StrictMode>,
);

document.documentElement.dataset.palette = defaultPaletteId;
