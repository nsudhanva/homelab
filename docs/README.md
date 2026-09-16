# Homelab Documentation

Documentation for the bare-metal K3s homelab cluster, built with [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/).

## Prerequisites

- [Bun](https://bun.sh/) (v1.3+ recommended) or Node.js 24+ LTS

## Installation

Install dependencies using Bun:

```bash
bun install
```

## Local Development

Start the local development server:

```bash
bun dev
```

The site will be available at `http://localhost:4321/` with hot module reloading.

## Type Checking & Validation

Run Astro's type checker:

```bash
bunx @astrojs/check
```

## Production Build

Generate the static site into the `dist/` directory:

```bash
bun run build
```

Preview the production build locally:

```bash
bun run preview
```

## Documentation Structure

The documentation follows the [Divio documentation system](https://docs.divio.com/documentation-system/):

- `tutorials/`: Learning-oriented tutorials (e.g., node preparation, K3s bootstrap)
- `how-to/`: Problem-oriented how-to guides (e.g., adding worker nodes, storage, monitoring)
- `reference/`: Information-oriented technical reference (e.g., versions, application catalog)
- `explanation/`: Understanding-oriented architectural explanations (e.g., networking, storage)

Content is written in Markdown (`.md`) and MDX (`.mdx`) in `src/content/docs/`.
