#!/usr/bin/env python3
"""回归组件 Gallery 的可重建性、组件覆盖和最终 HTML 契约。"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[2]
BUILDER = SKILL_DIR / "scripts" / "build_component_gallery.py"
CHECKER = SKILL_DIR / "scripts" / "check_html_report.py"
REGISTRY = SKILL_DIR / "assets" / "components" / "registry.json"


class ComponentGalleryTest(unittest.TestCase):
    def test_committed_gallery_is_current(self) -> None:
        completed = subprocess.run(
            ["python3", str(BUILDER), "--check"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_gallery_covers_registry_and_annotation_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "component-gallery.html"
            built = subprocess.run(
                ["python3", str(BUILDER), "--output", str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, built.returncode, built.stderr)
            checked = subprocess.run(
                ["python3", str(CHECKER), str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)

            html = output.read_text(encoding="utf-8")
            registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
            declaration_start = html.index('data-html-report-components="')
            declaration_end = html.index(
                '"',
                declaration_start + len('data-html-report-components="'),
            )
            declaration = html[declaration_start:declaration_end]
            for component in registry["components"]:
                self.assertIn(component, declaration)
            self.assertIn("QA_ANNOTATION_CSS_START", html)
            self.assertIn("QA_ANNOTATION_SCRIPT_START", html)
            self.assertIn('data-html-report-runtime="interactions"', html)
            self.assertIn("button.className = 'back-to-top'", html)


if __name__ == "__main__":
    unittest.main()
