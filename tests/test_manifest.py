from io import BytesIO
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("manifest", ROOT / "scripts/manifest.py")
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class ManifestTests(unittest.TestCase):
    def test_fork_release_targets_jellyfin_12_and_own_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "Jellyfin.MetaTube@v2026.1026.1.0.zip"
            artifact.write_bytes(b"build artifact")
            with patch.dict(
                os.environ,
                {"GITHUB_REPOSITORY": "rosystain/jellyfin-plugin-metatube"},
            ):
                entry = manifest.generate(
                    str(artifact),
                    "2026.1026.1.0",
                    ROOT / "Jellyfin.Plugin.MetaTube/Jellyfin.Plugin.MetaTube.csproj",
                )

            self.assertEqual(entry["targetAbi"], "12.0.0.0")
            self.assertEqual(
                entry["sourceUrl"],
                "https://github.com/rosystain/jellyfin-plugin-metatube/releases/download/"
                "v2026.1026.1.0/Jellyfin.MetaTube@v2026.1026.1.0.zip",
            )
            self.assertEqual(entry["checksum"], hashlib.md5(artifact.read_bytes()).hexdigest())
            self.assertTrue(entry["timestamp"].endswith("Z"))

    def test_local_generation_defaults_to_fork_repository(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                manifest.get_repository(),
                "rosystain/jellyfin-plugin-metatube",
            )

    def test_main_preserves_history_and_reads_fork_manifest(self):
        repository = "rosystain/jellyfin-plugin-metatube"
        prior_version = {
            "version": "2025.1102.2200.0",
            "sourceUrl": "https://github.com/metatube-community/jellyfin-plugin-metatube/releases/download/old.zip",
        }
        prior_manifest = [{"guid": "01cc53ec-c415-4108-bbd4-a684a9801a32", "versions": [prior_version]}]

        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "Jellyfin.MetaTube@v2026.1026.1.0.zip"
            artifact.write_bytes(b"new build")
            manifest_path = Path(directory) / "manifest.json"
            current_directory = os.getcwd()
            try:
                os.chdir(directory)
                with (
                    patch.dict(os.environ, {"GITHUB_REPOSITORY": repository}),
                    patch.object(sys, "argv", ["manifest.py", str(artifact)]),
                    patch.object(manifest, "urlopen", return_value=BytesIO(json.dumps(prior_manifest).encode())) as urlopen,
                ):
                    manifest.main()
            finally:
                os.chdir(current_directory)

            result = json.loads(manifest_path.read_text())
            self.assertEqual(
                urlopen.call_args.args[0],
                f"https://raw.githubusercontent.com/{repository}/dist/manifest.json",
            )
            self.assertEqual(result[0]["versions"][1], prior_version)
            self.assertEqual(
                result[0]["versions"][0]["sourceUrl"],
                f"https://github.com/{repository}/releases/download/"
                "v2026.1026.1.0/Jellyfin.MetaTube@v2026.1026.1.0.zip",
            )


if __name__ == "__main__":
    unittest.main()
