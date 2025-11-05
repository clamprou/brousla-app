AI Desktop MVP (Electron + React + Python FastAPI)

Quickstart

1) Install Node 18+ and Python 3.10+
2) Install FFMPEG (required for multi-clip video concatenation):
   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg` or `sudo yum install ffmpeg`
3) Install dependencies:

```
npm install
```

3) Development (runs renderer, Electron, and Python backend):

```
npm run dev
```

4) Build installers for Win/Mac/Linux:

```
npm run build
```

Structure

- `electron/`: Electron main and preload
- `src/`: React renderer (Vite)
- `server/`: Python FastAPI backend
- `models/`: Model configs/placeholders for ComfyUI
- `assets/`: Static assets

Notes

- Settings are stored in `server/data/preferences.json`.
- History is stored in `server/data/history.json`.
- Extend workflows in `server/workflows/` and React `src/workflows/`.