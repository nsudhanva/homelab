# Homelab Documentation

Documentation for the bare-metal K3s homelab cluster. The site uses [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/).

## Prerequisites

- [Bun](https://bun.sh/) (v1.3+ recommended) or Node.js 24+ LTS

## Installation

Install the dependencies with Bun:

```bash
bun install
```

## Local Development

Start the local development server:

```bash
bun dev
```

The site is available at `http://localhost:4321/` with hot module reloading.

## Type Checking and Validation

Run the Astro type checker:

```bash
bunx @astrojs/check
```

## Production Build

Build the static site into the `dist/` directory:

```bash
bun run build
```

Preview the production build locally:

```bash
bun run preview
```

## Container Image

The `Dockerfile` builds the site and serves `dist/` with nginx. The server configuration is in `nginx/default.conf`:

- Requests to `docs.sudhanva.me` get a 301 redirect to the same path on `homelab.sudhanva.me`.
- Redirects use relative `Location` headers, so they keep HTTPS behind the gateway.
- Requests for old Markdown URLs, such as `/how-to/how-to/vault.md`, get a 301 redirect to the live page. The build runs `scripts/md-redirects.mjs`, which writes this map from the pages in `dist/`.
- Unknown paths return the Starlight 404 page with status 404.

Each page sets its own canonical URL from `site` in `astro.config.mjs`. Do not add a global canonical link in `head`.

## Documentation Structure

The documentation uses the [Divio documentation system](https://docs.divio.com/documentation-system/):

- `tutorials/`: Learning-oriented tutorials (for example, node preparation and K3s bootstrap)
- `how-to/`: Problem-oriented how-to guides (for example, worker nodes, storage, and monitoring)
- `reference/`: Information-oriented technical reference (for example, versions and the application catalog)
- `explanation/`: Understanding-oriented explanations of the architecture (for example, networking and storage)

The content is in Markdown (`.md`) and MDX (`.mdx`) files in `src/content/docs/`.
