import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';
import mermaid from 'astro-mermaid';

export default defineConfig({
  site: 'https://docs.sudhanva.me',
  integrations: [
    sitemap(),
    mermaid(),
    starlight({
      title: 'Talos Linux Homelab',
      description: 'Talos Linux Kubernetes cluster on immutable infrastructure, managed via GitOps with ArgoCD, Cilium CNI, and declarative talosctl automation.',
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
            content: 'talos linux kubernetes, talos cluster, ubuntu 26.04 containers, argocd gitops, cilium cni, homelab kubernetes, longhorn storage',
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
            content: 'https://docs.sudhanva.me/og-image.svg',
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
            content: 'https://docs.sudhanva.me/og-image.svg',
          },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'canonical',
            href: 'https://docs.sudhanva.me',
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
            'description': 'Complete guide to building a Talos Linux Kubernetes cluster with declarative machine configuration, ArgoCD, and Cilium.',
            'author': {
              '@type': 'Person',
              'name': 'Sudhanva Narayana',
            },
            'publisher': {
              '@type': 'Organization',
              'name': 'homelab',
              'url': 'https://github.com/nsudhanva/homelab',
            },
            'mainEntityOfPage': 'https://docs.sudhanva.me',
          }),
        },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Overview', slug: 'index' },
            { label: 'From Scratch', slug: 'how-to/from-scratch' },
            { label: 'Local Development', slug: 'tutorials/local-talos-cluster' },
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
                { label: 'Boot Media', slug: 'tutorials/system-prep' },
                { label: 'Machine Configuration', slug: 'tutorials/containerd' },
              ],
            },
            {
              label: 'Cluster Bootstrap',
              collapsed: true,
              items: [
                { label: 'Talos Bootstrap', slug: 'tutorials/kubernetes' },
                { label: 'Cilium CNI', slug: 'tutorials/cilium' },
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
                { label: 'Sync ArgoCD Apps', slug: 'how-to/argocd-sync' },
                { label: 'Connect Repo to ArgoCD', slug: 'how-to/argocd-repo' },
                { label: 'Automated Image Updates', slug: 'how-to/image-updates' },
              ],
            },
            {
              label: 'Storage & Secrets',
              collapsed: true,
              items: [
                { label: 'Longhorn Storage', slug: 'how-to/storage' },
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
                { label: 'Ntfy Alerting', slug: 'how-to/ntfy-alerting' },
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
            { label: 'Local vs Bare Metal', slug: 'explanation/local-vs-baremetal' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Infrastructure Components', slug: 'reference/infrastructure-components' },
            { label: 'Applications Catalog', slug: 'reference/applications' },
            { label: 'Version Matrix', slug: 'reference/versions' },
            { label: 'Operations Checklist', slug: 'reference/operations-checklist' },
          ],
        },
      ],
    }),
  ],
});
