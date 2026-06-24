from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "export_generated_assets.py"
    )
    spec = importlib.util.spec_from_file_location(
        "export_generated_assets_script",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExportGeneratedAssetsPathTests(unittest.TestCase):
    def test_iter_source_svgs_reads_assets_poster_generated_folders(self) -> None:
        module = load_script_module()

        with tempfile.TemporaryDirectory(prefix="skill-analyzer-paths-") as temp_dir:
            root = Path(temp_dir)
            expected = [
                root / "assets" / "poster" / "generated-icons" / "user-icon.svg",
                root / "assets" / "poster" / "generated-decor" / "star-spark.svg",
                root / "assets" / "poster" / "generated-background" / "paper-texture.svg",
            ]

            for path in expected:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<svg />", encoding="utf-8")

            actual = module.iter_source_svgs(root)

            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
