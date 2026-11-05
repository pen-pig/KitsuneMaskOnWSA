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
"""List the WSA builds that are currently offered by the Microsoft FE3 service."""
import sys
from pathlib import Path

from packaging import version
from requests import Session

from wsa_builds import (
    RELEASE_TYPES,
    android_version_of,
    get_cookie,
    kernel_hint,
    query_feed,
    wsa_builds,
)

xml_dir = Path.cwd().parent / "xml"
session = Session()
session.verify = False
user = ''
cookie = get_cookie(session, xml_dir, user)

builds = {}
for channel in RELEASE_TYPES:
    try:
        for build in wsa_builds(query_feed(session, xml_dir, user, cookie, channel)):
            builds.setdefault(build, channel)
    except Exception as e:  # noqa: BLE001 - a broken channel must not hide the others
        print(f"WARN: Failed to query the {channel} channel: {e}", file=sys.stderr)

for build in sorted(builds, key=version.parse):
    print(f"{build}\t{android_version_of(build)}\t{kernel_hint(build)}")
