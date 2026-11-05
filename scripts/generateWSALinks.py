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
# Copyright (C) 2024 LSPosed Contributors
#

import logging
import re
import sys

from pathlib import Path
from threading import Thread
from xml.dom import minidom

from packaging import version
from requests import Session

from wsa_builds import (
    FE3_SECURED_URL,
    RELEASE_NAME_MAP,
    RELEASE_TYPES,
    SOAP_HEADERS,
    android_version_of,
    android_versions_of,
    get_cookie,
    kernel_hint,
    query_feed,
    wsa_builds,
)

logging.captureWarnings(True)
arch = sys.argv[1]

release_type = sys.argv[2] if sys.argv[2] != "" else "retail"
if release_type.lower() == "retail":
    release_type = "retail"
release_name = RELEASE_NAME_MAP.get(release_type, release_type)
download_dir = Path.cwd().parent / \
    "download" if sys.argv[3] == "" else Path(sys.argv[3])
ms_account_conf = download_dir/".ms_account"
tempScript = sys.argv[4]
skip_wsa_download = sys.argv[5] == "1" if len(sys.argv) >= 6 else False
# Optional target: "latest", an Android version (13.0/12.1/11.0) or an exact
# build number (2407.40000.4.0). Defaults to the newest build.
target = sys.argv[6] if len(sys.argv) >= 7 else ""
user = ''
session = Session()
session.verify = False
if ms_account_conf.is_file():
    with open(ms_account_conf, "r") as f:
        conf = f.read().splitlines()
        for line in conf:
            if line.startswith('user_code='):
                user = line.split('=', 1)[1]
                break
print(
    f"Generating WSA download link: arch={arch} release_type={release_name}\n", flush=True)

xml_dir = Path.cwd().parent / "xml"
cookie = get_cookie(session, xml_dir, user)

feed_cache = {}


def feed(channel):
    if channel not in feed_cache:
        feed_cache[channel] = query_feed(session, xml_dir, user, cookie, channel)
    return feed_cache[channel]


def builds_of(channel):
    return wsa_builds(feed(channel))


def pick(builds):
    """Return the build of ``builds`` matching the requested target."""
    if not builds:
        return ""
    if target in ("", "latest", "newest"):
        return max(builds, key=version.parse)
    if re.fullmatch(r"\d{4}\.\d{5}\.\d{1,}\.\d{1,}", target):
        return target if target in builds else ""
    wanted = target if target.count(".") == 1 else target + ".0"
    candidates = [b for b in builds if android_version_of(b) == wanted]
    return max(candidates, key=version.parse) if candidates else ""


if target and target not in ("latest", "newest", "") and not re.fullmatch(
        r"\d{4}\.\d{5}\.\d{1,}\.\d{1,}", target):
    wanted = target if target.count(".") == 1 else target + ".0"
    if not re.fullmatch(r"\d+\.\d+", wanted):
        raise SystemExit(f"ERROR: Invalid Android version: {target}")

# The requested channel is preferred, but the retail channel only exposes the
# newest build, so the other channels are used as a fallback.
channel = ""
wsa_build_ver = ""
for candidate in [release_type] + [c for c in RELEASE_TYPES if c != release_type]:
    wsa_build_ver = pick(builds_of(candidate))
    if wsa_build_ver:
        channel = candidate
        break

if not wsa_build_ver:
    known = {}
    for c in RELEASE_TYPES:
        for b in builds_of(c):
            known[b] = c
    if skip_wsa_download:
        print("WARN: No matching WSA build found, only the dependencies are downloaded", flush=True)
        sys.exit(0)
    print("ERROR: No WSA build matching the request is available.", flush=True)
    # Only offer what Microsoft actually publishes, nothing else.
    available = android_versions_of(known)
    if available:
        print(f"Available Android versions: {', '.join(available)}", flush=True)
    print("Available WSA builds:", flush=True)
    for b in sorted(known, key=version.parse):
        print(f"  {b}  (Android {android_version_of(b)}, kernel {kernel_hint(b) or 'unknown'})", flush=True)
    sys.exit(1)

if channel != release_type:
    print(f"Selected build {wsa_build_ver} from the "
          f"{RELEASE_NAME_MAP.get(channel, channel)} channel", flush=True)

identities = feed(channel)

with open(Path.cwd().parent / "xml/FE3FileUrl.xml", "r") as f:
    FE3_file_content = f.read()

if not download_dir.is_dir():
    download_dir.mkdir()

tmpdownlist = open(download_dir/tempScript, 'a')
download_files = {}


def send_req(i, v, out_file_name):
    out = session.post(
        FE3_SECURED_URL,
        data=FE3_file_content.format(user, i, v, channel),
        headers=SOAP_HEADERS
    )
    doc = minidom.parseString(out.text)
    for l in doc.getElementsByTagName("FileLocation"):
        url = l.getElementsByTagName("Url")[0].firstChild.nodeValue
        if len(url) != 99:
            download_files[out_file_name] = url


threads = []
for filename, values in identities.items():
    if re.match(rf"Microsoft\.UI\.Xaml\..*_{arch}_.*\.appx", filename):
        out_file_name = f"{values[1]}_{arch}.appx"
        out_file = download_dir / out_file_name
    elif re.match(rf"Microsoft\.VCLibs\..+\.UWPDesktop_.*_{arch}_.*\.appx", filename):
        out_file_name = f"{values[1]}_{arch}.appx"
        out_file = download_dir / out_file_name
    elif re.match(rf"Microsoft\.VCLibs\..+_.*_{arch}_.*\.appx", filename):
        out_file_name = f"{values[1]}_{arch}.appx"
        out_file = download_dir / out_file_name
    elif not skip_wsa_download and re.match(rf"MicrosoftCorporationII\.WindowsSubsystemForAndroid_.*\.msixbundle", filename):
        tmp_wsa_build_ver = re.search(
            r'\d{4}.\d{5}.\d{1,}.\d{1,}', filename).group()
        if (wsa_build_ver != tmp_wsa_build_ver):
            continue
        out_file_name = f"wsa-{release_type}.zip"
        out_file = download_dir / out_file_name
    else:
        continue
    th = Thread(target=send_req, args=(
        values[0][0], values[0][1], out_file_name))
    threads.append(th)
    th.daemon = True
    th.start()
for th in threads:
    th.join()
print(f'WSA Build Version={wsa_build_ver}\n', flush=True)
print(f'WSA Android Version={android_version_of(wsa_build_ver)}\n', flush=True)
for key, value in download_files.items():
    print(f"download link: {value}\npath: {download_dir / key}\n", flush=True)
    tmpdownlist.writelines(value + '\n')
    tmpdownlist.writelines(f'  dir={download_dir}\n')
    tmpdownlist.writelines(f'  out={key}\n')
tmpdownlist.close()
