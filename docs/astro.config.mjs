import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';
import mermaid from 'astro-mermaid';

export default defineConfig({
  site: 'https://homelab.sudhanva.me',
  integrations: [
    sitemap(),
    mermaid(),
    starlight({
      title: 'Bare-Metal K3s Homelab',
      description: 'Bare-metal K3s Kubernetes cluster on Ubuntu 26.04 LTS (node legion), managed via GitOps with ArgoCD, Envoy Gateway, and Ansible automation.',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/nsudhanva/homelab' },
      ],
      editLink: {
        baseUrl: 'https://github.com/nsudhanva/homelab/edit/master/docs/',
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'keywords',
            content: 'k3s homelab, bare metal kubernetes, ubuntu 26.04 containers, argocd gitops, envoy gateway, tailscale gateway api, local-path storage, nvidia gpu cdi',
          },
        },
        {
          tag: 'meta',
          attrs: {
            name: 'author',
            content: 'Sudhanva Narayana',
          },
        },
        {
          tag: 'meta',
          attrs: {
            property: 'og:image',
            content: 'https://homelab.sudhanva.me/og-image.svg',
          },
        },
        {
          tag: 'meta',
          attrs: {
            property: 'og:type',
            content: 'website',
          },
        },
        {
          tag: 'meta',
          attrs: {
            name: 'twitter:card',
            content: 'summary_large_image',
          },
        },
        {
          tag: 'meta',
          attrs: {
            name: 'twitter:image',
            content: 'https://homelab.sudhanva.me/og-image.svg',
          },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'canonical',
            href: 'https://homelab.sudhanva.me',
          },
        },
        {
          tag: 'script',
          attrs: {
            type: 'application/ld+json',
          },
          content: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'TechArticle',
            'headline': 'Bare Metal Kubernetes Homelab',
            'description': 'Complete guide to building a bare-metal K3s Kubernetes cluster on Ubuntu 26.04 LTS with ArgoCD GitOps, Envoy Gateway, and Ansible.',
            'author': {
              '@type': 'Person',
              'name': 'Sudhanva Narayana',
            },
            'publisher': {
              '@type': 'Organization',
              'name': 'homelab',
              'url': 'https://github.com/nsudhanva/homelab',
            },
            'mainEntityOfPage': 'https://homelab.sudhanva.me',
          }),
        },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Overview', slug: 'index' },
            { label: 'From Scratch', slug: 'how-to/from-scratch' },
          ],
        },
        {
          label: 'Tutorials',
          collapsed: false,
          items: [
            { label: 'Tutorial Overview', slug: 'tutorials' },
            {
              label: 'Node Setup',
              collapsed: true,
              items: [
                { label: 'Prerequisites', slug: 'tutorials/prerequisites' },
                { label: 'Host Preparation', slug: 'tutorials/system-prep' },
                { label: 'Ansible Configuration', slug: 'tutorials/containerd' },
              ],
            },
            {
              label: 'Cluster Bootstrap',
              collapsed: true,
              items: [
                { label: 'K3s Bootstrap', slug: 'tutorials/kubernetes' },
                { label: 'ArgoCD GitOps', slug: 'tutorials/argocd' },
                { label: 'Add Workers', slug: 'tutorials/join-workers' },
              ],
            },
          ],
        },
        {
          label: 'How-To Guides',
          collapsed: false,
          items: [
            {
              label: 'Cluster Operations',
              collapsed: true,
              items: [
                { label: 'Add Worker Node', slug: 'how-to/add-worker-node' },
                { label: 'Deploy Apps', slug: 'how-to/deploy-apps' },
                { label: 'Actual Budget', slug: 'how-to/actual-budget' },
                { label: 'Sync ArgoCD Apps', slug: 'how-to/argocd-sync' },
                { label: 'Connect Repo to ArgoCD', slug: 'how-to/argocd-repo' },
                { label: 'Automated Image Updates', slug: 'how-to/image-updates' },
                { label: 'GitOps Automation', slug: 'how-to/gitops-automation' },
              ],
            },
            {
              label: 'Storage & Secrets',
              collapsed: true,
              items: [
                { label: 'Local-Path Storage', slug: 'how-to/storage' },
                { label: 'Vault Secrets', slug: 'how-to/vault' },
              ],
            },
            {
              label: 'Networking',
              collapsed: true,
              items: [
                { label: 'Tailscale Ingress', slug: 'how-to/tailscale' },
              ],
            },
            {
              label: 'Monitoring & Security',
              collapsed: true,
              items: [
                { label: 'Prometheus & Grafana', slug: 'how-to/monitoring' },
                { label: 'Kubescape Security', slug: 'how-to/kubescape' },
              ],
            },
            {
              label: 'Maintenance',
              collapsed: true,
              items: [
                { label: 'Cluster Maintenance', slug: 'how-to/maintenance' },
                { label: 'Validation', slug: 'how-to/validation' },
                { label: 'CI/CD Pipeline', slug: 'how-to/ci-cd' },
              ],
            },
            {
              label: 'Advanced',
              collapsed: true,
              items: [
                { label: 'GPU Support', slug: 'how-to/gpu' },
                { label: 'Headlamp UI', slug: 'how-to/headlamp' },
                { label: 'Scheduling Workloads', slug: 'how-to/scheduling-workloads' },
                { label: 'Ubuntu Workstation', slug: 'tutorials/workstation' },
              ],
            },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Automation Model', slug: 'explanation/automation-model' },
            { label: 'Gateway & Networking', slug: 'explanation/gateway-networking' },
            { label: 'Node Networking & DNS', slug: 'explanation/node-networking' },
            { label: 'Storage Architecture', slug: 'explanation/storage-architecture' },
            { label: 'AI Email Classifier', slug: 'explanation/gmail-classifier' },
          ],
        },

        {
          label: 'Reference',
          items: [
            { label: 'Infrastructure Components', slug: 'reference/infrastructure-components' },
            { label: 'Applications Catalog', slug: 'reference/applications' },
            { label: 'Version Matrix', slug: 'reference/versions' },
            { label: 'Operations Checklist', slug: 'reference/operations-checklist' },
            { label: 'Documentation Structure', slug: 'reference/docs-structure' },
          ],
        },
      ],
    }),
  ],
});
