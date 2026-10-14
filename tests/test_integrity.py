"""A plausible, internally consistent edit must not bypass release integrity."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from registry.core import build, validate
from registry.sources import encoded
from test_registry import fixtures


class ReleaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        original_directory = Path.cwd()
        self.addCleanup(os.chdir, original_directory)
        os.chdir(temporary.name)
        data, reviewed = fixtures()
        Path("data").mkdir()
        Path("data/reviewed-evidence.json").write_bytes(encoded(reviewed))
        Path("licenses").mkdir()
        Path("licenses/Fixture-MIT.txt").write_text("Fixture license\n")
        Path(".cache").mkdir()
        for name, value in data.items():
            Path(".cache", name + ".json").write_bytes(encoded(value))
        self.output = Path("public/v1")
        build(output=self.output)

    def rewrite_manifest(self):
        """Simulate an editor regenerating checksums after modifying JSON."""
        lines = []
        for path in sorted(self.output.rglob("*")):
            if path.is_file() and path.name != "checksums.sha256":
                lines.append(hashlib.sha256(path.read_bytes()).hexdigest()
                             + "  " + str(path.relative_to(self.output)))
        (self.output / "checksums.sha256").write_text("\n".join(lines) + "\n")

    def test_consistent_model_edit_with_new_checksums_rejects_stale_data_version(self):
        # Keep every partition consistent and make the new checksum inventory valid.
        # The unchanged release identity must still reveal the content mutation.
        for path in self.output.rglob("*.json"):
            value = json.loads(path.read_text())
            for model in value.get("models", []):
                if model["id"] == "lab/model-one":
                    model["name"] = "Unreviewed replacement name"
            path.write_bytes(encoded(value))
        self.rewrite_manifest()
        with self.assertRaisesRegex(ValueError, "data_version"):
            validate(self.output)

    def test_missing_manifest_is_rejected(self):
        (self.output / "checksums.sha256").unlink()
        with self.assertRaisesRegex(ValueError, "Missing checksum manifest"):
            validate(self.output)

    def test_split_and_provider_sources_cannot_diverge_even_with_new_checksums(self):
        for relative in ("models.json", "provider-models/lab.json"):
            with self.subTest(document=relative):
                path = self.output / relative
                original = path.read_bytes()
                value = json.loads(original)
                value["sources"][0]["url"] = "https://different.example.test/catalog.json"
                path.write_bytes(encoded(value))
                self.rewrite_manifest()
                with self.assertRaisesRegex(ValueError, "Envelope sources differ"):
                    validate(self.output)
                path.write_bytes(original)
                self.rewrite_manifest()


if __name__ == "__main__":
    unittest.main()
