---
title: Documentation Structure
description: Rules for contributions to the homelab documentation. Covers file names, frontmatter, and content organization with the Divio documentation system.
keywords:
  - documentation guidelines
  - divio documentation system
  - astro starlight
  - documentation structure
  - markdown documentation
sidebar:
  order: 5
---

# Documentation Structure

The documentation uses [Astro Starlight](https://starlight.astro.build/) and the [Divio documentation system](https://docs.divio.com/documentation-system/).

## Content Organization

| Section | Purpose | Example |
|---------|---------|---------|
| **Tutorials** | Learning-oriented walkthroughs | Setting up the cluster |
| **How-To Guides** | Problem-oriented procedures | Adding a worker node |
| **Explanation** | Understanding-oriented concepts | GitOps automation model |
| **Reference** | Information-oriented lookup | Version matrix |

## File Locations

```text
docs/src/content/docs/
├── tutorials/      # Step-by-step learning paths
├── how-to/         # Task-specific procedures
├── explanation/    # Architecture and concepts
├── reference/      # Component catalogs and matrices
└── index.mdx       # Landing page
```

## Frontmatter Requirements

Each document must have SEO-optimized frontmatter:

```yaml
---
title: Descriptive Title with Keywords
description: Clear description for search results (150-160 chars)
keywords:
  - primary keyword
  - secondary keyword
  - related terms
sidebar:
  order: 1
---
```

## Naming Conventions

- Use lowercase kebab-case: `add-worker-node.md`
- Use task-based names: `deploy-apps.md` not `apps.md`
- Do not use numeric prefixes in filenames

## Mermaid Diagrams

The astro-mermaid plugin renders the diagrams:

```mermaid
flowchart LR
  Git[Git] --> ArgoCD[ArgoCD]
  ArgoCD --> K8s[Kubernetes API]
```

## Writing Guidelines

- Follow the [AGENTS.md](https://github.com/nsudhanva/homelab/blob/master/AGENTS.md) conventions
- Use tables, not numbered lists, for steps
- Do not use inline YAML comments
- Write professional prose with no marketing language
