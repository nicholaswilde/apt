---
name: build-app
description: Build an application locally across all architectures (amd64, arm64, armhf, armel) from /home/nicholas/git/nicholaswilde/<app> and copy the generated .deb packages to this APT repository pool/main/. Trigger: /build-app, /build-app-deb, /build-deb, "build app", "build app locally", "build debs locally", "build deb", "build and copy debs".
---

# Build App Locally & Copy Debian Packages Skill

Protocol and helper automation to build an application locally across all supported Debian architectures (`amd64`, `arm64`, `armhf`, `armel`) from `/home/nicholas/git/nicholaswilde/<app>` and copy the generated `.deb` packages directly into `pool/main/` of `nicholaswilde/apt`.

## Inputs

- `<app_name>` or `<path>` (Required): Application name located in `/home/nicholas/git/nicholaswilde/` (e.g. `tfa`) or full directory path.
- `[--arch <arch>]` (Optional): Restrict build to single architecture (`amd64`, `arm64`, `armhf`, `armel`).
- `[--skip-build]` (Optional): Package `.deb` files from existing build artifacts without recompiling.
- `[--dry-run]` (Optional): Preview build and copy commands.

## Supported Architectures

| Debian Architecture | Rust Target Platform Triple | Common Device / CPU |
|---|---|---|
| `amd64` | `x86_64-unknown-linux-gnu` | 64-bit x86 PCs, servers |
| `arm64` | `aarch64-unknown-linux-gnu` | Raspberry Pi 3/4/5 (64-bit), ARM servers |
| `armhf` | `armv7-unknown-linux-gnueabihf` | Raspberry Pi 2/3 (32-bit), ARMv7 boards |
| `armel` | `arm-unknown-linux-musleabi` | Raspberry Pi Zero / 1, ARMv6 legacy boards |

---

## Quick Execution via Helper Script

Run the automated build script:

```bash
# Build all architectures and copy to pool/main/
.agents/skills/build-app/scripts/build-app.sh <app_name>

# Example: build tfa across all architectures
.agents/skills/build-app/scripts/build-app.sh tfa

# Build single architecture
.agents/skills/build-app/scripts/build-app.sh --arch arm64 tfa

# Package and copy only without recompiling binaries
.agents/skills/build-app/scripts/build-app.sh --skip-build tfa
```

---

## Manual Protocol

### Step 1: Locate Local Application Repository

Resolve the target application in the local workspace:

```bash
APP_NAME="<app_name>" # e.g. "tfa"
APP_DIR="/home/nicholas/git/nicholaswilde/${APP_NAME}"
APT_REPO="/home/nicholas/git/nicholaswilde/apt"

if [ ! -d "${APP_DIR}" ]; then
  echo "Error: Directory ${APP_DIR} does not exist" >&2
  exit 1
fi
cd "${APP_DIR}"
```

### Step 2: Compile Binaries for All Architectures

Using `cross` or project `Taskfile.yml`:

```bash
# AMD64 (x86_64)
cross build --release --target x86_64-unknown-linux-gnu

# ARM64 (aarch64)
cross build --release --target aarch64-unknown-linux-gnu

# ARMv7 (armhf)
cross build --release --target armv7-unknown-linux-gnueabihf

# ARMv6 (armel)
cross build --release --target arm-unknown-linux-musleabi
```

If the project defines multi-arch tasks in `Taskfile.yml` (e.g. `tfa`):

```bash
task build:amd64
task build:arm64
task build:armv7
task build:armv6
```

### Step 3: Package Debian `.deb` Files

Generate `.deb` packages with `cargo-deb`:

```bash
cargo deb --no-build --target x86_64-unknown-linux-gnu
cargo deb --no-build --target aarch64-unknown-linux-gnu
cargo deb --no-build --target armv7-unknown-linux-gnueabihf
cargo deb --no-build --target arm-unknown-linux-musleabi
```

Packages are output to `target/debian/` (or `target/<target>/debian/`).

### Step 4: Copy `.deb` Files to APT Repository

Copy all generated `.deb` packages into `pool/main/`:

```bash
# Copy from target build directories to APT repo pool
find target dist -type f -name "*.deb" -exec cp -f {} "${APT_REPO}/pool/main/" \;
```

### Step 5: Update Package Catalog & Verify

Switch back to `nicholaswilde/apt`:

```bash
cd "${APT_REPO}"

# Synchronize public/index.html catalog with pool/ packages
task catalog

# Check catalog sync status
task catalog:check
```

Inspect copied `.deb` packages:

```bash
for deb in pool/main/*.deb; do
  dpkg-deb -I "$deb" | grep -E "Package:|Version:|Architecture:"
done
```

### Step 6: Commit and Deploy

Stage new deb packages and catalog, commit, and push to deploy via GitHub Actions:

```bash
rtk git add pool/main/*.deb public/index.html
rtk git commit -m "feat(pkg): add ${APP_NAME} debs (amd64, arm64, armhf, armel)"
rtk git push origin main
```
