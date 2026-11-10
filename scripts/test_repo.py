#!/usr/bin/env python3
"""Automated end-to-end test suite for serverless APT repository."""

import gzip
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

DEFAULT_URL = "https://nicholaswilde.io/apt"
HEADERS = {"User-Agent": "curl/7.88.1"}


def fetch_url(url: str, retries: int = 5, delay: int = 3) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_err}")


def run_tests(base_url: str) -> bool:
    base_url = base_url.rstrip("/")
    print(f"[*] Starting APT Repository Test Suite on: {base_url}")
    failed = False

    # 1. Verify Core HTTP Endpoints
    print("\n--- Phase 1: HTTP Endpoint Checks ---")
    core_files = [
        "public.key",
        "dists/stable/Release",
        "dists/stable/Release.gpg",
        "dists/stable/InRelease",
    ]
    for rel_path in core_files:
        url = f"{base_url}/{rel_path}"
        try:
            data = fetch_url(url)
            print(f"  ✓ {rel_path} ({len(data)} bytes)")
        except Exception as e:
            print(f"  ✗ {rel_path} FAILED: {e}")
            failed = True

    if failed:
        print("[!] Core endpoints unreachable. Aborting further checks.")
        return False

    with tempfile.TemporaryDirectory() as td:
        key_asc = os.path.join(td, "public.key")
        key_gpg = os.path.join(td, "public.gpg")
        inrel_path = os.path.join(td, "InRelease")
        rel_path = os.path.join(td, "Release")
        rel_gpg_path = os.path.join(td, "Release.gpg")

        with open(key_asc, "wb") as f:
            f.write(fetch_url(f"{base_url}/public.key"))
        with open(inrel_path, "wb") as f:
            f.write(fetch_url(f"{base_url}/dists/stable/InRelease"))
        with open(rel_path, "wb") as f:
            f.write(fetch_url(f"{base_url}/dists/stable/Release"))
        with open(rel_gpg_path, "wb") as f:
            f.write(fetch_url(f"{base_url}/dists/stable/Release.gpg"))

        # 2. Cryptographic Verification with gpgv
        print("\n--- Phase 2: Cryptographic Signature Verification (gpgv) ---")
        subprocess.run(["gpg", "--dearmor", "-o", key_gpg, key_asc], check=True)

        # InRelease (clearsigned)
        v_inrel = subprocess.run(
            ["gpgv", "--keyring", key_gpg, inrel_path],
            capture_output=True,
            text=True,
        )
        if v_inrel.returncode == 0:
            print("  ✓ InRelease: valid cryptographic signature")
        else:
            print(f"  ✗ InRelease verification failed:\n{v_inrel.stderr.strip()}")
            failed = True

        # Release.gpg (detached signature)
        v_rel = subprocess.run(
            ["gpgv", "--keyring", key_gpg, rel_gpg_path, rel_path],
            capture_output=True,
            text=True,
        )
        if v_rel.returncode == 0:
            print("  ✓ Release.gpg: valid detached signature")
        else:
            print(f"  ✗ Release.gpg verification failed:\n{v_rel.stderr.strip()}")
            failed = True

        # 3. Checksum Verification against Release file
        print("\n--- Phase 3: Release Index & Architecture Checksums ---")
        release_text = open(rel_path, "r", encoding="utf-8").read()
        sha256_entries = {}
        in_sha256 = False
        for line in release_text.splitlines():
            if line.startswith("SHA256:"):
                in_sha256 = True
                continue
            if in_sha256:
                if line.startswith(" ") or line.startswith("\t"):
                    parts = line.strip().split()
                    if len(parts) == 3:
                        sha256_entries[parts[2]] = (parts[0], int(parts[1]))
                else:
                    in_sha256 = False

        expected_archs = ["amd64", "arm64", "armhf", "armel"]
        for arch in expected_archs:
            pkg_rel = f"main/binary-{arch}/Packages"
            pkg_gz_rel = f"main/binary-{arch}/Packages.gz"

            for p in (pkg_rel, pkg_gz_rel):
                if p not in sha256_entries:
                    print(f"  ✗ Missing index entry in Release: {p}")
                    failed = True
                    continue

                exp_hash, exp_size = sha256_entries[p]
                data = fetch_url(f"{base_url}/dists/stable/{p}")
                actual_hash = hashlib.sha256(data).hexdigest()
                if actual_hash == exp_hash and len(data) == exp_size:
                    print(f"  ✓ {p} verified ({len(data)} bytes, sha256 match)")
                else:
                    print(f"  ✗ {p} checksum mismatch!")
                    failed = True

        # 4. Client Simulation (apt-get update & package inspection)
        print("\n--- Phase 4: Simulated APT Client Execution ---")
        etc_apt = os.path.join(td, "etc/apt")
        keyrings = os.path.join(etc_apt, "keyrings")
        sources_d = os.path.join(etc_apt, "sources.list.d")
        lists = os.path.join(td, "var/lib/apt/lists/partial")
        cache = os.path.join(td, "var/cache/apt/archives/partial")
        os.makedirs(keyrings, exist_ok=True)
        os.makedirs(sources_d, exist_ok=True)
        os.makedirs(lists, exist_ok=True)
        os.makedirs(cache, exist_ok=True)
        os.makedirs(os.path.join(td, "var/lib/dpkg"), exist_ok=True)
        with open(os.path.join(td, "var/lib/dpkg/status"), "w") as f:
            pass

        keyring_dest = os.path.join(keyrings, "repo.gpg")
        subprocess.run(["gpg", "--dearmor", "-o", keyring_dest, key_asc], check=True)

        sources_file = os.path.join(sources_d, "test.list")
        with open(sources_file, "w") as f:
            f.write(f"deb [signed-by={keyring_dest}] {base_url} stable main\n")

        apt_opts = [
            "-o", f"Dir::Etc={etc_apt}",
            "-o", f"Dir::Etc::sourcelist={sources_file}",
            "-o", f"Dir::Etc::sourceparts=-",
            "-o", f"Dir::State={os.path.join(td, 'var/lib/apt')}",
            "-o", f"Dir::State::status={os.path.join(td, 'var/lib/dpkg/status')}",
            "-o", f"Dir::Cache={os.path.join(td, 'var/cache/apt')}",
        ]

        # Test apt-get update
        res_update = subprocess.run(["apt-get", *apt_opts, "update"], capture_output=True, text=True)
        if res_update.returncode == 0:
            print("  ✓ apt-get update succeeded (exit code 0)")
        else:
            print(f"  ✗ apt-get update failed:\n{res_update.stderr.strip()}")
            failed = True

        # Test package query if packages present in amd64
        pkg_amd64_data = fetch_url(f"{base_url}/dists/stable/main/binary-amd64/Packages").decode("utf-8")
        package_names = [
            line.split(":", 1)[1].strip()
            for line in pkg_amd64_data.splitlines()
            if line.startswith("Package:")
        ]
        if package_names:
            target_pkg = package_names[0]
            res_show = subprocess.run(["apt-cache", *apt_opts, "show", target_pkg], capture_output=True, text=True)
            if res_show.returncode == 0 and f"Package: {target_pkg}" in res_show.stdout:
                print(f"  ✓ apt-cache show '{target_pkg}' resolved package metadata")
            else:
                print(f"  ✗ apt-cache show '{target_pkg}' failed")
                failed = True

            # Test package download
            res_dl = subprocess.run(["apt-get", *apt_opts, "download", target_pkg], cwd=td, capture_output=True, text=True)
            downloaded_debs = [f for f in os.listdir(td) if f.endswith(".deb")]
            if res_dl.returncode == 0 and downloaded_debs:
                print(f"  ✓ apt-get download '{target_pkg}' successfully downloaded {downloaded_debs[0]}")
            else:
                print(f"  ✗ apt-get download '{target_pkg}' failed")
                failed = True

    if failed:
        print("\n[!] TEST SUITE FAILED.")
        return False
    else:
        print("\n[✓] ALL TESTS PASSED.")
        return True


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    success = run_tests(url)
    sys.exit(0 if success else 1)
