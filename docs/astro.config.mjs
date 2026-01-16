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
      title: 'Bare Metal Kubernetes Homelab',
      description: 'Multi-node bare-metal Kubernetes cluster on Ubuntu 24.04 LTS, managed via GitOps with ArgoCD, Cilium CNI, and Ansible automation.',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/sudhanva/homelab' },
      ],
      editLink: {
        baseUrl: 'https://github.com/sudhanva/homelab/edit/master/docs/',
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'keywords',
            content: 'bare metal kubernetes, kubeadm, ubuntu 24.04, ansible kubernetes, argocd gitops, cilium cni, homelab kubernetes, longhorn storage',
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
            'description': 'Complete guide to building a bare-metal Kubernetes cluster with kubeadm, Ansible, ArgoCD, and Cilium.',
            'author': {
              '@type': 'Person',
              'name': 'Sudhanva Narayana',
            },
            'publisher': {
              '@type': 'Organization',
              'name': 'homelab',
              'url': 'https://github.com/sudhanva/homelab',
            },
            'mainEntityOfPage': 'https://docs.sudhanva.me',
          }),
        },
      ],
      sidebar: [
        {
          label: 'Tutorials',
          autogenerate: { directory: 'tutorials' },
        },
        {
          label: 'How-To Guides',
          autogenerate: { directory: 'how-to' },
        },
        {
          label: 'Explanation',
          autogenerate: { directory: 'explanation' },
        },
        {
          label: 'Reference',
          autogenerate: { directory: 'reference' },
        },
      ],
    }),
  ],
});
