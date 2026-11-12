---
name: enable-apt-trigger
description: >
  Update an upstream repository to trigger the APT repository deployment workflow
  upon release. Searches local workspace in /home/nicholas/git/nicholaswilde
  first before falling back to remote clone, verifies or sets the APT_REPO_TOKEN
  secret from pass, updates the application's .github/workflows/release.yml to
  build Debian packages and push them to pool/main in nicholaswilde/apt, and
  commits and pushes the changes. Trigger: /enable-apt-trigger, /add-apt-trigger,
  "update repo to trigger apt", "enable apt trigger", "add apt trigger",
  "configure apt trigger", "trigger apt flow".
---

# Enable APT Trigger Skill

Protocol for configuring an upstream application repository to automatically build Debian packages (`.deb`) and push them into `pool/main/` of `nicholaswilde/apt` whenever a new release tag is published, automatically triggering the APT repository deployment workflow (`deploy-repo.yml`).

## Inputs

- `<repo_name>` or `<owner>/<repo>`: Application repository name (e.g. `proxmox-mcp-rs`, `syncthing-mcp-rs`, `tfa`).
- `[secret_name]`: Secret name containing the GitHub PAT (defaults to `APT_REPO_TOKEN`).

## Tool Hygiene & Rules

- Pipe all GitHub CLI commands to `cat`: `rtk gh <command> | cat` (prevents pager hangs).
- Prefix shell commands with `rtk` where subcommands exist (`rtk git`, `rtk gh`, `rtk rg`).
- Never echo or write plaintext token secrets to chat or committed files.

---

## Workflow Steps

### Step 1: Discover Repository (Local Workspace First)

Always check the local workspace directory `/home/nicholas/git/nicholaswilde` first before using a remote clone:

```bash
REPO="<repo_name>" # e.g. "proxmox-mcp-rs"
LOCAL_DIR="/home/nicholas/git/nicholaswilde/${REPO}"

if [ -d "${LOCAL_DIR}" ]; then
  echo "Found local repository at: ${LOCAL_DIR}"
  cd "${LOCAL_DIR}"
else
  echo "Local repository not found in /home/nicholas/git/nicholaswilde/${REPO}. Cloning remote repository..."
  git clone "https://github.com/nicholaswilde/${REPO}.git" "/tmp/${REPO}"
  cd "/tmp/${REPO}"
fi
```

### Step 2: Configure `APT_REPO_TOKEN` Secret on Target Repo

The application's release workflow requires `APT_REPO_TOKEN` (fine-grained personal access token with `contents: write` permissions on `nicholaswilde/apt`) to clone and push `.deb` packages to this repository.

1. Check if secret exists:

   ```bash
   rtk gh secret list --repo "nicholaswilde/${REPO}" | cat
   ```

2. If missing, retrieve token value securely from `pass` and set repository secret via `gh`:

   ```bash
   rtk gh secret set APT_REPO_TOKEN --repo "nicholaswilde/${REPO}" --body "$(pass github-apt-fine-grain-token)" | cat
   ```

### Step 3: Verify Debian Packaging in Application

Ensure the target project has Debian package building configured.

#### For Rust CLI Projects (e.g. `Cargo.toml`)

In `Cargo.toml`, ensure `[package.metadata.deb]` exists with standard fields:

```toml
[package.metadata.deb]
maintainer = "Nicholas Wilde <ncwilde43@gmail.com>"
copyright = "2026 Nicholas Wilde"
license-file = ["LICENSE", "4"]
extended-description = "<Application description>"
section = "utils"
priority = "optional"
assets = [
  ["target/release/<binary>", "usr/bin/", "755"],
  ["README.md", "usr/share/doc/<binary>/README.md", "644"],
]
```

### Step 4: Update Application Release Workflow (`.github/workflows/release.yml`)

In the target repository's `.github/workflows/release.yml`:

#### A. Install `cargo-deb`, build package, and upload artifact

Inside the Linux release build job (e.g. `build-release`):

```yaml
    - name: Install cargo-deb
      if: startsWith(matrix.build, 'linux')
      shell: bash
      run: |
        CARGO_DEB_VER="3.8.0"
        curl -LO "https://github.com/kornelski/cargo-deb/releases/download/v${CARGO_DEB_VER}/cargo-deb_${CARGO_DEB_VER}-1_amd64.deb"
        sudo dpkg -i "cargo-deb_${CARGO_DEB_VER}-1_amd64.deb"
        rm -f "cargo-deb_${CARGO_DEB_VER}-1_amd64.deb"

    - name: Build Debian package
      if: startsWith(matrix.build, 'linux')
      shell: bash
      run: |
        cargo deb --no-build --target ${{ matrix.target }}

    - name: Upload Debian package artifact
      if: startsWith(matrix.build, 'linux')
      uses: actions/upload-artifact@v4
      with:
        name: deb-${{ matrix.build }}
        path: target/debian/*.deb
        retention-days: 1
```

#### B. Add `publish-deb` job

Add the `publish-deb` job after `build-release`:

```yaml
  publish-deb:
    name: publish-deb
    needs: ['create-release', 'build-release']
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Download all Debian packages
        uses: actions/download-artifact@v4
        with:
          pattern: deb-*
          merge-multiple: true
          path: debs/

      - name: Push .deb packages to nicholaswilde/apt
        if: github.ref_type == 'tag'
        env:
          APT_REPO_TOKEN: ${{ secrets.APT_REPO_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"

          # Clone apt repo using PAT
          git clone "https://x-access-token:${APT_REPO_TOKEN}@github.com/nicholaswilde/apt.git" apt-repo

          # Copy all generated Debian packages into pool/main
          cp debs/*.deb apt-repo/pool/main/

          # Commit and push changes
          cd apt-repo
          git add pool/main/*.deb
          if ! git diff --staged --quiet; then
            git commit -m "feat(pkg): add ${REPO} ${{ needs.create-release.outputs.version }} debs (amd64, arm64, armhf, armel)"
            git push origin main
          fi
```

### Step 5: Verify, Commit, and Push Changes

Review the changes in the target repository:

```bash
git diff
```

Commit and push to remote `main`:

```bash
git add Cargo.toml .github/workflows/release.yml
git commit -m "ci(release): add debian package build and publish to apt repo"
git push origin main
```
