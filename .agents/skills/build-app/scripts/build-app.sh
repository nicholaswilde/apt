#!/usr/bin/env bash
set -euo pipefail

# Build application locally across all architectures and copy .deb packages to APT repo.
# Supported Debian architectures: amd64, arm64, armhf, armel

DEFAULT_WORKSPACE_BASE="/home/nicholas/git/nicholaswilde"
DEFAULT_APT_REPO="/home/nicholas/git/nicholaswilde/apt"

APP_INPUT=""
APT_REPO="${APT_DIR:-$DEFAULT_APT_REPO}"
SPECIFIC_ARCH=""
SKIP_BUILD=false
SKIP_CATALOG=false
DRY_RUN=false

show_help() {
  cat << 'EOF'
Usage: build-app.sh [OPTIONS] <APP_NAME_OR_PATH>

Build an application locally across all architectures and copy .deb files to nicholaswilde/apt.

Arguments:
  <APP_NAME_OR_PATH>         Name of repo in /home/nicholas/git/nicholaswilde/ or absolute path

Options:
  -a, --arch <arch>          Build only specified architecture (amd64, arm64, armhf, armel)
  --apt-dir <path>           Path to APT repository (default: /home/nicholas/git/nicholaswilde/apt)
  --skip-build               Skip binary compilation, only package .deb and copy
  --skip-catalog             Skip running 'task catalog' after copying
  -n, --dry-run              Print commands without executing
  -h, --help                 Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--arch)
      SPECIFIC_ARCH="$2"
      shift 2
      ;;
    --apt-dir)
      APT_REPO="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --skip-catalog)
      SKIP_CATALOG=true
      shift
      ;;
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      if [[ -z "$APP_INPUT" ]]; then
        APP_INPUT="$1"
      else
        echo "Error: Unknown argument: $1" >&2
        show_help
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$APP_INPUT" ]]; then
  echo "Error: Application name or path required." >&2
  show_help
  exit 1
fi

# Resolve application directory
if [[ -d "$APP_INPUT" ]]; then
  APP_DIR="$(cd "$APP_INPUT" && pwd)"
elif [[ -d "${DEFAULT_WORKSPACE_BASE}/${APP_INPUT}" ]]; then
  APP_DIR="${DEFAULT_WORKSPACE_BASE}/${APP_INPUT}"
else
  echo "Error: Directory not found: ${APP_INPUT} or ${DEFAULT_WORKSPACE_BASE}/${APP_INPUT}" >&2
  exit 1
fi

APP_NAME="$(basename "$APP_DIR")"
POOL_DIR="${APT_REPO}/pool/main"

echo "=== Building ${APP_NAME} locally for APT repository ==="
echo "Application directory: ${APP_DIR}"
echo "Destination pool:      ${POOL_DIR}"

if [[ ! -d "$POOL_DIR" ]]; then
  echo "Error: Destination pool directory does not exist: $POOL_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

# Target definitions for multi-arch builds (Debian arch : Rust target triple)
declare -a ALL_TARGETS=(
  "amd64:x86_64-unknown-linux-gnu"
  "arm64:aarch64-unknown-linux-gnu"
  "armhf:armv7-unknown-linux-gnueabihf"
  "armel:arm-unknown-linux-musleabi"
)

