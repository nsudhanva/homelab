# Offers

Offers tracks credit card and subscription credits against the transactions in Actual Budget. It shows the credits that are used and unused in each period, and it sends Telegram reminders before unused credits expire.

- `catalog.yaml`: the cards and their offers
- `src/offers/engine.py`: the rules, the AI candidates, and the offer states
- `src/offers/sync.py`: the daily job
- `src/offers/web.py`: the JSON API, and the server for the single-page app
- `web/`: the single-page app (React, TanStack Router and Query, shadcn/ui, Tailwind CSS). Run `bun install` and `bun run dev` in `web/`, with `offers serve` on port 8000

For the full guide, refer to `docs/src/content/docs/how-to/offers.md`.

## Commands

```bash
uv run offers check-catalog
uv run offers sync --no-notify
uv run offers serve --port 8000
uv run ruff check && uv run ruff format --check && uv run ty check && uv run pytest
```

The tests use synthetic data only. Do not add real transactions, account names, or account numbers to this directory.
