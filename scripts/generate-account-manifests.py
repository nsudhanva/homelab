#!/usr/bin/env python3
"""Generates declarative Kubernetes manifests for multi-account Google workloads.

Reads the account matrix from apps/accounts.yaml and generates symmetrical
CronJob and ExternalSecret manifests for each account in apps/gmail-classifier/
and apps/drive-organizer/.
"""

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = REPO_ROOT / "apps" / "accounts.yaml"


def generate_gmail_cronjob(account_id: str, schedule: str) -> str:
    return f"""apiVersion: batch/v1
kind: CronJob
metadata:
  name: gmail-classifier-{account_id}
  namespace: gmail-classifier
spec:
  schedule: "{schedule}"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      ttlSecondsAfterFinished: 86400
      template:
        metadata:
          labels:
            app: gmail-classifier-{account_id}
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
            - name: gmail-classifier
              image: ghcr.io/nsudhanva/homelab-gmail-classifier:latest
              imagePullPolicy: Always
              securityContext:
                runAsNonRoot: true
                runAsUser: 10001
                runAsGroup: 10001
                readOnlyRootFilesystem: true
                allowPrivilegeEscalation: false
                capabilities:
                  drop:
                    - ALL
              resources:
                requests:
                  cpu: 100m
                  memory: 128Mi
                limits:
                  cpu: 500m
                  memory: 384Mi
              envFrom:
                - secretRef:
                    name: gmail-credentials-{account_id}
                - secretRef:
                    name: openrouter-credentials
                    optional: true
              env:
                - name: ACCOUNT_NAME
                  value: "{account_id}"
                - name: PRIMARY_LLM_PROVIDER
                  value: "local"
                - name: FALLBACK_LLM_PROVIDER
                  value: "openrouter"
                - name: LLM_BASE_URL
                  value: "http://llama-server.llama.svc.cluster.local:8080/v1"
                - name: TELEGRAM_CHAT_ID
                  value: "7341944813"
                - name: CONFIDENCE_THRESHOLD
                  value: "0.80"
                - name: QUARANTINE_LABEL
                  value: "ai-review"
                - name: PROCESSED_LABEL
                  value: "ai-processed"
                - name: CONCURRENCY
                  value: "1"
                - name: ARCHIVE_OLDER_THAN_DAYS
                  value: "90"
                - name: AUTO_ARCHIVE_ENABLED
                  value: "true"
              volumeMounts:
                - name: tmp
                  mountPath: /tmp
          volumes:
            - name: tmp
              emptyDir: {{}}
"""


def generate_gmail_secret(account_id: str, vault_path: str) -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: gmail-credentials-{account_id}
  namespace: gmail-classifier
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
    argocd.argoproj.io/sync-wave: "1"
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: ClusterSecretStore
  target:
    name: gmail-credentials-{account_id}
    creationPolicy: Owner
  data:
    - secretKey: client_id
      remoteRef:
        key: {vault_path}
        property: client_id
    - secretKey: client_secret
      remoteRef:
        key: {vault_path}
        property: client_secret
    - secretKey: refresh_token
      remoteRef:
        key: {vault_path}
        property: refresh_token
    - secretKey: GMAIL_CLIENT_ID
      remoteRef:
        key: {vault_path}
        property: client_id
    - secretKey: GMAIL_CLIENT_SECRET
      remoteRef:
        key: {vault_path}
        property: client_secret
    - secretKey: GMAIL_REFRESH_TOKEN
      remoteRef:
        key: {vault_path}
        property: refresh_token
    - secretKey: TELEGRAM_BOT_TOKEN
      remoteRef:
        key: telegram/bot
        property: token
"""


def generate_drive_cronjob(account_id: str, schedule: str) -> str:
    return f"""apiVersion: batch/v1
kind: CronJob
metadata:
  name: drive-organizer-{account_id}
  namespace: drive-organizer
