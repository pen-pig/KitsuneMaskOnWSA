#!/usr/bin/python3
#
# This file is part of MagiskOnWSALocal.
#
# MagiskOnWSALocal is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# MagiskOnWSALocal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with MagiskOnWSALocal.  If not, see <https://www.gnu.org/licenses/>.
#
# Copyright (C) 2025 LSPosed Contributors
#
"""Shared helpers for the KernelSU / SuKiSU / APatch WSA kernel generators."""
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, OrderedDict

import requests

ABI_MAP = {"x64": "x86_64", "arm64": "arm64"}
# Name of the kernel image inside a WSA kernel package, keyed by ABI
KERNEL_MEMBER = {"x86_64": "bzImage", "arm64": "Image"}


class Prop(OrderedDict):
    def __init__(self, props: str = ...) -> None:
        super().__init__()
        for i, line in enumerate(props.splitlines(False)):
            if '=' in line:
                k, v = line.split('=', 1)
                self[k] = v
            else:
                self[f".{i}"] = line

    def __setattr__(self, __name: str, __value: Any) -> None:
        self[__name] = __value

    def __repr__(self):
        return '\n'.join(f'{item}={self[item]}' for item in self)


def write_env(**kwargs: str) -> None:
    """Update the WSA work environment file with the given key/value pairs."""
    env_path = os.environ['WSA_WORK_ENV']
    with open(env_path, 'r') as environ_file:
        env = Prop(environ_file.read())
    for key, value in kwargs.items():
        setattr(env, key, value)
    with open(env_path, 'w') as environ_file:
        environ_file.write(str(env))


def fetch_releases(repo: str, per_page: int = 100, max_pages: int = 3) -> list:
    """Return the releases of a GitHub repository, newest first.

    ``/releases/latest`` cannot be used here: the latest release of the
    upstream projects usually does not ship WSA kernel assets anymore.
    """
    releases = []
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}&page={page}"
        try:
            res = requests.get(url, timeout=30)
        except requests.RequestException as e:
            print(f"Failed to fetch releases of {repo}: {e}", flush=True)
            break
        if res.status_code != 200:
            if res.status_code == 403 and res.headers.get("x-ratelimit-remaining") == "0":
                print(f"Github API rate limit exceeded for {repo}", flush=True)
            break
        try:
            data = res.json()
        except ValueError:
            break
        if not data:
            break
        releases.extend(data)
        if len(data) < per_page:
            break
    return releases


def kernel_base(version: str) -> str:
    """Return the ``major.minor.patch`` part of a kernel version."""
    return ".".join(version.split(".")[:3])


def versions_match(left: str, right: str) -> bool:
    """Compare two kernel versions, ignoring the patch level."""
    if not left or not right:
        return False
    return kernel_base(left) == kernel_base(right)


def parse_kernel_version(asset_name: str):
    """Extract the kernel version encoded in a WSA kernel asset name."""
    match = re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)', asset_name)
    return match.group(1) if match else None


def find_remote_asset(repos: list, abi: str, kernel_version: str):
    """Find the best prebuilt WSA kernel asset for the given kernel version.

    The asset whose version matches ``kernel_version`` exactly wins, otherwise
    the first release shipping a kernel of the same ``major.minor.patch`` line
    is used. Returns a ``(release, asset)`` tuple or ``(None, None)``.
    """
    if not kernel_version:
        return None, None
    best = None
    for repo in repos:
        for index, release in enumerate(fetch_releases(repo)):
            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if not name.endswith(".zip"):
                    continue
                match = re.match(rf'^kernel-WSA-{re.escape(abi)}-(\d+\.\d+\.\d+(?:\.\d+)?)', name)
                if not match:
                    continue
                version = match.group(1)
                if not versions_match(version, kernel_version):
                    continue
                # prefer an exact match, then the newest release
                score = (1 if version == kernel_version else 0, -index)
                if best is None or score > best[0]:
                    best = (score, release, asset)
    if best is None:
        return None, None
    return best[1], best[2]


def zip_has_kernel(path: Path, abi: str) -> bool:
    """Check that a kernel package contains the kernel image for ``abi``."""
    member = KERNEL_MEMBER[abi]
    try:
        with zipfile.ZipFile(path) as archive:
            return any(name.split('/')[-1] == member for name in archive.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def _bzimage_version(data: bytes):
    """Read the kernel version from a bzImage setup header.

    The version string is stored in the (compressed) setup header, so it
    cannot be found by a plain search in the image.
    """
    if len(data) < 0x210:
        return None
    offset = int.from_bytes(data[0x20E:0x210], "little")
    start = 0x200 + offset
    if start >= len(data):
        return None
    end = data.find(b"\x00", start)
    if end < 0:
        end = start + 120
    text = data[start:end].decode(errors="replace").strip()
    match = re.match(r"(\d+\.\d+\.\d+(?:\.\d+)?)", text)
    return match.group(1) if match else None


def kernel_version_of_zip(path: Path, abi: str):
    """Return the kernel version of a kernel package, or None if unavailable.

    Also verifies that the package contains the kernel image expected for
    the given architecture.
    """
    member = KERNEL_MEMBER[abi]
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            candidates = [n for n in names if n.split('/')[-1] == member]
            if not candidates:
                return None
            data = archive.read(candidates[0])
    except (zipfile.BadZipFile, OSError):
        return None
    if member == "bzImage":
        version = _bzimage_version(data)
        if version:
            return version
    match = re.search(rb'Linux version ([0-9][^\s\x00]*)', data)
    if match is None:
        return None
    return match.group(1).decode(errors="replace").split('-')[0]


def find_local_package(download_dir: Path, abi: str, extra_names: list, kernel_version: str = ""):
    """Find a user provided kernel package in the download directory.

    Only packages that actually contain a kernel image for ``abi`` are
    accepted. The package whose kernel version matches ``kernel_version``
    is preferred.
    """
    candidates = []
    if download_dir.is_dir():
        candidates.extend(sorted(download_dir.glob(f"kernel-WSA-{abi}-*.zip")))
        for name in extra_names:
            path = download_dir / name
            if path.is_file():
                candidates.append(path)
    usable = []
    for path in candidates:
        if not zip_has_kernel(path, abi):
            continue
        version = kernel_version_of_zip(path, abi)
        usable.append((version or "", path))
    if not usable:
        return None
    for version, path in usable:
        if kernel_version and versions_match(version, kernel_version):
            return path
    return usable[0][1]


def install_local_package(source: Path, target: Path) -> None:
    """Copy a user provided package to the expected location.

    The original file is kept untouched so that it can be reused for
    another build.
    """
    if source.resolve() == target.resolve():
        return
    shutil.copy2(source, target)


def write_download_link(link: str, download_dir: Path, temp_script: str, out_name: str) -> None:
    with open(download_dir / temp_script, 'a') as f:
        f.writelines(f'{link}\n')
        f.writelines(f'  dir={download_dir}\n')
        f.writelines(f'  out={out_name}\n')
