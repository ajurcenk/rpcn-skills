# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Download the tested Redpanda Connect release binaries (AD-5).

Reads tools/rpcn_versions.txt (the only place tested versions are named), and
for each version downloads the plain release build
`redpanda-connect_<v>_<os>_<arch>.tar.gz` from the redpanda-data/connect GitHub
releases, checks it against the published `.sha256`, and unpacks it into
`.cache/rpcn/<v>/`. Versions already present are skipped.

Prints a JSON list of the binary paths on stdout. Exits non-zero on a checksum
failure, a download failure or an unsupported platform.

Run: uv run tools/fetch_rpcn.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSIONS_FILE = REPO_ROOT / "tools" / "rpcn_versions.txt"
CACHE_DIR = REPO_ROOT / ".cache" / "rpcn"
BINARY_NAME = "redpanda-connect"
RELEASE_URL = "https://github.com/redpanda-data/connect/releases/download/v{v}/{asset}"

_OS = {"Linux": "linux", "Darwin": "darwin"}
_ARCH = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


class FetchError(Exception):
    pass


def read_versions(path: Path = VERSIONS_FILE) -> list[str]:
    versions = []
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            versions.append(line.removeprefix("v"))
    if not versions:
        raise FetchError(f"{path} lists no versions")
    return versions


def platform_tag() -> str:
    system, machine = platform.system(), platform.machine()
    if system not in _OS or machine.lower() not in _ARCH:
        raise FetchError(f"unsupported platform {system}/{machine}; only Linux and macOS on amd64 or arm64")
    return f"{_OS[system]}_{_ARCH[machine.lower()]}"


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "rpcn-skills-fetch"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except OSError as exc:
        raise FetchError(f"download of {url} failed: {exc}") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_version(binary: Path, version: str) -> None:
    """Fail unless `binary --version` reports exactly `version` (catches a stale cache)."""
    try:
        proc = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FetchError(f"{binary} --version failed: {exc}") from exc
    m = re.search(r"^\s*Version:\s*v?(\S+)\s*$", proc.stdout + proc.stderr, re.MULTILINE)
    got = m.group(1) if m else None
    if proc.returncode != 0 or got != version:
        raise FetchError(f"{binary} reports version {got!r}, expected {version!r}")


def fetch(version: str, tag: str) -> Path:
    target_dir = CACHE_DIR / version
    binary = target_dir / BINARY_NAME
    if binary.is_file() and os.access(binary, os.X_OK):
        check_version(binary, version)
        return binary

    asset = f"redpanda-connect_{version}_{tag}.tar.gz"
    url = RELEASE_URL.format(v=version, asset=asset)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CACHE_DIR) as tmp:
        tmp_dir = Path(tmp)
        archive = tmp_dir / asset
        checksum = tmp_dir / f"{asset}.sha256"
        _download(url, archive)
        _download(url + ".sha256", checksum)
        fields = checksum.read_text().split()
        if not fields:
            raise FetchError(f"{url}.sha256 is empty")
        expected, actual = fields[0].lower(), _sha256(archive)
        if expected != actual:
            raise FetchError(f"checksum mismatch for {asset}: expected {expected}, got {actual}")

        unpack = tmp_dir / "unpack"
        unpack.mkdir()
        with tarfile.open(archive) as tar:
            member = next(
                (m for m in tar.getmembers() if m.isfile() and Path(m.name).name == BINARY_NAME),
                None,
            )
            if member is None:
                raise FetchError(f"{asset} holds no {BINARY_NAME} binary")
            src = tar.extractfile(member)
            assert src is not None
            out = unpack / BINARY_NAME
            with src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        out.chmod(0o755)
        check_version(out, version)

        if target_dir.exists():
            shutil.rmtree(target_dir)
        unpack.rename(target_dir)
    return binary


def main() -> int:
    try:
        tag = platform_tag()
        paths = [str(fetch(v, tag)) for v in read_versions()]
    except FetchError as exc:
        print(f"fetch_rpcn: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