spec:
  schedule: "{schedule}"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 5
      template:
        metadata:
          labels:
            app: drive-organizer-{account_id}
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: drive-organizer
            image: ghcr.io/nsudhanva/homelab-drive-organizer:latest
            imagePullPolicy: Always
            args:
            - "--scope=root"
            envFrom:
            - secretRef:
                name: drive-credentials-{account_id}
            - secretRef:
                name: openrouter-credentials
                optional: true
            env:
            - name: ACCOUNT_NAME
              value: "{account_id}"
            - name: PRIMARY_LLM_PROVIDER
              value: "local"
            - name: FALLBACK_LLM_PROVIDER
              value: "openrouter"
            - name: LLM_BASE_URL
              value: "http://llama-server.llama.svc.cluster.local:8080/v1"
            - name: LLM_MODEL_NAME
              value: "gemma-4-e2b-it"
            - name: TELEGRAM_CHAT_ID
              value: "7341944813"
            resources:
              requests:
                cpu: 100m
                memory: 128Mi
              limits:
                cpu: 500m
                memory: 512Mi
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
"""


def generate_drive_secret(account_id: str, vault_path: str) -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: drive-credentials-{account_id}
  namespace: drive-organizer
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
    argocd.argoproj.io/sync-wave: "1"
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: ClusterSecretStore
  target:
    name: drive-credentials-{account_id}
    creationPolicy: Owner
  data:
  - secretKey: DRIVE_CLIENT_ID
    remoteRef:
      key: {vault_path}
      property: client_id
  - secretKey: DRIVE_CLIENT_SECRET
    remoteRef:
      key: {vault_path}
      property: client_secret
  - secretKey: DRIVE_REFRESH_TOKEN
    remoteRef:
      key: {vault_path}
      property: refresh_token
  - secretKey: TELEGRAM_BOT_TOKEN
    remoteRef:
      key: telegram/bot
      property: token
"""


def generate_kustomization(namespace: str, account_ids: list[str]) -> str:
    resources = ["namespace.yaml", "openrouter-secret.yaml"]
    for aid in account_ids:
        resources.append(f"secret-{aid}.yaml")
        resources.append(f"cronjob-{aid}.yaml")

    res_lines = "\n".join(f"- {r}" for r in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: {namespace}
resources:
{res_lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate multi-account Google Kubernetes manifests"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if manifests are up to date without writing",
    )
    args = parser.parse_args()

    if not ACCOUNTS_FILE.exists():
        print(f"Error: {ACCOUNTS_FILE} not found", file=sys.stderr)
        sys.exit(1)

    with open(ACCOUNTS_FILE) as f:
        data = yaml.safe_load(f)

    accounts = data.get("accounts", [])
    account_ids = [acc["id"] for acc in accounts]

    targets = [
        {
            "app_dir": REPO_ROOT / "apps" / "gmail-classifier",
            "namespace": "gmail-classifier",
            "schedule_key": "gmail",
            "cronjob_gen": generate_gmail_cronjob,
            "secret_gen": generate_gmail_secret,
        },
        {
            "app_dir": REPO_ROOT / "apps" / "drive-organizer",
            "namespace": "drive-organizer",
            "schedule_key": "drive",
            "cronjob_gen": generate_drive_cronjob,
            "secret_gen": generate_drive_secret,
        },
    ]

    dirty = False

    for target in targets:
        app_dir: Path = target["app_dir"]
        namespace: str = target["namespace"]
        sched_key: str = target["schedule_key"]
        cronjob_gen = target["cronjob_gen"]
        secret_gen = target["secret_gen"]

        # Expected files and contents
        expected_files: dict[Path, str] = {}

        for acc in accounts:
            aid = acc["id"]
            sched = acc["schedule"][sched_key]
            vpath = acc["vault_path"]

            cron_file = app_dir / f"cronjob-{aid}.yaml"
            secret_file = app_dir / f"secret-{aid}.yaml"

            expected_files[cron_file] = cronjob_gen(aid, sched)
            expected_files[secret_file] = secret_gen(aid, vpath)

        kust_file = app_dir / "kustomization.yaml"
        expected_files[kust_file] = generate_kustomization(namespace, account_ids)

        # Clean up legacy un-suffixed or family files
        legacy_files = [
            app_dir / "cronjob.yaml",
            app_dir / "secret.yaml",
            app_dir / "cronjob-family.yaml",
            app_dir / "secret-family.yaml",
        ]

        if args.check:
            for l_file in legacy_files:
                if l_file.exists():
                    print(f"[DRIFT] Obsolete legacy file exists: {l_file}")
                    dirty = True
            for file_path, content in expected_files.items():
                if not file_path.exists():
                    print(f"[DRIFT] Missing manifest: {file_path}")
                    dirty = True
                elif file_path.read_text() != content:
                    print(f"[DRIFT] Content mismatch: {file_path}")
                    dirty = True
        else:
            for l_file in legacy_files:
                if l_file.exists():
                    print(f"Removing obsolete file: {l_file}")
                    l_file.unlink()
            for file_path, content in expected_files.items():
                file_path.write_text(content)
                print(f"Wrote {file_path.relative_to(REPO_ROOT)}")

    if args.check and dirty:
        print(
            "Manifests drift detected. Run `python3 scripts/generate-account-manifests.py` to reconcile.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif args.check:
        print("All account manifests are in sync.")


if __name__ == "__main__":
    main()
