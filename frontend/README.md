# Yomi — Frontend

React + TypeScript + Vite + Tailwind + Zustand + Framer Motion.

## Dev

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api/*` to the
Flask backend on `http://127.0.0.1:5001`. Make sure the backend is running.

## Build (for the demo)

```bash
npm run build
```

Output goes to `frontend/dist/`. The Flask app is configured to serve that
folder at `/` when present, so the whole app boots from a single port.

## Design tokens

The visual language is inspired by kodansha.us — editorial, mostly black and
white, with a single vermilion accent and serif headings.

- Colors: see `tailwind.config.js` (`ink`, `paper`, `vermilion`).
- Fonts: Inter (UI) + Noto Serif JP (Japanese + headings), loaded from
  Google Fonts in `index.html`.
