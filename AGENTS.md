# AGENTS.md

## Project overview

`cursor-startup-beteiligungs-app` is a startup cap table / equity participation app.
It is an npm-workspaces monorepo with two workspaces:

- `server/` — Express + TypeScript REST API. Cap-table logic lives in
  `server/src/capTable.ts`; the HTTP layer is in `server/src/app.ts`.
- `client/` — React + Vite + TypeScript web UI in `client/src/`.

Standard commands (lint/test/build/dev) are documented in `README.md` and defined in
the root and workspace `package.json` files. Prefer those instead of duplicating here.

## Cursor Cloud specific instructions

- Run everything with npm workspaces from the repo root. `npm install` at the root
  installs both workspaces; do not run installs inside `server/` or `client/`.
- `npm run dev` starts both services concurrently: the API on port `4000` and the Vite
  client on port `5173`. The client reaches the API through Vite's `/api` proxy
  (configured in `client/vite.config.ts`), so both must be running for the UI to load
  data. When testing the API through the browser origin, hit `http://localhost:5173/api/...`;
  hitting the API directly is `http://localhost:4000/api/...`.
- The cap table is stored **in memory** and re-seeded with two founders on every server
  restart. Any shareholders added at runtime are lost when the `server` process reloads
  (e.g. tsx watch restart). Don't rely on persisted state across restarts.
- Vitest must stay on a version that supports the installed Vite major (currently Vite 6
  → Vitest 3). If you bump Vite, keep Vitest aligned or the client `vite build` will fail
  with duplicate-`vite`-copy type errors from `vite.config.ts`. The client config imports
  `defineConfig` from `vitest/config` (not `vite`) so the `test` field type-checks.
