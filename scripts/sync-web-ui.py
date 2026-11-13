#!/usr/bin/env python3
"""Copy the shared UI library (packages/web-ui/src) into every web app.

Each app gets the same files at the same paths under web/src. Components in an app's
web/src/components/ui that the library does not have are removed, so the library is the
only place to add or change a ui component.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "packages/web-ui/src"


def library_files() -> list[Path]:
    return sorted(p.relative_to(LIBRARY) for p in LIBRARY.rglob("*") if p.is_file())


def main() -> int:
    files = library_files()
    for web in sorted(ROOT.glob("apps/*/web")):
        src = web / "src"
        for rel in files:
            target = src / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(LIBRARY / rel, target)
        keep = {rel.name for rel in files if rel.parent == Path("components/ui")}
        for extra in (src / "components/ui").glob("*.tsx"):
            if extra.name not in keep:
                extra.unlink()
                print(f"removed {extra.relative_to(ROOT)}")
        print(f"synced {len(files)} files to {web.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
