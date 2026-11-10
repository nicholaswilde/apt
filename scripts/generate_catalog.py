#!/usr/bin/env python3
"""Automatically generate and synchronize package catalog in index.html.

Scans the pool/ directory (.deb files) and dists/ repository metadata
to generate semantic HTML package cards in index.html between marker comments:
<!-- packages:start -->
<!-- packages:end -->
"""

import argparse
import html
import io
import os
import re
import subprocess
import sys
import tarfile
from typing import Any, Dict, List, Optional, Set


def parse_control_text(text: str) -> Dict[str, str]:
    """Parse Debian control stanza text into a key-value dictionary."""
    fields: Dict[str, str] = {}
    current_key: Optional[str] = None

    for line in text.splitlines():
        if line.startswith(" ") or line.startswith("\t"):
            if current_key and current_key in fields:
                fields[current_key] += "\n" + line.strip()
        elif ":" in line:
            key, val = line.split(":", 1)
            current_key = key.strip().lower()
            fields[current_key] = val.strip()

    return fields


def extract_deb_control(deb_path: str) -> Optional[str]:
    """Extract control file contents from a .deb package."""
    # 1. Try host dpkg-deb if installed
    try:
        res = subprocess.run(
            ["dpkg-deb", "-f", deb_path],
            capture_output=True,
            text=True,
            check=True,
        )
        if res.stdout.strip():
            return res.stdout
    except Exception:
        pass

    # 2. Pure Python fallback reading ar archive
    try:
        with open(deb_path, "rb") as f:
            magic = f.read(8)
            if magic != b"!<arch>\n":
                return None
            while True:
                hdr = f.read(60)
                if len(hdr) < 60:
                    break
                name = hdr[:16].decode("ascii", errors="ignore").strip()
                size_str = hdr[48:58].decode("ascii", errors="ignore").strip()
                if not size_str.isdigit():
                    break
                size = int(size_str)
                content = f.read(size)
                if size % 2 == 1:
                    f.read(1)  # Pad byte

                if name.startswith("control.tar"):
                    with tarfile.open(fileobj=io.BytesIO(content)) as tar:
                        member = tar.extractfile("./control") or tar.extractfile("control")
                        if member:
                            return member.read().decode("utf-8", errors="replace")
    except Exception:
        pass

    return None


