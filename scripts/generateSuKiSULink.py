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
import sys
from pathlib import Path

from ksu_common import (ABI_MAP, find_local_package, find_remote_asset,
                        install_local_package, write_download_link, write_env)

# The upstream project of the SuKiSU family. The releases are published by the
# KernelSU-Next organization, the personal repository of the original author
# does not publish any release. Only the releases of the organization ship
# prebuilt WSA kernels.
REPOS = [
    "KernelSU-Next/KernelSU-Next",
]
LOCAL_NAMES = [
    "sukisu.zip",
]

arch = sys.argv[1]
download_dir = Path.cwd().parent / "download" if sys.argv[2] == "" else Path(sys.argv[2])
tempScript = sys.argv[3]
kernelVersion = sys.argv[4]
file_name = sys.argv[5]
# "local": skip the remote lookup, only a kernel package provided by the
# user in the download directory is accepted.
local_only = len(sys.argv) > 6 and sys.argv[6] == "local"
abi = ABI_MAP[arch]
target = download_dir / file_name

if not local_only:
    print(
        f"Generating SuKiSU download link: arch={abi}, kernel version={kernelVersion}", flush=True)
    release, asset = find_remote_asset(REPOS, abi, kernelVersion)
    if asset is not None:
        link = asset["browser_download_url"]
        release_name = (release.get("name") or release.get("tag_name") or "custom").strip()
        write_env(KERNELSU_VER=release_name)
        print(f"SuKiSU release: {release_name}", flush=True)
        print(f"download link: {link}", flush=True)
        write_download_link(link, download_dir, tempScript, file_name)
        sys.exit(0)

    print("No prebuilt SuKiSU kernel found in GitHub releases. Trying local kernel...", flush=True)

source = find_local_package(download_dir, abi, LOCAL_NAMES + [file_name], kernelVersion)
if source is None:
    print(
        f"Error: No SuKiSU kernel found. Place kernel-WSA-{abi}-{kernelVersion}.zip "
        f"or sukisu.zip in {download_dir}. The zip must contain a kernel file "
        f"({'bzImage' if arch == 'x64' else 'Image'}).",
        flush=True)
    sys.exit(1)
print(f"Found custom kernel: {source.name}", flush=True)
install_local_package(source, target)
write_env(KERNELSU_VER="custom")
print(f"Custom kernel ready: {target.name}", flush=True)
# Do NOT write to the aria2c conf - the file is already local
