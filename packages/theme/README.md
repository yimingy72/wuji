# @wuji/theme public boundary

The package root is the only public module path. CORE fixes the palette IDs, shared token types, default palette and `isPaletteId` guard in `src/index.ts`.

The WEB batch migrates the single existing token source into this module and keeps these compatibility exports at the package root:

- `palettes: readonly WorkbenchPalette[]`
- `getPalette(id: PaletteId): WorkbenchPalette`
- `makeWorkbenchTheme(palette: WorkbenchPalette): ThemeConfig`

The migrated values must retain all five existing palettes. The prototype and formal app both import this package; they do not keep separate token copies.
