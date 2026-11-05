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

from ksu_common import (ABI_MAP, find_local_package, install_local_package,
                        write_env)

# APatch does not publish prebuilt WSA kernels, the kernel has to be
# provided by the user.
LOCAL_NAMES = [
    "apatch.zip",
]

arch = sys.argv[1]
download_dir = Path.cwd().parent / "download" if sys.argv[2] == "" else Path(sys.argv[2])
kernelVersion = sys.argv[4]
file_name = sys.argv[5]
abi = ABI_MAP[arch]
target = download_dir / file_name

print(f"Looking for APatch kernel: arch={abi}, kernel version={kernelVersion}", flush=True)
source = find_local_package(download_dir, abi, LOCAL_NAMES + [file_name], kernelVersion)
if source is None:
    print(
        f"Error: No APatch kernel found. Place apatch-WSA-{abi}-{kernelVersion}.zip "
        f"or apatch.zip in {download_dir}. The zip must contain a kernel file "
        f"({'bzImage' if arch == 'x64' else 'Image'}).",
        flush=True)
    sys.exit(1)
print(f"Found APatch kernel: {source.name}", flush=True)
install_local_package(source, target)
write_env(KERNELSU_VER="custom")
print(f"APatch kernel ready: {target.name}", flush=True)
