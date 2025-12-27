import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

const pathways = [
  {
    title: 'Local rehearsal (Multipass)',
    description:
      'Spin up a three-node VM cluster that mirrors bare metal, then iterate fast.',
    href: '/docs/tutorials/local-multipass-cluster',
  },
  {
    title: 'Bare metal bring-up',
    description:
      'Provision Ubuntu 24.04 nodes with Ansible, then bootstrap Kubernetes with kubeadm.',
    href: '/docs/tutorials/prerequisites',
  },
  {
    title: 'Operate with GitOps',
    description:
      'ArgoCD owns cluster state. App and infra changes flow through Git.',
    href: '/docs/explanation/automation-model',
  },
];

const checklists = [
  {
    title: 'Step 1',
    text: 'Provision nodes with Ansible.',
  },
  {
    title: 'Step 2',
    text: 'Initialize the control plane and install Cilium.',
  },
  {
    title: 'Step 3',
    text: 'Bootstrap ArgoCD and sync apps.',
  },
];

function Hero() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={styles.hero}>
      <div className={styles.heroBackdrop} />
      <div className={styles.heroContent}>
        <div className={styles.heroLeft}>
          <Heading as="h1" className={styles.heroTitle}>
            {siteConfig.title}
          </Heading>
          <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryButton} to="/docs/intro">
              Read the docs
            </Link>
            <Link className={styles.secondaryButton} to="/docs/how-to/argocd-sync">
              Sync with ArgoCD
            </Link>
          </div>
        </div>
        <div className={styles.heroRight}>
          <div className={styles.card}>
            <Heading as="h2" className={styles.cardTitle}>
              Automation-first flow
            </Heading>
            <p className={styles.cardText}>
              Ansible manages nodes. ArgoCD manages the cluster. Every change is
              reproducible, reviewable, and versioned.
            </p>
            <div className={styles.cardFooter}>
              <Link className={styles.cardLink} to="/docs/reference/operations-checklist">
                Operations checklist
              </Link>
              <Link className={styles.cardLink} to="/docs/reference/versions">
                Version matrix
              </Link>
            </div>
          </div>
          <div className={styles.checklist}>
            {checklists.map((item) => (
              <div key={item.title} className={styles.checklistItem}>
                <span className={styles.checklistTitle}>{item.title}</span>
                <span className={styles.checklistText}>{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}

function Pathways() {
  return (
    <section className={styles.pathways}>
      <div className={styles.sectionHeader}>
        <Heading as="h2" className={styles.sectionTitle}>
          Choose your path
        </Heading>
        <p className={styles.sectionSubtitle}>
          Start local, migrate to bare metal, and operate with GitOps.
        </p>
      </div>
      <div className={styles.pathwayGrid}>
        {pathways.map((path) => (
          <div key={path.title} className={styles.pathwayCard}>
            <Heading as="h3" className={styles.pathwayTitle}>
              {path.title}
            </Heading>
            <p className={styles.pathwayText}>{path.description}</p>
            <Link className={styles.pathwayLink} to={path.href}>
              Open guide
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}

function QuickLinks() {
  return (
    <section className={styles.quickLinks}>
      <Heading as="h2" className={styles.sectionTitle}>
        Runbooks
      </Heading>
      <div className={styles.linkGrid}>
        <Link className={styles.linkCard} to="/docs/how-to/maintenance">
          Cluster maintenance
        </Link>
        <Link className={styles.linkCard} to="/docs/how-to/deploy-apps">
          Deploy an app
        </Link>
        <Link className={styles.linkCard} to="/docs/how-to/storage">
          Storage and Longhorn
        </Link>
        <Link className={styles.linkCard} to="/docs/how-to/argocd-sync">
          ArgoCD sync
        </Link>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout title="Homelab" description="Bare-metal Kubernetes with GitOps automation.">
      <Hero />
      <main className={styles.main}>
        <Pathways />
        <QuickLinks />
      </main>
    </Layout>
  );
}
