"""Packaging boundaries: reject wrong/private inputs, preserve the review gate."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stage_e1003_candidate", REPO / "scripts/stage_e1003_candidate.py"
)
staging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(staging)


class CandidatePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        shutil.copytree(staging.SOURCE, self.source)
        # Synthetic fixture. The actual artifact is checked separately during
        # acceptance; no binary or real configuration belongs in test fixtures.
        self.payload = b"public synthetic factory image"
        self.firmware = self.root / "firmware.factory.bin"
        self.firmware.write_bytes(self.payload)
        manifest_path = self.source / "assets/firmware/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update(
            size_bytes=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
        )
        manifest_path.write_text(json.dumps(manifest))
        self.output = self.root / "review/reterminal_e1003_ha"

    def test_materializes_flash_payload_without_enabling_or_adding_setup_forms(self):
        staging.stage(self.firmware, self.output, source=self.source)
        self.assertFalse(yaml.safe_load((self.output / "solution.yaml").read_text())["enabled"])
        self.assertEqual(
            (self.output / "assets/firmware/firmware.factory.bin").read_bytes(),
            self.payload,
        )
        for lang in ("guide.md", "guide_zh.md"):
            self.assertIn(staging.NEW_STEP, (self.output / lang).read_text())
            self.assertNotIn(staging.OLD_STEP, (self.output / lang).read_text())
        flash = yaml.safe_load((self.output / "devices/e1003_usb.yaml").read_text())
        self.assertEqual(flash["firmware"]["flash_config"]["partitions"][0]["offset"], "0x0")
        self.assertFalse(next(s for s in flash["steps"] if s["id"] == "erase")["default"])
        self.assertFalse((self.output / "devices/review_flash.yaml").exists())
        for path in (self.output / "devices").glob("*.yaml"):
            self.assertFalse(yaml.safe_load(path.read_text()).get("user_inputs"))

    def test_rejects_same_size_corruption_before_creating_output(self):
        self.firmware.write_bytes(b"x" * len(self.payload))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            staging.stage(self.firmware, self.output, source=self.source)
        self.assertFalse(self.output.parent.exists())

    def test_rejects_wrong_size_before_creating_output(self):
        self.firmware.write_bytes(b"wrong size")
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            staging.stage(self.firmware, self.output, source=self.source)
        self.assertFalse(self.output.exists())

    def test_private_paths_are_rejected_without_reading_them(self):
        for directory in ("provisioning", "verification"):
            with self.assertRaisesRegex(ValueError, "Private"):
                staging.stage(self.root / ".esphome" / directory / "absent.bin", self.output)

    def test_refuses_git_checkout_output_and_existing_review_directory(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            staging.stage(self.firmware, staging.SOURCE, source=self.source)
        self.output.mkdir(parents=True)
        (self.output / "keep.txt").write_text("reviewer work")
        with self.assertRaisesRegex(ValueError, "already exists"):
            staging.stage(self.firmware, self.output, source=self.source)
        self.assertEqual((self.output / "keep.txt").read_text(), "reviewer work")


if __name__ == "__main__":
    unittest.main()
