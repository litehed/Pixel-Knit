# Pixel Knit

A desktop app for designing knitting charts on a pixel grid and following them row by row.

## Requirements
 
- Windows 10 or newer, or macOS 13 (Ventura) or newer (These are the two operating systems I have tested on so it may be compatible with others)
- [uv](https://docs.astral.sh/uv/) to run from source

## Run from source
 
```bash
cd <project-folder>
uv sync
uv run pixel-knit
```

## Build a standalone app
 
Build on the system you want to run it on. The build tools are installed by `uv sync`.
 
```bash
uv run pyinstaller PixelKnit.spec --noconfirm
```

<ins>App Locations after building:</ins>

Windows: `dist/PixelKnit/PixelKnit.exe` 

macOS: `dist/PixelKnit.app` 

## Where your data lives
 
Charts are saved wherever you choose. Settings and autosave recovery files are kept in the app's data folder:
 
- Windows: `%APPDATA%\PixelKnit\PixelKnit`
- macOS: `~/Library/Application Support/PixelKnit/PixelKnit`