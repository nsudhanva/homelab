import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

const launchpads = [
  {
    kicker: 'From scratch',
    title: 'Rebuild the cluster end-to-end',
    description:
      'Use the repo as the source of truth for a clean bare-metal or VM rebuild.',
    href: '/docs/how-to/from-scratch',
  },
  {
    kicker: 'Local rehearsal',
    title: 'Simulate the homelab on Multipass',
    description:
      'Spin up a local control plane + workers to validate changes before bare metal.',
    href: '/docs/tutorials/local-multipass-cluster',
  },
  {
    kicker: 'GitOps ops',
    title: 'Operate through ArgoCD',
    description:
      'Sync infrastructure and apps using ApplicationSets with drift-free automation.',
    href: '/docs/explanation/automation-model',
  },
  {
    kicker: 'Automation',
    title: 'Keep images up to date',
    description:
      'Let ArgoCD Image Updater track new tags and commit back to Git.',
    href: '/docs/how-to/image-updates',
  },
];

const snapshot = [
  {
    title: 'GitOps control',
    text: 'ArgoCD + ApplicationSets for infra and apps.',
  },
  {
    title: 'Ingress',
    text: 'Gateway API, Envoy Gateway, and Tailscale.',
  },
  {
    title: 'Storage + backup',
    text: 'Longhorn volumes and PVC-driven apps.',
  },
  {
    title: 'Secrets',
    text: 'Vault + External Secrets for all credentials.',
  },
];

const systems = [
  {
    title: 'Networking and ingress',
    description:
      'Gateway API, ExternalDNS, and split-horizon routing for tailnet HTTPS.',
    href: '/docs/explanation/gateway-networking',
  },
  {
    title: 'Secrets and access',
    description:
      'Vault-backed secrets and OIDC-enabled access for admin tooling.',
    href: '/docs/how-to/vault',
  },
  {
    title: 'Storage lifecycle',
    description:
      'Longhorn-backed PVCs and data movement workflows for media and apps.',
    href: '/docs/how-to/storage',
  },
  {
    title: 'Monitoring and alerting',
    description:
      'Prometheus, Grafana, and Alertmanager with GitOps-run dashboards.',
    href: '/docs/how-to/monitoring',
  },
];

const runbooks = [
  {
    title: 'Cluster maintenance',
    href: '/docs/how-to/maintenance',
  },
  {
    title: 'Deploy an app',
    href: '/docs/how-to/deploy-apps',
  },
  {
    title: 'ArgoCD sync',
    href: '/docs/how-to/argocd-sync',
  },
  {
    title: 'Version matrix',
    href: '/docs/reference/versions',
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
          <p className={styles.heroSubtitle}>
            {siteConfig.tagline}. GitOps-first, reproducible, and ready for both
            bare metal and local rehearsal.
          </p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryButton} to="/docs/how-to/from-scratch">
              Start from scratch
            </Link>
            <Link className={styles.secondaryButton} to="/docs/tutorials/local-multipass-cluster">
              Local rehearsal
            </Link>
            <Link className={styles.tertiaryButton} to="/docs/intro">
              Read the docs
            </Link>
          </div>
          <div className={styles.heroNote}>
            Built for Ubuntu 24.04 nodes, automated with Ansible and ArgoCD.
          </div>
        </div>
        <div className={styles.heroRight}>
          <div className={styles.snapshotCard}>
            <Heading as="h2" className={styles.cardTitle}>
              Cluster snapshot
            </Heading>
            <p className={styles.cardText}>
              A Git-tracked homelab where infra and apps are reconciled every sync.
            </p>
            <div className={styles.snapshotGrid}>
              {snapshot.map((item) => (
                <div key={item.title} className={styles.snapshotItem}>
                  <span className={styles.snapshotTitle}>{item.title}</span>
                  <span className={styles.snapshotText}>{item.text}</span>
                </div>
              ))}
            </div>
            <div className={styles.cardFooter}>
              <Link className={styles.cardLink} to="/docs/reference/infrastructure-components">
                Infrastructure map
              </Link>
              <Link className={styles.cardLink} to="/docs/reference/versions">
                Version matrix
              </Link>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function Launchpads() {
  return (
    <section className={styles.launchpads}>
      <div className={styles.sectionHeader}>
        <Heading as="h2" className={styles.sectionTitle}>
          Start with the right runway
        </Heading>
        <p className={styles.sectionSubtitle}>
          Pick a playbook that matches where you are today.
        </p>
      </div>
      <div className={styles.launchpadGrid}>
        {launchpads.map((card) => (
          <div key={card.title} className={styles.launchpadCard}>
            <span className={styles.launchpadKicker}>{card.kicker}</span>
            <Heading as="h3" className={styles.launchpadTitle}>
              {card.title}
            </Heading>
            <p className={styles.launchpadText}>{card.description}</p>
            <Link className={styles.launchpadLink} to={card.href}>
              Open guide
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}

function SystemMap() {
  return (
    <section className={styles.systems}>
      <div className={styles.sectionHeader}>
        <Heading as="h2" className={styles.sectionTitle}>
          Core systems
        </Heading>
        <p className={styles.sectionSubtitle}>
          The components that keep the cluster secure, observable, and stable.
        </p>
      </div>
      <div className={styles.systemGrid}>
        {systems.map((system) => (
          <div key={system.title} className={styles.systemCard}>
            <Heading as="h3" className={styles.systemTitle}>
              {system.title}
            </Heading>
            <p className={styles.systemText}>{system.description}</p>
            <Link className={styles.systemLink} to={system.href}>
              Explore system
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}

function Runbooks() {
  return (
    <section className={styles.runbooks}>
      <Heading as="h2" className={styles.sectionTitle}>
        Runbooks
      </Heading>
      <div className={styles.runbookGrid}>
        {runbooks.map((runbook) => (
          <Link key={runbook.title} className={styles.runbookCard} to={runbook.href}>
            <span>{runbook.title}</span>
            <span className={styles.runbookArrow}>→</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout title="Homelab" description="Bare-metal Kubernetes with GitOps automation.">
      <div className={styles.page}>
        <Hero />
        <main className={styles.main}>
          <Launchpads />
          <SystemMap />
          <Runbooks />
        </main>
      </div>
    </Layout>
  );
}
