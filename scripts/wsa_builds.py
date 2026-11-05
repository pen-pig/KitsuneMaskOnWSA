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
"""Helpers to enumerate the WSA builds published by the Microsoft FE3 service."""
import html
import re

from xml.dom import minidom

FE3_URL = 'https://fe3.delivery.mp.microsoft.com/ClientWebService/client.asmx'
FE3_SECURED_URL = FE3_URL + '/secured'
SOAP_HEADERS = {'Content-Type': 'application/soap+xml; charset=utf-8'}
CAT_ID = '858014f3-3934-4abe-8078-4aa193e74ca8'
RELEASE_TYPES = ("retail", "RP", "WIS", "WIF")
RELEASE_NAME_MAP = {"retail": "Retail", "RP": "Release Preview",
                    "WIS": "Insider Slow", "WIF": "Insider Fast"}
WSA_BUNDLE_RE = re.compile(r"MicrosoftCorporationII\.WindowsSubsystemForAndroid_.*\.msixbundle")
BUILD_RE = re.compile(r"\d{4}\.\d{5}\.\d{1,}\.\d{1,}")
# Android version -> API level of the GApps images shipped by WSA-Addon
ANDROID_API = {"13.0": "33", "12.1": "32", "11.0": "30", "10.0": "29"}


def android_version_of(build: str) -> str:
    """Return the Android version shipped by a WSA build.

    The build number is ``YYMM.40000.rev.build``, the ``YYMM`` part tells
    which Android release the build is based on.
    """
    yymm = int(build.split(".")[0])
    if yymm >= 2211:
        return "13.0"
    if yymm >= 2204:
        return "12.1"
    if yymm >= 2106:
        return "11.0"
    return "10.0"


def kernel_hint(build: str) -> str:
    """Return the known Linux kernel version of a WSA build (may be empty)."""
    yymm = int(build.split(".")[0])
    if yymm >= 2306:
        return "5.15.104"
    if yymm >= 2305:
        return "5.15.94"
    if yymm >= 2303:
        return "5.15.78"
    return ""


def get_cookie(session, xml_dir, user: str) -> str:
    """Ask the FE3 service for a session cookie."""
    with open(xml_dir / "GetCookie.xml", "r") as f:
        content = f.read().format(user)
    out = session.post(FE3_URL, data=content, headers=SOAP_HEADERS)
    doc = minidom.parseString(out.text)
    return doc.getElementsByTagName('EncryptedData')[0].firstChild.nodeValue


def query_feed(session, xml_dir, user: str, cookie: str, release_type: str) -> dict:
    """Return the updates of a release channel.

    The result maps a file name to its ``([update_id, revision], package)``.
    """
    with open(xml_dir / "WUIDRequest.xml", "r") as f:
        cat_id_content = f.read().format(user, cookie, CAT_ID, release_type)
    out = session.post(FE3_URL, data=cat_id_content, headers=SOAP_HEADERS)
    doc = minidom.parseString(html.unescape(out.text))

    filenames = {}
    for node in doc.getElementsByTagName('ExtendedUpdateInfo')[0].getElementsByTagName('Updates')[0].getElementsByTagName('Update'):
        node_xml = node.getElementsByTagName('Xml')[0]
        node_files = node_xml.getElementsByTagName('Files')
        if not node_files:
            continue
        for node_file in node_files[0].getElementsByTagName('File'):
            if node_file.hasAttribute('InstallerSpecificIdentifier') and node_file.hasAttribute('FileName'):
                filenames[node.getElementsByTagName('ID')[0].firstChild.nodeValue] = (
                    f"{node_file.attributes['InstallerSpecificIdentifier'].value}_{node_file.attributes['FileName'].value}",
                    node_xml.getElementsByTagName('ExtendedProperties')[0].attributes['PackageIdentityName'].value)

    identities = {}
    for node in doc.getElementsByTagName('NewUpdates')[0].getElementsByTagName('UpdateInfo'):
        node_xml = node.getElementsByTagName('Xml')[0]
        if not node_xml.getElementsByTagName('SecuredFragment'):
            continue
        id = node.getElementsByTagName('ID')[0].firstChild.nodeValue
        update_identity = node_xml.getElementsByTagName('UpdateIdentity')[0]
        if id in filenames:
            fileinfo = filenames[id]
            if fileinfo[0] not in identities:
                identities[fileinfo[0]] = ([update_identity.attributes['UpdateID'].value,
                                           update_identity.attributes['RevisionNumber'].value], fileinfo[1])
    return identities


def wsa_builds(identities: dict) -> dict:
    """Return the WSA bundles of a feed, keyed by their build number."""
    builds = {}
    for filename, values in identities.items():
        if WSA_BUNDLE_RE.match(filename):
            builds[BUILD_RE.search(filename).group()] = values
    return builds
