#!/usr/bin/env python3
"""Unit tests for scripts/generate_catalog.py."""

import os
import tempfile
import unittest

from scripts.generate_catalog import (
    clean_description,
    extract_deb_control,
    generate_html_catalog,
    parse_control_text,
    scan_packages,
    update_index_file,
)


class TestGenerateCatalog(unittest.TestCase):
    def test_parse_control_text(self):
        text = """Package: my-app
Version: 1.2.3
Architecture: amd64
Description: Short synopsis
 Extended description line 1.
 Extended line 2.
Section: utils
"""
        fields = parse_control_text(text)
        self.assertEqual(fields["package"], "my-app")
        self.assertEqual(fields["version"], "1.2.3")
        self.assertEqual(fields["architecture"], "amd64")
        self.assertEqual(fields["section"], "utils")
        self.assertIn("Short synopsis", fields["description"])
        self.assertIn("Extended line 2.", fields["description"])

    def test_clean_description(self):
        raw = "CLI utility for testing\n Extended details here."
        self.assertEqual(clean_description(raw), "CLI utility for testing.")

        empty = ""
        self.assertEqual(clean_description(empty), "Debian package hosted in repository.")

    def test_generate_html_catalog(self):
        packages = [
            {
                "name": "sample-pkg",
                "version": "2.0.0",
                "archs": ["amd64", "arm64"],
                "description": "Sample test package.",
                "section": "utils",
            }
        ]
        html = generate_html_catalog(packages)
        self.assertIn('class="package-name">sample-pkg</span>', html)
        self.assertIn('class="badge badge-version">v2.0.0</span>', html)
        self.assertIn('class="badge badge-arch">amd64</span>', html)
        self.assertIn('class="badge badge-arch">arm64</span>', html)
        self.assertIn("sudo apt install sample-pkg", html)

    def test_update_index_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".html") as tf:
            tf.write("""<!doctype html>
<html>
<body>
  <!-- packages:start -->
  <p>Old content</p>
  <!-- packages:end -->
</body>
</html>""")
            tf_path = tf.name

        try:
            new_content = '<div class="package-item">New Package</div>'
            res = update_index_file(tf_path, new_content)
            self.assertTrue(res)

            with open(tf_path, "r") as f:
                content = f.read()
            self.assertIn("New Package", content)
            self.assertNotIn("Old content", content)

            # Check mode: already in sync returns True
            check_res = update_index_file(tf_path, new_content, check_only=True)
            self.assertTrue(check_res)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_real_pool_tfa(self):
        pool_path = "pool"
        if not os.path.isdir(pool_path):
            self.skipTest("pool/ directory not found")

        packages = scan_packages(pool_path, "dists")
        pkg_names = [p["name"] for p in packages]
        self.assertIn("tfa", pkg_names)

        tfa_pkg = next(p for p in packages if p["name"] == "tfa")
        self.assertEqual(tfa_pkg["version"], "0.1.16-1")
        self.assertIn("amd64", tfa_pkg["archs"])


if __name__ == "__main__":
    unittest.main()
