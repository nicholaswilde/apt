---
name: deploy-apt-repo
description: Trigger manual deployment of the APT repository on GitHub Actions or inspect deployment status. Trigger: /deploy-apt-repo, "deploy apt repo", "deploy repo", "trigger apt deployment".
---

# Deploy APT Repo Skill

Trigger manual execution of `.github/workflows/deploy-repo.yml` to generate APT metadata, sign release, and publish to GitHub Pages.

## Protocol

1. Trigger workflow dispatch:

   ```bash
   rtk gh workflow run deploy-repo.yml | cat
   ```

2. Watch run status:

   ```bash
   rtk gh run list --workflow=deploy-repo.yml --limit=1 | cat
   ```