# Filter targets if specific arch requested
TARGETS_TO_BUILD=()
if [[ -n "$SPECIFIC_ARCH" ]]; then
  for item in "${ALL_TARGETS[@]}"; do
    arch="${item%%:*}"
    if [[ "$arch" == "$SPECIFIC_ARCH" ]]; then
      TARGETS_TO_BUILD+=("$item")
    fi
  done
  if [[ ${#TARGETS_TO_BUILD[@]} -eq 0 ]]; then
    echo "Error: Unsupported architecture: $SPECIFIC_ARCH. Supported: amd64, arm64, armhf, armel" >&2
    exit 1
  fi
else
  TARGETS_TO_BUILD=("${ALL_TARGETS[@]}")
fi

run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] $*"
  else
    echo "+ $*"
    "$@"
  fi
}

# Determine project type
if [[ -f "Cargo.toml" ]]; then
  echo "Detected Rust project (Cargo.toml)"

  if ! grep -q "\[package.metadata.deb\]" Cargo.toml; then
    echo "Warning: [package.metadata.deb] not found in Cargo.toml. cargo-deb might need configuration."
  fi

  # Check cargo-deb
  if ! command -v cargo-deb >/dev/null 2>&1; then
    echo "Error: cargo-deb is not installed. Install via: cargo install cargo-deb" >&2
    exit 1
  fi

  # 1. Compile binaries for all targets
  if [[ "$SKIP_BUILD" != "true" ]]; then
    echo "--- Building binaries ---"
    for item in "${TARGETS_TO_BUILD[@]}"; do
      arch="${item%%:*}"
      triple="${item##*:}"
      echo "Building binary for ${arch} (${triple})..."

      # Check if Taskfile has build task for this target
      if [[ -f "Taskfile.yml" || -f "Taskfile.yaml" ]] && command -v task >/dev/null 2>&1; then
        case "$arch" in
          amd64)
            if task --list | grep -q "build:amd64"; then
              run_cmd task build:amd64
              continue
            fi
            ;;
          arm64)
            if task --list | grep -q "build:arm64"; then
              run_cmd task build:arm64
              continue
            fi
            ;;
          armhf)
            if task --list | grep -q "build:armv7"; then
              run_cmd task build:armv7
              continue
            fi
            ;;
          armel)
            if task --list | grep -q "build:armv6"; then
              run_cmd task build:armv6
              continue
            fi
            ;;
        esac
      fi

      # Fallback to cross build or cargo build
      if command -v cross >/dev/null 2>&1; then
        run_cmd cross build --release --target "$triple"
      else
        run_cmd cargo build --release --target "$triple"
      fi
    done
  else
    echo "Skipping binary compilation (--skip-build specified)."
  fi

  # 2. Package into .deb using cargo-deb
  echo "--- Packaging Debian (.deb) files ---"
  mkdir -p target/debian
  for item in "${TARGETS_TO_BUILD[@]}"; do
    arch="${item%%:*}"
    triple="${item##*:}"
    echo "Packaging Debian package for ${arch} (${triple})..."
    run_cmd cargo deb --no-build --target "$triple"
  done

elif [[ -f "Taskfile.yml" || -f "Taskfile.yaml" ]] && command -v task >/dev/null 2>&1; then
  echo "Detected Taskfile project"
  if [[ "$SKIP_BUILD" != "true" ]]; then
    if task --list | grep -q "deb"; then
      run_cmd task deb
    elif task --list | grep -q "build"; then
      run_cmd task build
    fi
  fi
else
  echo "Unknown or custom project type. Looking for existing .deb packages..."
fi

# 3. Locate and copy .deb packages to APT pool/main
echo "--- Copying .deb packages to APT repository pool ---"
COPIED_COUNT=0
declare -A SEEN_DEBS

# Find all generated deb files across build directories
while IFS= read -r -d '' deb_file; do
  deb_filename="$(basename "$deb_file")"
  if [[ -z "${SEEN_DEBS[$deb_filename]:-}" ]]; then
    SEEN_DEBS["$deb_filename"]=1
    echo "Copying ${deb_filename} -> ${POOL_DIR}/"
    run_cmd cp -f "$deb_file" "${POOL_DIR}/"
    ((COPIED_COUNT++)) || true
  fi
done < <(find target dist -type f -name "*.deb" -print0 2>/dev/null || true)

echo "Successfully copied ${COPIED_COUNT} .deb package(s) to ${POOL_DIR}."

# 4. Update APT repository catalog
if [[ "$SKIP_CATALOG" != "true" && -f "${APT_REPO}/Taskfile.yaml" ]]; then
  echo "--- Updating package catalog in ${APT_REPO} ---"
  (
    cd "$APT_REPO"
    if command -v task >/dev/null 2>&1; then
      run_cmd task catalog
      run_cmd task catalog:check
    fi
  )
fi

# 5. Display summary of deb files in pool/main
echo "=== Copied Packages in pool/main ==="
for deb in "${POOL_DIR}"/*.deb; do
  if [[ -f "$deb" ]] && command -v dpkg-deb >/dev/null 2>&1; then
    pkg_info="$(dpkg-deb -I "$deb" 2>/dev/null | grep -E 'Package:|Version:|Architecture:' | tr '\n' ' ')"
    echo "  $(basename "$deb"): ${pkg_info}"
  fi
done

echo ""
echo "Next steps in ${APT_REPO}:"
echo "  1. Verify git status: rtk git status"
echo "  2. Stage changes:     rtk git add pool/main/*.deb public/index.html"
echo "  3. Commit and push:   rtk git commit -m \"feat(pkg): add ${APP_NAME} debs\" && rtk git push origin main"
