#!/usr/bin/env python3
"""Fail when the custom apps drift from one shared stack.

Rules (docs/src/content/docs/reference/app-stack.md):
- Every web app pins the frozen core packages with exact versions, and a package that two
  web apps use has the same version in both.
- Every web app holds an exact copy of the shared UI library (packages/web-ui/src) and no
  other ui component. scripts/sync-web-ui.py makes the copies.
- tsconfig.json and components.json are identical across web apps; vite.config.ts and the
  Dockerfile are identical after the app name is replaced.
- A Python package locked by two projects has the same version in both uv.lock files, and
  every project has the same requires-python.
- The ruff pre-commit hook runs the same ruff version that the projects lock.
"""

import json
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN_WEB = [
    "react",
    "react-dom",
    "@tanstack/react-query",
    "@tanstack/react-router",
    "@tanstack/router-plugin",
    "radix-ui",
    "lucide-react",
    "sonner",
    "class-variance-authority",
    "clsx",
    "tailwind-merge",
    "tailwindcss",
    "@tailwindcss/vite",
    "tw-animate-css",
    "vite",
    "@vitejs/plugin-react",
    "typescript",
    "@types/react",
    "@types/react-dom",
    "@types/node",
]
SHARED_FILES = ["tsconfig.json", "components.json"]
LIBRARY = ROOT / "packages/web-ui/src"
EXACT = re.compile(r"^\d+\.\d+\.\d+$")


def web_apps() -> dict[str, Path]:
    return {
        p.parent.parent.name: p.parent
        for p in sorted(ROOT.glob("apps/*/web/package.json"))
    }


def check_web(errors: list[str]) -> None:
    apps = web_apps()
    versions: dict[str, dict[str, str]] = defaultdict(dict)
    for name, web in apps.items():
        pkg = json.loads((web / "package.json").read_text())
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for dep, version in deps.items():
            if not EXACT.match(version):
                errors.append(
                    f"{name}: {dep} must be an exact version, not {version!r}"
                )
            versions[dep][name] = version
        for dep in FROZEN_WEB:
            if dep not in deps:
                errors.append(f"{name}: frozen web package {dep} is missing")
    for dep, by_app in sorted(versions.items()):
        if len(set(by_app.values())) > 1:
            errors.append(f"web package {dep} differs: {by_app}")

    library = sorted(p.relative_to(LIBRARY) for p in LIBRARY.rglob("*") if p.is_file())
    ui_names = {p.name for p in library if p.parent == Path("components/ui")}
    for name, web in apps.items():
        for rel in library:
            copy = web / "src" / rel
            if not copy.is_file() or copy.read_bytes() != (LIBRARY / rel).read_bytes():
                errors.append(
                    f"{name}: src/{rel} differs from packages/web-ui/src/{rel}"
                )
        for extra in sorted((web / "src/components/ui").glob("*.tsx")):
            if extra.name not in ui_names:
                errors.append(
                    f"{name}: ui component {extra.name} is not in packages/web-ui"
                )

    if len(apps) < 2:
        return
    names = list(apps)
    first = names[0]
    for rel in SHARED_FILES:
        owners = [n for n in names if (apps[n] / rel).is_file()]
        texts = {n: (apps[n] / rel).read_text() for n in owners}
        if len(set(texts.values())) > 1:
            errors.append(
                f"{rel} differs between {owners}; copy one version to all apps"
            )
    for rel, root in (("web/vite.config.ts", "apps/{}/"), ("Dockerfile", "apps/{}/")):
        texts = {}
        for n in names:
            path = ROOT / root.format(n) / rel
            if path.is_file():
                texts[n] = path.read_text().replace(n, "APP")
        if len(set(texts.values())) > 1:
            errors.append(f"{rel} differs between {sorted(texts)} beyond the app name")
    for rel in SHARED_FILES:
        if not (apps[first] / rel).is_file():
            errors.append(f"{first}: shared file {rel} is missing")


def check_python(errors: list[str]) -> dict[str, str]:
    projects = sorted(ROOT.glob("apps/*/pyproject.toml")) + sorted(
        ROOT.glob("packages/*/pyproject.toml")
    )
    pythons = {}
    locked: dict[str, dict[str, str]] = defaultdict(dict)
    for pyproject in projects:
        name = pyproject.parent.name
        pythons[name] = tomllib.loads(pyproject.read_text())["project"].get(
            "requires-python"
        )
        lock = pyproject.parent / "uv.lock"
        if not lock.is_file():
            errors.append(f"{name}: uv.lock is missing")
            continue
        for pkg in tomllib.loads(lock.read_text()).get("package", []):
            source = pkg.get("source", {})
            if "version" in pkg and not ("editable" in source or "virtual" in source):
                locked[pkg["name"]][name] = pkg["version"]
    if len(set(pythons.values())) > 1:
        errors.append(f"requires-python differs: {pythons}")
    for pkg, by_project in sorted(locked.items()):
        if len(set(by_project.values())) > 1:
            errors.append(f"python package {pkg} differs: {by_project}")
    return {pkg: next(iter(v.values())) for pkg, v in locked.items()}


def check_precommit(errors: list[str], locked: dict[str, str]) -> None:
    text = (ROOT / ".pre-commit-config.yaml").read_text()
    match = re.search(r"astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v?([\d.]+)", text)
    if match and "ruff" in locked and match.group(1) != locked["ruff"]:
        errors.append(
            f"pre-commit ruff is {match.group(1)} but the projects lock ruff {locked['ruff']}"
        )


def main() -> int:
    errors: list[str] = []
    check_web(errors)
    check_precommit(errors, check_python(errors))
    for e in errors:
        print(f"app stack: {e}")
    if errors:
        print(
            "Change packages/web-ui, then run scripts/sync-web-ui.py. Upgrade packages"
        )
        print("in all apps together. See reference/app-stack in the docs.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
