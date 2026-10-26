#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import urlopen

from packaging.version import Version

DEFAULT_REPOSITORY = "rosystain/jellyfin-plugin-metatube"


def get_repository() -> str:
    return os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)


def md5sum(filename) -> str:
    with open(filename, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_jellyfin_version(csproj: str) -> str:
    tree = ET.parse(csproj)
    root = tree.getroot()

    for pkg in root.iter("PackageReference"):
        if pkg.attrib.get("Include") in ("Jellyfin.Controller", "Jellyfin.Model"):
            return Version(pkg.attrib.get("Version")).base_version

    raise Exception("Jellyfin version not found")


def generate(filename, version, csproj, repository=None) -> dict:
    repository = repository or get_repository()
    return {
        "checksum": md5sum(filename),
        "changelog": "Auto Released by Actions",
        "targetAbi": f"{get_jellyfin_version(csproj)}.0",
        "sourceUrl": f"https://github.com/{repository}/releases/download/"
        f"v{version}/Jellyfin.MetaTube@v{version}.zip",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": version,
    }


def main() -> None:
    filename = sys.argv[1]
    version = filename.split("@", maxsplit=1)[1].removeprefix("v").removesuffix(".zip")
    csproj = os.path.join(
        os.path.dirname(__file__),
        "../Jellyfin.Plugin.MetaTube/Jellyfin.Plugin.MetaTube.csproj",
    )

    repository = get_repository()
    manifest_url = f"https://raw.githubusercontent.com/{repository}/dist/manifest.json"
    with urlopen(manifest_url) as f:
        manifest = json.load(f)

    manifest[0]["versions"].insert(0, generate(filename, version, csproj, repository))

    with open("manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
