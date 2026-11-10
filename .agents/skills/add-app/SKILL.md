---
name: add-app
description: Onboard an application to this APT repository. Searches local workspace in /home/nicholas/git/nicholaswilde first before falling back to remote URL, configures Debian package building, sets the APT_REPO_TOKEN secret from pass using gh, and updates the app release workflow to push .deb packages into pool/main. Trigger: /add-app, /add-package, "add app", "add app to apt repo", "add package to apt", "onboard app".
---

# Add App to APT Repository

Protocol for onboarding an application to `nicholaswilde/apt`. Configures Debian package building, configures the `APT_REPO_TOKEN` GitHub Actions secret from `pass`, updates the application's release workflow to automatically push `.deb` packages to `pool/main/`, and handles optional initial `.deb` import.

## Inputs

- `<app_name>` or `<owner>/<repo>`: Application repository name (e.g. `tfa` or `nicholaswilde/tfa`).

## Tool Hygiene & Rules

- Pipe all GitHub CLI commands to `cat`: `rtk gh <command> | cat` (prevents pager hangs).
- Prefix shell commands with `rtk` where subcommands exist (`rtk git`, `rtk gh`, `rtk rg`).
- Never echo or write plaintext token secrets to chat or committed files.

---

## Workflow Steps

### Step 1: Discover Repository (Local Workspace First)

Always check the local workspace directory `/home/nicholas/git/nicholaswilde` first before using remote URL:

```bash
REPO="<app_name>" # e.g. "tfa"
LOCAL_DIR="/home/nicholas/git/nicholaswilde/${REPO}"

if [ -d "${LOCAL_DIR}" ]; then
  echo "Found local repository at: ${LOCAL_DIR}"
  cd "${LOCAL_DIR}"
else
  echo "Local repository not found in /home/nicholas/git/nicholaswilde/${REPO}. Using remote URL: https://github.com/nicholaswilde/${REPO}.git"
  git clone "https://github.com/nicholaswilde/${REPO}.git" "/tmp/${REPO}"
  cd "/tmp/${REPO}"
fi
```

### Step 2: Configure `APT_REPO_TOKEN` Secret on Target Repo

The application's release workflow requires `APT_REPO_TOKEN` (fine-grained personal access token with `contents: write` permissions on `nicholaswilde/apt`) to clone and push `.deb` packages to this repository.

1. Retrieve token value securely from `pass` and set repository secret via `gh`:

   ```bash
   rtk gh secret set APT_REPO_TOKEN --repo "nicholaswilde/${REPO}" --body "$(pass github-apt-fine-grain-token)" | cat
   ```

2. Confirm secret is configured:

   ```bash
   rtk gh secret list --repo "nicholaswilde/${REPO}" | cat
   ```

### Step 3: Configure Debian Packaging in Application

Ensure the target project is configured to generate standard `.deb` packages.

#### For Rust CLI Projects (e.g. `tfa`)

In `Cargo.toml`, add or verify `[package.metadata.deb]`:

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
  ["assets/<binary>.1", "usr/share/man/man1/", "644"],
  ["completions/<binary>.bash", "usr/share/bash-completion/completions/<binary>", "644"],
  ["completions/_<binary>", "usr/share/zsh/vendor-completions/_<binary>", "644"],
  ["completions/<binary>.fish", "usr/share/fish/vendor_completions.d/<binary>.fish", "644"],
  ["README.md", "usr/share/doc/<binary>/README.md", "644"],
]
```

> **Note**: Only list assets that actually exist in the project (e.g. omit man pages or completions if not generated).

### Step 4: Update Application Release Workflow (`.github/workflows/release.yml`)

In the target application repository, update `.github/workflows/release.yml`:

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

    - name: Upload release archive
      uses: softprops/action-gh-release@v2
      if: github.ref_type == 'tag'
      with:
        files: |
          ${{ env.ASSET }}
          ${{ env.ASSET_SUM }}
          target/debian/*.deb
        draft: true
```

#### B. Add `publish-deb` job to push `.deb` packages to `nicholaswilde/apt`

Add job running after build:

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
            git commit -m "feat(pkg): add <app> ${{ needs.create-release.outputs.version }} debs"
            git push origin main
          fi
```

### Step 5: (Optional) Immediately Import Existing Release

If the application already has `.deb` releases on GitHub and should be available in the APT repo before the next release tag:

1. Switch to `nicholaswilde/apt` workspace:

   ```bash
   cd /home/nicholas/git/nicholaswilde/apt
   ```

2. Download released `.deb` files from latest release:

   ```bash
   rtk gh release download --repo "nicholaswilde/${REPO}" --pattern "*.deb" --dir pool/main/ | cat
   ```

3. Commit and push to `apt`:

   ```bash
   rtk git add pool/main/*.deb
   rtk git commit -m "feat(pkg): add ${REPO} deb"
   rtk git push origin main
   ```

### Step 6: Verify APT Deployment and Catalog

When new `.deb` packages land on `main` in `nicholaswilde/apt`:

1. GitHub Actions triggers `.github/workflows/deploy-repo.yml` automatically.
2. Monitor run status:

   ```bash
   rtk gh run list --workflow=deploy-repo.yml --limit=1 | cat
   ```

3. Verify catalog generation:

   ```bash
   task catalog:check
   ```
