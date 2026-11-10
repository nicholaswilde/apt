# APT Repository Management Rules

## Repository Layout & Packages
1. **Debian Packages**: Store raw `.deb` binary files in `pool/main/` or package subdirectories.
2. **Metadata Generation**: Never commit generated `dists/`, `Packages`, `Packages.gz`, `Release`, `InRelease`, or `public.key` files to `main`. These are generated and deployed automatically via `.github/workflows/deploy-repo.yml` on GitHub Pages.
3. **Directory Tracking**: Maintain `pool/main/.keep` so git tracks empty package directories before `.deb` additions.

## Workflow Triggers & Secrets
1. **Triggers**: Workflow runs automatically on pushes modifying `pool/**/*.deb` or via `workflow_dispatch`.
2. **GPG Signing**: CI requires GitHub repository secrets `GPG_PRIVATE_KEY` and `GPG_PASSPHRASE`.
3. **Manual Trigger**: Dispatch workflow with `rtk gh workflow run deploy-repo.yml | cat`.
