# cursor-startup-beteiligungs-app

A startup **cap table / equity participation ("Beteiligung")** app. Add shareholders
with a number of shares and a share class, and see ownership percentages recalculated
in real time.

## Stack

- **Monorepo:** npm workspaces (`server`, `client`)
- **Server:** Express + TypeScript (REST API, in-memory cap table), tested with Vitest
- **Client:** React + Vite + TypeScript, tested with Vitest + Testing Library
- **Tooling:** ESLint (flat config) + TypeScript across the repo

## Prerequisites

- Node.js >= 20 (developed on Node 22)
- npm (comes with Node)

## Setup

```bash
npm install
```

## Develop

Run both the API and the web client with hot reload:

```bash
npm run dev
```

- Web client: http://localhost:5173
- API: http://localhost:4000 (the client proxies `/api` → `:4000`)

You can also run a single workspace:

```bash
npm run dev -w server
npm run dev -w client
```

## Lint / test / build

```bash
npm run lint     # eslint across the repo
npm run test     # vitest in server + client
npm run build    # tsc (server) + tsc & vite build (client)
```

## API

| Method | Path                       | Description                          |
| ------ | -------------------------- | ------------------------------------ |
| GET    | `/api/health`              | Health check                         |
| GET    | `/api/cap-table`           | Current cap table + ownership %      |
| POST   | `/api/shareholders`        | Add a shareholder `{name, shares, shareClass}` |
| DELETE | `/api/shareholders/:id`    | Remove a shareholder                 |

Data is stored **in memory** and seeded with two founders on startup, so it resets
whenever the server restarts. Swap `CapTable` for a real datastore when persistence
is needed.
