#!/usr/bin/env python3
"""Delete local-registry repository prefixes, then garbage-collect orphan blobs."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPOS_ROOT = Path(os.environ.get(
    "LOCAL_REPOS_ROOT",
    "/var/lib/registry/local/docker/registry/v2/repositories",
))
GC_CONFIG = os.environ.get(
    "CLEANER_GC_LOCAL_CONFIG",
    "/etc/docker/registry/config-gc-local.yml",
)


def resolve_target(rel):
    rel = rel.strip().strip("/")
    if not rel or rel in (".", "..") or ".." in Path(rel).parts:
        raise SystemExit("invalid path: %r" % rel)
    root = REPOS_ROOT.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise SystemExit("path escapes local repositories: %r" % rel)
    if target == root:
        raise SystemExit("refusing to delete the whole local registry; pass a repo prefix")
    return target


def list_repos():
    if not REPOS_ROOT.is_dir():
        return []
    found = []
    for manifests in REPOS_ROOT.rglob("_manifests"):
        if manifests.is_dir():
            found.append(str(manifests.parent.relative_to(REPOS_ROOT)))
    return sorted(found)


def garbage_collect():
    if not Path(GC_CONFIG).is_file():
        raise SystemExit("GC config not found: %s" % GC_CONFIG)
    print("Running garbage-collect (%s)" % GC_CONFIG)
    result = subprocess.run(
        ["registry", "garbage-collect", GC_CONFIG],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if result.returncode != 0:
        raise SystemExit("garbage-collect failed with exit %s" % result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Delete local registry repository paths (images and metadata), then GC blobs.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="repository prefix, e.g. myimage or team/app (recursive)",
    )
    parser.add_argument("--list", action="store_true", help="list local repositories and exit")
    parser.add_argument("--no-gc", action="store_true", help="do not run garbage-collect after delete")
    args = parser.parse_args()

    if args.list or not args.paths:
        repos = list_repos()
        if not repos:
            print("No local repositories under %s" % REPOS_ROOT)
        else:
            print("Local repositories:")
            for repo in repos:
                print("  %s" % repo)
        if not args.list:
            parser.print_help(sys.stderr)
        return 0

    deleted = 0
    for rel in args.paths:
        target = resolve_target(rel)
        if not target.exists():
            print("Not found: %s" % rel)
            continue
        print("Deleting %s" % target)
        shutil.rmtree(target)
        deleted += 1

    if deleted == 0:
        print("Nothing deleted")
        return 1

    if not args.no_gc:
        garbage_collect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
