# web-ui

The shared UI library of the custom web apps (`apps/offers/web`, `apps/jobs/web`). It holds the shadcn/ui components, the theme (`index.css`), the `cn` helper, and the search and filter controls.

Each web app has a copy of these files at the same paths under `web/src`. Do not change the copies. Change the files here, then copy them to all apps:

```bash
python3 scripts/sync-web-ui.py
```

`scripts/check-app-stack.py` runs in pre-commit and fails when a copy is different from this library, or when an app has a ui component that is not in this library. See `docs/src/content/docs/reference/app-stack.md`.

## Contents

| File | Source |
| --- | --- |
| `src/components/ui/button.tsx`, `card.tsx`, `popover.tsx`, `progress.tsx`, `skeleton.tsx`, `sonner.tsx`, `tooltip.tsx` | shadcn 4.23.0, `new-york` style |
| `src/components/search.tsx` | Search box and filter chips |
| `src/index.css` | Tailwind 4 theme tokens for light and dark mode |
| `src/lib/utils.ts` | `cn` helper (`clsx` and `tailwind-merge`) |

The components differ from the shadcn output in three places. They import `cn` from `@/lib/utils`, they have no `"use client"` line, and `sonner.tsx` uses the system theme without `next-themes`.

## Add a Component

Step 1: Run `bunx shadcn@4.23.0 add <component>` in one app's `web/` folder.

Step 2: Move the new file to `src/components/ui/` here, and apply the three changes above.

Step 3: Run `python3 scripts/sync-web-ui.py`, then `bun run build` in each app.