def parse_packages_file(packages_path: str) -> List[Dict[str, str]]:
    """Parse a Debian Packages file containing multiple stanzas."""
    stanzas: List[Dict[str, str]] = []
    if not os.path.isfile(packages_path):
        return stanzas

    try:
        with open(packages_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return stanzas

    raw_blocks = content.split("\n\n")
    for block in raw_blocks:
        block = block.strip()
        if block:
            fields = parse_control_text(block)
            if "package" in fields:
                stanzas.append(fields)

    return stanzas


def clean_description(raw_desc: str) -> str:
    """Format package description for HTML presentation."""
    if not raw_desc:
        return "Debian package hosted in repository."

    lines = [line.strip() for line in raw_desc.splitlines() if line.strip()]
    if not lines:
        return "Debian package hosted in repository."

    # Use first line (synopsis), plus second line if short
    synopsis = lines[0]
    if not synopsis.endswith("."):
        synopsis += "."
    return synopsis


def scan_packages(pool_dir: str, dists_dir: str) -> List[Dict[str, Any]]:
    """Aggregate package information across pool/ and dists/ metadata."""
    packages: Dict[str, Dict[str, Any]] = {}

    # 1. Scan dists/ metadata if present
    if os.path.isdir(dists_dir):
        for root, _, files in os.walk(dists_dir):
            for file in files:
                if file == "Packages":
                    full_path = os.path.join(root, file)
                    for stanza in parse_packages_file(full_path):
                        name = stanza.get("package")
                        if not name:
                            continue
                        version = stanza.get("version", "unknown")
                        arch = stanza.get("architecture", "all")
                        desc = stanza.get("description", "")
                        section = stanza.get("section", "main")

                        if name not in packages:
                            packages[name] = {
                                "name": name,
                                "version": version,
                                "archs": set(),
                                "description": clean_description(desc),
                                "section": section,
                            }
                        if arch:
                            packages[name]["archs"].add(arch)
                        # Keep newest or latest version string
                        if version and version != "unknown":
                            packages[name]["version"] = version

    # 2. Scan pool/ .deb archives
    if os.path.isdir(pool_dir):
        for root, _, files in os.walk(pool_dir):
            for file in files:
                if file.endswith(".deb"):
                    deb_path = os.path.join(root, file)
                    ctrl_text = extract_deb_control(deb_path)
                    if not ctrl_text:
                        continue
                    fields = parse_control_text(ctrl_text)
                    name = fields.get("package")
                    if not name:
                        continue
                    version = fields.get("version", "unknown")
                    arch = fields.get("architecture", "all")
                    desc = fields.get("description", "")
                    section = fields.get("section", "main")

                    if name not in packages:
                        packages[name] = {
                            "name": name,
                            "version": version,
                            "archs": set(),
                            "description": clean_description(desc),
                            "section": section,
                        }
                    if arch:
                        packages[name]["archs"].add(arch)
                    if version and version != "unknown":
                        packages[name]["version"] = version

    # Convert to sorted list
    result = []
    for name in sorted(packages.keys()):
        data = packages[name]
        data["archs"] = sorted(list(data["archs"])) if data["archs"] else ["all"]
        result.append(data)

    return result


def generate_html_catalog(packages: List[Dict[str, Any]], suite: str = "stable", component: str = "main") -> str:
    """Generate HTML snippet for package cards."""
    if not packages:
        return '        <p class="no-packages">No packages are currently published in the repository pool.</p>'

    items = []
    for pkg in packages:
        name = html.escape(pkg["name"])
        version = html.escape(pkg["version"])
        desc = html.escape(pkg["description"])
        arch_badges = "\n".join(
            f'              <span class="badge badge-arch">{html.escape(arch)}</span>'
            for arch in pkg["archs"]
        )

        card = f"""        <div class="package-item">
          <div class="package-header">
            <span class="package-name">{name}</span>
            <div class="package-badges">
              <span class="badge badge-version">v{version}</span>
              <span class="badge badge-component">{suite}/{component}</span>
{arch_badges}
            </div>
          </div>
          <p>
            {desc}
          </p>
          <div class="code-container">
            <div class="code-header">
              <span>install</span>
              <button class="copy-btn" data-target="cmd-install-{name}" title="Copy to clipboard">
                Copy
              </button>
            </div>
            <pre class="code-block" id="cmd-install-{name}"><code>sudo apt install {name}</code></pre>
          </div>
        </div>"""
        items.append(card)

    return "\n\n".join(items)


def update_index_file(index_path: str, new_content: str, check_only: bool = False) -> bool:
    """Update index.html with new package catalog between marker comments."""
    if not os.path.isfile(index_path):
        print(f"Error: {index_path} not found.", file=sys.stderr)
        return False

    with open(index_path, "r", encoding="utf-8") as f:
        original = f.read()

    marker_start = "<!-- packages:start -->"
    marker_end = "<!-- packages:end -->"

    pattern = re.compile(
        rf"({re.escape(marker_start)})(.*?)({re.escape(marker_end)})",
        re.DOTALL,
    )

    if not pattern.search(original):
        print(
            f"Error: Markers '{marker_start}' and '{marker_end}' not found in {index_path}.",
            file=sys.stderr,
        )
        return False

    replacement = f"{marker_start}\n{new_content}\n        {marker_end}"
    updated = pattern.sub(replacement, original)

    if updated == original:
        print("[✓] index.html is already up-to-date.")
        return True

    if check_only:
        print("[✗] index.html package catalog is out of date.", file=sys.stderr)
        return False

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"[✓] Updated {index_path} package catalog successfully.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize package catalog in index.html with pool/ and dists/."
    )
    parser.add_argument(
        "--index",
        default="index.html",
        help="Path to index.html (default: index.html)",
    )
    parser.add_argument(
        "--pool",
        default="pool",
        help="Path to pool directory (default: pool)",
    )
    parser.add_argument(
        "--dists",
        default="dists",
        help="Path to dists directory (default: dists)",
    )
    parser.add_argument(
        "--suite",
        default="stable",
        help="APT suite name (default: stable)",
    )
    parser.add_argument(
        "--component",
        default="main",
        help="APT component name (default: main)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if index.html is up-to-date without modifying (exit 1 if out-of-date)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated catalog HTML to stdout without modifying index.html",
    )

    args = parser.parse_args()

    packages = scan_packages(args.pool, args.dists)
    print(f"[*] Found {len(packages)} unique package(s) in repository.")
    for p in packages:
        print(f"    - {p['name']} (v{p['version']}, archs: {', '.join(p['archs'])})")

    catalog_html = generate_html_catalog(packages, suite=args.suite, component=args.component)

    if args.dry_run:
        print("\n--- Generated HTML Catalog ---")
        print(catalog_html)
        return 0

    success = update_index_file(args.index, catalog_html, check_only=args.check)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
