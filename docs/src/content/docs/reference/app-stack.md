---
title: Custom App Stack
description: The frozen frontend and backend stack for the custom web apps (Offers, Jobs) and the Python apps, the files that must stay the same in each app, and how to upgrade the stack.
keywords:
  - react tanstack shadcn stack
  - fastapi sqlite web app
  - frozen dependency versions
---

All custom apps use one stack. The script `scripts/check-app-stack.py` checks the stack in pre-commit and in the CI `pre-commit` job. A commit that makes two apps different fails.

## Web Apps

The web apps are `apps/offers/` and `apps/jobs/`. Each app has a Python backend that serves a JSON API under `/api` and the built single-page app from `src/<app>/web_dist/`.

### Frontend

| Part | Package | Version |
| --- | --- | --- |
| UI framework | `react`, `react-dom` | 19.3.1 |
| Routing | `@tanstack/react-router`, `@tanstack/router-plugin` (file routes, code splitting) | 1.170.46, 1.168.48 |
| Server state | `@tanstack/react-query` | 5.106.1 |
| Tables (Jobs only) | `@tanstack/react-table` | 9.3.1 |
| Components | shadcn/ui 4.23.0 (`new-york` style) on `radix-ui`, from the shared library `packages/web-ui` | 1.8.1 |
| Styles | `tailwindcss`, `@tailwindcss/vite`, `tw-animate-css` | 4.3.4, 4.3.4, 1.4.0 |
| Class helpers | `class-variance-authority`, `clsx`, `tailwind-merge` | 0.7.1, 2.1.1, 3.7.0 |
| Icons | `lucide-react` | 1.69.0 |
| Toasts | `sonner` | 2.0.8 |
| Build | `vite`, `@vitejs/plugin-react` | 8.3.6, 6.2.1 |
| Type check | `typescript` (`tsc -b` after `vite build`) | 7.0.2 |
| Package manager | Bun (`bun.lock`), `oven/bun:1.4.4` in the Dockerfile | 1.4.4 |

### Backend

| Part | Choice |
| --- | --- |
| Language | Python 3.12 (`requires-python = ">=3.12"`) |
| Web framework | FastAPI with `uvicorn[standard]`, GZip middleware, and cache headers (`/assets/` immutable, `/api` no-store) |
| Settings | `pydantic-settings`, with an `<APP>_` prefix for the variables of the app |
| Storage | SQLite in WAL mode on a `local-path` PVC at `/data` |
| AI | `homelab-ai` (`packages/homelab-ai`), with structured output through `AITask` |
| Package manager | uv, with `uv.lock` |
| Lint, format, types, tests | `ruff`, `ty`, `pytest` |
| Image | The multi-stage Dockerfile of `apps/offers/Dockerfile`: Bun builds the frontend, uv installs the backend, and the image runs as user 10001 |

### Shared UI Library

`packages/web-ui/src` is the only source of the UI components, the theme, and the shared controls:

| File | Contents |
| --- | --- |
| `components/ui/*.tsx` | shadcn/ui components: button, card, popover, progress, skeleton, sonner, tooltip |
| `components/search.tsx` | Search box and filter chips |
| `index.css` | Tailwind 4 theme tokens for light and dark mode |
| `lib/utils.ts` | `cn` helper |

Each web app has a copy of these files at the same paths under `web/src`. To change one, change it in `packages/web-ui`, then run `python3 scripts/sync-web-ui.py`. An app cannot have a ui component that is not in the library. Put app-only components in `web/src/components/` (not in `ui/`). `packages/web-ui/README.md` tells how to add a shadcn/ui component.

### Files That Must Be the Same

`web/tsconfig.json` and `web/components.json` are identical in all web apps. `web/vite.config.ts` and `Dockerfile` are identical after the script replaces the app name.

### Page Conventions

- Layout: a header with the app name and the sync time, a top navigation on wide screens, and a bottom navigation on phones. Tables become card lists below 768 px.
- Data: one query key for each API resource. A mutation updates the cache, then shows a `sonner` toast.
- Filters and search: put them in the URL search parameters, so that a filtered view can be shared or bookmarked.
- Personal data: tailnet-only HTTPRoute, `robots.txt` with `Disallow: /`, and `X-Robots-Tag: noindex`.

## Python Apps

The Python apps without a web frontend (`actual-classifier`, `alert-summarizer`, `drive-organizer`, `gmail-classifier`) use the backend stack above, without the web parts. A package that two projects lock has the same version in all `uv.lock` files.

## Upgrade the Stack

Upgrade all apps in one change. Do not upgrade one app alone.

Step 1: Find the latest stable version of each package.

Step 2: For the frontend, change the version in each `apps/*/web/package.json`, then run `bun install` in each `web/` folder.

Step 3: For Python, run `uv lock --upgrade` in each project in `apps/` and `packages/`.

Step 4: Set the `rev` of `ruff-pre-commit` in `.pre-commit-config.yaml` to the locked `ruff` version.

Step 5: Run the checks in each project:

```bash
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
bun run build
python3 scripts/check-app-stack.py
```

Step 6: Update the version tables on this page.

## Add a Web App

Step 1: Copy `apps/offers/` without its `src/offers/` code, `tests/`, and `catalog.yaml`.

Step 2: Run `python3 scripts/sync-web-ui.py` to copy the shared UI library into the app. Keep the shared files above unchanged.

Step 3: Run `python3 scripts/check-app-stack.py`. It must pass before you commit.
